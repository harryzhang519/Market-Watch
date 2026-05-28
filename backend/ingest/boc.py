"""
Bank of Canada overnight rate ingestion.

Fetches the latest policy interest rate from the Bank of Canada Valet API.
No API key required.
"""

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

BOC_URL = "https://www.bankofcanada.ca/valet/observations/V39079/json"
REQUEST_TIMEOUT = 30.0


async def fetch_boc_rate() -> Optional[Dict[str, Any]]:
    """Fetch the latest Bank of Canada overnight policy rate.

    Returns:
        Dict with keys: rate (float), bank (str) — or None on failure.
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(BOC_URL, timeout=REQUEST_TIMEOUT)

            if resp.status_code != 200:
                logger.warning(
                    "Bank of Canada API returned HTTP %d", resp.status_code
                )
                return None

            data = resp.json()

        # Navigate the Valet API response structure:
        # { "observations": [ { "d": "2024-01-01", "V122530": { "v": "5.00" }, ... }, ... ] }
        observations = data.get("observations", [])
        if not observations:
            logger.warning("No observations in Bank of Canada response")
            return None

        # Latest observation is the last one (chronological order)
        latest = observations[-1]

        # Find the rate value — the key varies but typically starts with 'V'
        rate_value: Optional[float] = None
        for key, val in latest.items():
            if key == "d":
                continue  # skip date field
            if isinstance(val, dict) and "v" in val:
                try:
                    rate_value = float(val["v"])
                    break
                except (ValueError, TypeError):
                    continue

        if rate_value is None:
            logger.warning("Could not extract rate from Bank of Canada response")
            return None

        logger.info("Bank of Canada overnight rate: %.2f%%", rate_value)
        return {
            "rate": rate_value,
            "bank": "Bank of Canada",
        }

    except httpx.TimeoutException:
        logger.warning("Timeout fetching Bank of Canada rate")
        return None
    except httpx.HTTPError as e:
        logger.warning("HTTP error fetching Bank of Canada rate: %s", e)
        return None
    except (KeyError, ValueError, TypeError) as e:
        logger.error("Error parsing Bank of Canada response: %s", e)
        return None
    except Exception as e:
        logger.error("Unexpected error fetching Bank of Canada rate: %s", e)
        return None
