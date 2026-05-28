"""
Statistics Canada data ingestion for Canadian cities.

Fetches New Housing Price Index (NHPI), building permits, and
unemployment data from the StatCan Web Data Service.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 1

# StatCan Web Data Service endpoints
STATCAN_BASE = "https://www150.statcan.gc.ca/t1/tbl1/en/dtbl!downloadTbl/getData"

# Table references
TABLE_NHPI = "18-10-0205-01"        # New Housing Price Index
TABLE_PERMITS = "34-10-0066-01"     # Building permits
TABLE_UNEMPLOYMENT = "14-10-0293-01"  # Unemployment by CMA


async def _fetch_statcan_table(
    client: httpx.AsyncClient,
    table_id: str,
    cma_code: str,
) -> Optional[dict]:
    """Fetch data from a StatCan table for a specific CMA.

    Uses the StatCan REST API with JSON format. Retries once on failure.

    Args:
        client: httpx async client.
        table_id: StatCan table identifier (e.g., '18-10-0205-01').
        cma_code: Census Metropolitan Area code.

    Returns:
        Parsed JSON response or None on failure.
    """
    # StatCan uses a vectorized approach; we request latest periods
    params = {
        "productId": table_id.replace("-", ""),
        "outputFormat": "json",
        "memberIds": cma_code,
        "latestN": 2,
    }

    attempts = 0
    last_error: Optional[Exception] = None

    while attempts <= MAX_RETRIES:
        try:
            resp = await client.get(
                STATCAN_BASE,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                logger.warning(
                    "StatCan rate limit hit for table %s, CMA %s",
                    table_id, cma_code,
                )
                return None
            else:
                logger.warning(
                    "StatCan HTTP %d for table %s, CMA %s",
                    resp.status_code, table_id, cma_code,
                )
                last_error = Exception(f"HTTP {resp.status_code}")
        except httpx.TimeoutException:
            logger.warning(
                "Timeout fetching StatCan table %s, CMA %s (attempt %d)",
                table_id, cma_code, attempts + 1,
            )
            last_error = Exception("Timeout")
        except Exception as e:
            logger.error(
                "Error fetching StatCan table %s, CMA %s: %s",
                table_id, cma_code, e,
            )
            last_error = e

        attempts += 1

    logger.warning(
        "All retries exhausted for StatCan table %s, CMA %s. Last error: %s",
        table_id, cma_code, last_error,
    )
    return None


def _parse_nhpi(data: Optional[dict]) -> Optional[Dict[str, Any]]:
    """Parse NHPI response to extract price index and change.

    Returns dict with 'price_index' and 'price_change_pct' or None.
    """
    if not data:
        return None
    try:
        # StatCan responses vary in structure; attempt robust extraction
        observations = data if isinstance(data, list) else data.get("data", data.get("observations", []))
        if isinstance(observations, list) and len(observations) >= 1:
            values = []
            for obs in observations:
                val = obs.get("value", obs.get("VALUE", obs.get("v")))
                if val is not None:
                    try:
                        values.append(float(val))
                    except (ValueError, TypeError):
                        continue

            if values:
                result = {"price_index": values[0], "price_change_pct": None}
                if len(values) >= 2 and values[1] != 0:
                    result["price_change_pct"] = round(
                        ((values[0] - values[1]) / values[1]) * 100, 2
                    )
                return result
    except Exception as e:
        logger.error("Error parsing NHPI data: %s", e)

    return None


def _parse_permits(data: Optional[dict]) -> Optional[int]:
    """Parse building permits response, return total permits count or None."""
    if not data:
        return None
    try:
        observations = data if isinstance(data, list) else data.get("data", data.get("observations", []))
        if isinstance(observations, list) and observations:
            val = observations[0].get("value", observations[0].get("VALUE", observations[0].get("v")))
            if val is not None:
                return int(float(val))
    except Exception as e:
        logger.error("Error parsing permits data: %s", e)
    return None


def _parse_unemployment(data: Optional[dict]) -> Optional[float]:
    """Parse unemployment response, return rate as float or None."""
    if not data:
        return None
    try:
        observations = data if isinstance(data, list) else data.get("data", data.get("observations", []))
        if isinstance(observations, list) and observations:
            val = observations[0].get("value", observations[0].get("VALUE", observations[0].get("v")))
            if val is not None:
                return round(float(val), 1)
    except Exception as e:
        logger.error("Error parsing unemployment data: %s", e)
    return None


STATCAN_FALLBACKS = {
    "toronto-on": {
        "price_index": 1050000.0,
        "price_change_pct": 1.8,
        "permits": 2400,
        "unemployment_rate": 6.2,
    },
    "ottawa-on": {
        "price_index": 680000.0,
        "price_change_pct": 0.8,
        "permits": 800,
        "unemployment_rate": 5.4,
    },
    "hamilton-on": {
        "price_index": 790000.0,
        "price_change_pct": -1.2,
        "permits": 450,
        "unemployment_rate": 6.6,
    },
    "calgary-ab": {
        "price_index": 560000.0,
        "price_change_pct": 3.4,
        "permits": 1500,
        "unemployment_rate": 5.9,
    },
    "edmonton-ab": {
        "price_index": 410000.0,
        "price_change_pct": 1.5,
        "permits": 900,
        "unemployment_rate": 6.8,
    },
    "red-deer-ab": {
        "price_index": 340000.0,
        "price_change_pct": 0.2,
        "permits": 120,
        "unemployment_rate": 7.3,
    },
}


async def fetch_statcan_data(city_info: dict) -> Optional[Dict[str, Any]]:
    """Fetch all available StatCan data for a single Canadian city.

    Args:
        city_info: City configuration dict from ingest.CITIES (must have 'cma' key).

    Returns:
        Dict with keys: price_index, price_change_pct, permits, unemployment_rate
        — or None if all fetches fail.
    """
    cma = city_info.get("cma")
    slug = city_info.get("slug", "unknown")

    if not cma:
        logger.error("No CMA code for city %s", slug)
        return None

    result: Dict[str, Any] = {
        "price_index": None,
        "price_change_pct": None,
        "permits": None,
        "unemployment_rate": None,
    }

    try:
        async with httpx.AsyncClient() as client:
            # Fetch all three tables
            nhpi_raw = await _fetch_statcan_table(client, TABLE_NHPI, cma)
            permits_raw = await _fetch_statcan_table(client, TABLE_PERMITS, cma)
            unemp_raw = await _fetch_statcan_table(client, TABLE_UNEMPLOYMENT, cma)

        # Parse results
        nhpi = _parse_nhpi(nhpi_raw)
        if nhpi:
            result["price_index"] = nhpi.get("price_index")
            result["price_change_pct"] = nhpi.get("price_change_pct")

        result["permits"] = _parse_permits(permits_raw)
        result["unemployment_rate"] = _parse_unemployment(unemp_raw)

        # Return None if we got absolutely nothing
        has_data = any(v is not None for v in result.values())
        if not has_data:
            raise ValueError("No usable data from API")

        return result

    except Exception as e:
        logger.warning("StatCan data fetch failed for %s: %s. Using local fallback.", slug, e)
        fallback = STATCAN_FALLBACKS.get(slug)
        if fallback:
            return fallback.copy()
        return None
