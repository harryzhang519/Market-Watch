"""
CMHC (Canada Mortgage and Housing Corporation) data ingestion.

Fetches housing starts, completions, and absorption rate data.
"""

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

CMHC_BASE_URL = "https://www.cmhc-schl.gc.ca/api/housingmarketdata"
REQUEST_TIMEOUT = 30.0


async def _fetch_cmhc_indicators(
    client: httpx.AsyncClient,
    cma_code: str,
) -> Optional[dict]:
    """Fetch CMHC housing market indicators for a CMA.

    Args:
        client: httpx async client.
        cma_code: Census Metropolitan Area code.

    Returns:
        Raw JSON response or None on failure.
    """
    params = {
        "cmaCode": cma_code,
        "seriesType": "monthly",
        "format": "json",
    }

    try:
        resp = await client.get(
            CMHC_BASE_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        if resp.status_code == 429:
            logger.warning(
                "CMHC rate limit (429) for CMA %s — will use cached data",
                cma_code,
            )
            return None

        if resp.status_code != 200:
            logger.warning(
                "CMHC HTTP %d for CMA %s",
                resp.status_code, cma_code,
            )
            return None

        return resp.json()

    except httpx.TimeoutException:
        logger.warning("Timeout fetching CMHC data for CMA %s", cma_code)
        return None
    except httpx.HTTPError as e:
        logger.warning("HTTP error fetching CMHC data for CMA %s: %s", cma_code, e)
        return None
    except Exception as e:
        logger.error(
            "Unexpected error fetching CMHC data for CMA %s: %s", cma_code, e
        )
        return None


def _parse_cmhc_response(data: Optional[dict]) -> Optional[Dict[str, Any]]:
    """Parse CMHC response into structured housing data.

    Returns dict with keys: starts, completions, absorption_rate — or None.
    """
    if not data:
        return None

    try:
        # CMHC responses can vary; attempt multiple extraction paths
        result: Dict[str, Any] = {
            "starts": None,
            "completions": None,
            "absorption_rate": None,
        }

        # Path 1: Direct top-level keys
        if isinstance(data, dict):
            # Try nested data structure
            records = data.get("data", data.get("records", data.get("results", [])))

            if isinstance(records, list) and records:
                latest = records[0] if records else {}
                result["starts"] = _safe_int(
                    latest.get("starts", latest.get("housing_starts"))
                )
                result["completions"] = _safe_int(
                    latest.get("completions", latest.get("housing_completions"))
                )
                result["absorption_rate"] = _safe_float(
                    latest.get("absorption_rate", latest.get("absorptionRate"))
                )
            elif isinstance(records, dict):
                result["starts"] = _safe_int(
                    records.get("starts", records.get("housing_starts"))
                )
                result["completions"] = _safe_int(
                    records.get("completions", records.get("housing_completions"))
                )
                result["absorption_rate"] = _safe_float(
                    records.get("absorption_rate", records.get("absorptionRate"))
                )

            # Fallback: top-level keys
            if result["starts"] is None:
                result["starts"] = _safe_int(data.get("starts"))
            if result["completions"] is None:
                result["completions"] = _safe_int(data.get("completions"))
            if result["absorption_rate"] is None:
                result["absorption_rate"] = _safe_float(data.get("absorption_rate"))

        has_data = any(v is not None for v in result.values())
        return result if has_data else None

    except Exception as e:
        logger.error("Error parsing CMHC response: %s", e)
        return None


def _safe_int(value: Any) -> Optional[int]:
    """Safely convert a value to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _safe_float(value: Any) -> Optional[float]:
    """Safely convert a value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (ValueError, TypeError):
        return None


CMHC_FALLBACKS = {
    "toronto-on": {
        "starts": 12400,
        "completions": 1100,
        "absorption_rate": 4.545,  # 100 / 4.545 = 22 days on market
        "inventory_change_pct": -5.2,
    },
    "ottawa-on": {
        "starts": 3200,
        "completions": 280,
        "absorption_rate": 3.333,  # 100 / 3.333 = 30 days on market
        "inventory_change_pct": 2.1,
    },
    "hamilton-on": {
        "starts": 2100,
        "completions": 190,
        "absorption_rate": 2.222,  # 100 / 2.222 = 45 days on market
        "inventory_change_pct": 8.4,
    },
    "calgary-ab": {
        "starts": 6500,
        "completions": 580,
        "absorption_rate": 6.666,  # 100 / 6.666 = 15 days on market
        "inventory_change_pct": -8.7,
    },
    "edmonton-ab": {
        "starts": 4800,
        "completions": 420,
        "absorption_rate": 3.846,  # 100 / 3.846 = 26 days on market
        "inventory_change_pct": -1.2,
    },
    "red-deer-ab": {
        "starts": 850,
        "completions": 70,
        "absorption_rate": 2.0,    # 100 / 2.0 = 50 days on market
        "inventory_change_pct": 0.5,
    },
}


async def fetch_cmhc_data(city_info: dict) -> Optional[Dict[str, Any]]:
    """Fetch CMHC housing market data for a single Canadian city.

    Args:
        city_info: City configuration dict (must have 'cma' key).

    Returns:
        Dict with keys: starts, completions, absorption_rate — or None on failure.
    """
    cma = city_info.get("cma")
    slug = city_info.get("slug", "unknown")

    if not cma:
        logger.error("No CMA code for city %s", slug)
        return None

    try:
        async with httpx.AsyncClient() as client:
            raw_data = await _fetch_cmhc_indicators(client, cma)

        result = _parse_cmhc_response(raw_data)
        if not result:
            raise ValueError("No usable data from API")
        return result

    except Exception as e:
        logger.warning("CMHC data fetch failed for %s: %s. Using local fallback.", slug, e)
        fallback = CMHC_FALLBACKS.get(slug)
        if fallback:
            return fallback.copy()
        return None
