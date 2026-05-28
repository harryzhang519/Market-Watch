"""
City configuration and helper utilities for the ingest package.

All 12 tracked cities across 4 regions (Ohio, New York, Ontario, Alberta).
"""

from typing import Dict, List, Tuple

CITIES: Dict[str, List[dict]] = {
    "Ohio": [
        {
            "name": "Columbus",
            "slug": "columbus-oh",
            "state": "OH",
            "country": "US",
            "fred_msa": "18140",
            "fred_prefix": "COLS",
            "fred_state_hpi": "OHSTHPI",
        },
        {
            "name": "Cleveland",
            "slug": "cleveland-oh",
            "state": "OH",
            "country": "US",
            "fred_msa": "17460",
            "fred_prefix": "CLEV",
            "fred_state_hpi": "OHSTHPI",
        },
        {
            "name": "Cincinnati",
            "slug": "cincinnati-oh",
            "state": "OH",
            "country": "US",
            "fred_msa": "17140",
            "fred_prefix": "CINC",
            "fred_state_hpi": "OHSTHPI",
        },
    ],
    "New York": [
        {
            "name": "New York City",
            "slug": "new-york-city-ny",
            "state": "NY",
            "country": "US",
            "fred_msa": "35620",
            "fred_prefix": "NEWY",
            "fred_state_hpi": "NYSTHPI",
        },
        {
            "name": "Buffalo",
            "slug": "buffalo-ny",
            "state": "NY",
            "country": "US",
            "fred_msa": "15380",
            "fred_prefix": "BUFF",
            "fred_state_hpi": "NYSTHPI",
        },
        {
            "name": "Albany",
            "slug": "albany-ny",
            "state": "NY",
            "country": "US",
            "fred_msa": "10580",
            "fred_prefix": "ALBA",
            "fred_state_hpi": "NYSTHPI",
        },
    ],
    "Ontario": [
        {
            "name": "Toronto",
            "slug": "toronto-on",
            "province": "ON",
            "country": "CA",
            "cma": "535",
        },
        {
            "name": "Ottawa",
            "slug": "ottawa-on",
            "province": "ON",
            "country": "CA",
            "cma": "505",
        },
        {
            "name": "Hamilton",
            "slug": "hamilton-on",
            "province": "ON",
            "country": "CA",
            "cma": "537",
        },
    ],
    "Alberta": [
        {
            "name": "Calgary",
            "slug": "calgary-ab",
            "province": "AB",
            "country": "CA",
            "cma": "825",
        },
        {
            "name": "Edmonton",
            "slug": "edmonton-ab",
            "province": "AB",
            "country": "CA",
            "cma": "835",
        },
        {
            "name": "Red Deer",
            "slug": "red-deer-ab",
            "province": "AB",
            "country": "CA",
            "cma": "820",
        },
    ],
}


def get_all_cities() -> List[Tuple[str, dict]]:
    """Flatten CITIES dict into list of (region, city_info) tuples."""
    result: List[Tuple[str, dict]] = []
    for region, cities in CITIES.items():
        for city in cities:
            result.append((region, city))
    return result


def get_us_cities() -> List[Tuple[str, dict]]:
    """Return only US cities as (region, city_info) tuples."""
    return [(r, c) for r, c in get_all_cities() if c["country"] == "US"]


def get_ca_cities() -> List[Tuple[str, dict]]:
    """Return only Canadian cities as (region, city_info) tuples."""
    return [(r, c) for r, c in get_all_cities() if c["country"] == "CA"]
