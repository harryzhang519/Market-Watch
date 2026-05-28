"""
FRED (Federal Reserve Economic Data) ingestion for US cities.

Fetches median listing prices, housing inventory, days on market,
and mortgage rates from the FRED API.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
REQUEST_TIMEOUT = 30.0

# Known FRED series ID mappings per city slug.
# FRED series naming is inconsistent, so we list multiple possible IDs to try.
SERIES_CANDIDATES: Dict[str, Dict[str, List[str]]] = {
    "columbus-oh": {
        "price": ["MEDLISPRI18140", "MEDLISPRICOLS18140", "ATNHPIUS18140A"],
        "inventory": ["ACTLISCOU18140", "ACTLISCOUMSA18140"],
        "dom": ["MEDDAYONMAR18140", "MEDDAYONMARMSA18140"],
    },
    "cleveland-oh": {
        "price": ["MEDLISPRI17460", "MEDLISPRICLEV17460", "ATNHPIUS17460A"],
        "inventory": ["ACTLISCOU17460", "ACTLISCOUMSA17460"],
        "dom": ["MEDDAYONMAR17460", "MEDDAYONMARMSA17460"],
    },
    "cincinnati-oh": {
        "price": ["MEDLISPRI17140", "MEDLISPRICINC17140", "ATNHPIUS17140A"],
        "inventory": ["ACTLISCOU17140", "ACTLISCOUMSA17140"],
        "dom": ["MEDDAYONMAR17140", "MEDDAYONMARMSA17140"],
    },
    "new-york-city-ny": {
        "price": ["MEDLISPRI35620", "MEDLISPRINEWYOR35620", "ATNHPIUS35620A"],
        "inventory": ["ACTLISCOU35620", "ACTLISCOUMSA35620"],
        "dom": ["MEDDAYONMAR35620", "MEDDAYONMARMSA35620"],
    },
    "buffalo-ny": {
        "price": ["MEDLISPRI15380", "MEDLISPRIBUFF15380", "ATNHPIUS15380A"],
        "inventory": ["ACTLISCOU15380", "ACTLISCOUMSA15380"],
        "dom": ["MEDDAYONMAR15380", "MEDDAYONMARMSA15380"],
    },
    "albany-ny": {
        "price": ["MEDLISPRI10580", "MEDLISPRIALBA10580", "ATNHPIUS10580A"],
        "inventory": ["ACTLISCOU10580", "ACTLISCOUMSA10580"],
        "dom": ["MEDDAYONMAR10580", "MEDDAYONMARMSA10580"],
    },
}

# National mortgage rate series — consistent and reliable
MORTGAGE_SERIES = "MORTGAGE30US"


def _get_api_key() -> Optional[str]:
    """Retrieve the FRED API key from environment."""
    key = os.getenv("FRED_API_KEY")
    if not key:
        logger.warning(
            "FRED_API_KEY not set in environment. FRED data will be unavailable. "
            "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html"
        )
    return key


async def _fetch_series(
    client: httpx.AsyncClient,
    series_id: str,
    api_key: str,
    limit: int = 2,
) -> Optional[List[dict]]:
    """Fetch the latest observations for a single FRED series.

    Returns a list of observation dicts or None if the series doesn't exist / errors.
    """
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
    }
    try:
        resp = await client.get(FRED_BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 404:
            logger.debug("FRED series %s not found (404)", series_id)
            return None
        if resp.status_code == 429:
            logger.warning("FRED rate limit hit while fetching %s", series_id)
            return None
        resp.raise_for_status()
        data = resp.json()
        observations = data.get("observations", [])
        # Filter out observations with missing values
        return [
            obs for obs in observations
            if obs.get("value") not in (None, "", ".")
        ]
    except httpx.TimeoutException:
        logger.warning("Timeout fetching FRED series %s", series_id)
        return None
    except httpx.HTTPStatusError as e:
        logger.warning("HTTP error fetching FRED series %s: %s", series_id, e)
        return None
    except Exception as e:
        logger.error("Unexpected error fetching FRED series %s: %s", series_id, e)
        return None


async def _try_series_candidates(
    client: httpx.AsyncClient,
    candidates: List[str],
    api_key: str,
) -> Optional[List[dict]]:
    """Try multiple series ID candidates; return the first successful result."""
    for series_id in candidates:
        result = await _fetch_series(client, series_id, api_key, limit=2)
        if result:
            logger.info("Found working FRED series: %s", series_id)
            return result
    return None


def _compute_pct_change(observations: List[dict]) -> Optional[float]:
    """Compute percentage change between two most recent observations.

    Observations should be in descending date order (newest first).
    """
    if not observations or len(observations) < 2:
        return None
    try:
        current = float(observations[0]["value"])
        previous = float(observations[1]["value"])
        if previous == 0:
            return None
        return round(((current - previous) / previous) * 100, 2)
    except (ValueError, KeyError, TypeError):
        return None


def _extract_latest_value(observations: Optional[List[dict]]) -> Optional[float]:
    """Extract the numeric value from the most recent observation."""
    if not observations:
        return None
    try:
        return float(observations[0]["value"])
    except (ValueError, KeyError, TypeError, IndexError):
        return None


async def fetch_fred_data(city_info: dict) -> Optional[Dict[str, Any]]:
    """Fetch all available FRED data for a single US city.

    Args:
        city_info: City configuration dict from ingest.CITIES.

    Returns:
        Dict with keys: price, price_change_pct, inventory, inventory_change_pct,
        days_on_market, rate — or None if all fetches fail.
    """
    api_key = _get_api_key()
    if not api_key:
        return None

    slug = city_info["slug"]
    candidates = SERIES_CANDIDATES.get(slug, {})
    state_hpi = city_info.get("fred_state_hpi")

    result: Dict[str, Any] = {
        "price": None,
        "price_change_pct": None,
        "inventory": None,
        "inventory_change_pct": None,
        "days_on_market": None,
        "rate": None,
        "bank": "Federal Reserve",
    }

    try:
        async with httpx.AsyncClient() as client:
            # --- Median listing price ---
            price_obs = None
            if "price" in candidates:
                price_obs = await _try_series_candidates(
                    client, candidates["price"], api_key
                )

            # Fallback to state-level HPI if city series unavailable
            if not price_obs and state_hpi:
                logger.info(
                    "City-level price series not found for %s, falling back to state HPI: %s",
                    slug, state_hpi,
                )
                price_obs = await _fetch_series(client, state_hpi, api_key, limit=2)

            if price_obs:
                result["price"] = _extract_latest_value(price_obs)
                result["price_change_pct"] = _compute_pct_change(price_obs)

            # --- Active inventory ---
            if "inventory" in candidates:
                inv_obs = await _try_series_candidates(
                    client, candidates["inventory"], api_key
                )
                if inv_obs:
                    raw_inv = _extract_latest_value(inv_obs)
                    result["inventory"] = int(raw_inv) if raw_inv is not None else None
                    result["inventory_change_pct"] = _compute_pct_change(inv_obs)

            # --- Days on market ---
            if "dom" in candidates:
                dom_obs = await _try_series_candidates(
                    client, candidates["dom"], api_key
                )
                if dom_obs:
                    raw_dom = _extract_latest_value(dom_obs)
                    result["days_on_market"] = (
                        int(raw_dom) if raw_dom is not None else None
                    )

            # --- 30-year mortgage rate (national) ---
            rate_obs = await _fetch_series(client, MORTGAGE_SERIES, api_key, limit=1)
            if rate_obs:
                result["rate"] = _extract_latest_value(rate_obs)

        # Return None if we got absolutely nothing useful
        has_data = any(
            result[k] is not None
            for k in ("price", "inventory", "days_on_market", "rate")
        )
        if not has_data:
            logger.warning("No usable FRED data retrieved for %s", slug)
            return None

        return result

    except Exception as e:
        logger.error("Unexpected error in fetch_fred_data for %s: %s", slug, e)
        return None
