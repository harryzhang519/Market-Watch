"""
News ingestion via NewsAPI.

Fetches the latest real estate / housing headlines for a given city.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

NEWSAPI_URL = "https://newsapi.org/v2/everything"
REQUEST_TIMEOUT = 30.0


def _get_api_key() -> Optional[str]:
    """Retrieve the NewsAPI key from environment."""
    key = os.getenv("NEWS_API_KEY") or os.getenv("NEWSAPI_KEY")
    if not key:
        logger.warning(
            "NEWS_API_KEY or NEWSAPI_KEY not set in environment. News data will be unavailable. "
            "Get a key at https://newsapi.org/register"
        )
    return key


def _parse_published_at(date_str: Optional[str]) -> Optional[datetime]:
    """Parse an ISO 8601 date string into a UTC datetime."""
    if not date_str:
        return None
    try:
        # NewsAPI uses ISO 8601 with trailing 'Z'
        cleaned = date_str.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return None


def _get_country_for_city(city_name: str) -> str:
    """Look up which country a city belongs to in the configuration."""
    try:
        from ingest import CITIES
        name_clean = city_name.lower().replace(" city", "").strip()
        for region, cities in CITIES.items():
            for city in cities:
                c_name = city["name"].lower().replace(" city", "").strip()
                if name_clean == c_name or name_clean in c_name or c_name in name_clean:
                    return city.get("country", "US")
    except Exception as e:
        logger.error("Error looking up country for city %s: %s", city_name, e)
    return "US"


RELEVANT_KEYWORDS = [
    "house", "housing", "price", "permit", "rent", "mortgage", 
    "rate", "zoning", "rezoning", "employer", "hiring", "layoff", 
    "economic", "inflation", "bank", "fed", "interest", "real estate", 
    "property", "building", "home", "condo", "apartment", "market", 
    "develop", "construction", "policy", "monetary"
]


def _is_relevant(headline: str) -> bool:
    """Check if the headline contains at least one relevant keyword."""
    if not headline:
        return False
    lower_headline = headline.lower()
    return any(keyword in lower_headline for keyword in RELEVANT_KEYWORDS)


async def _query_newsapi(client: httpx.AsyncClient, query: str, api_key: str) -> List[Dict[str, Any]]:
    """Helper to query NewsAPI and return parsed articles."""
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 10,  # Fetch more so we have a pool to filter
        "apiKey": api_key,
    }
    
    try:
        resp = await client.get(NEWSAPI_URL, params=params, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            logger.warning("NewsAPI returned HTTP %d for query '%s'", resp.status_code, query)
            return []
            
        data = resp.json()
        if data.get("status") != "ok":
            return []
            
        articles = data.get("articles", [])
        results = []
        for article in articles:
            if not article:
                continue
            title = article.get("title", "")
            if not title or title == "[Removed]":
                continue
                
            results.append({
                "headline": title,
                "url": article.get("url", ""),
                "source_name": article.get("source", {}).get("name", "Unknown"),
                "published_at": _parse_published_at(article.get("publishedAt")),
            })
        return results
    except Exception as e:
        logger.error("Error in _query_newsapi for query '%s': %s", query, e)
        return []


async def fetch_news(city_name: str) -> List[Dict[str, Any]]:
    """Fetch recent real estate news headlines for a city.
    
    Uses hyperfocused queries, Python keyword filtering, and macroeconomic fallback
    (Fed rate decisions for US, BoC overnight rate decisions for Canada).
    """
    api_key = _get_api_key()
    if not api_key:
        return []

    country = _get_country_for_city(city_name)
    
    # 1. Hyperfocused local query
    topics = (
        '"real estate" OR "housing market" OR "mortgage" OR '
        '"zoning" OR "rezoning" OR "interest rate" OR "overnight rate" OR '
        '"inflation" OR "home price" OR "housing construction" OR '
        '"major employer" OR "job growth" OR "hiring"'
    )
    negatives = (
        '-sports -NFL -NHL -football -basketball -hockey -soccer -baseball '
        '-museum -biennial -concert -album -theatre -movie -artist -celebrity'
    )
    
    local_query = f'"{city_name}" AND ({topics}) {negatives}'
    
    results: List[Dict[str, Any]] = []
    
    try:
        async with httpx.AsyncClient() as client:
            # Query local headlines
            local_articles = await _query_newsapi(client, local_query, api_key)
            
            # Filter locally relevant ones
            for art in local_articles:
                if _is_relevant(art["headline"]):
                    results.append(art)
                    
            # 2. If we have fewer than 3 local articles, trigger macro fallback
            if len(results) < 3:
                logger.info(
                    "Fewer than 3 local articles for %s (%d found). Running macroeconomic fallback query.",
                    city_name, len(results)
                )
                
                if country == "CA":
                    macro_query = '"Bank of Canada" AND ("interest rate" OR "overnight rate" OR "inflation" OR "housing market")'
                else:
                    macro_query = '"Federal Reserve" AND ("interest rate" OR "inflation" OR "mortgage rate" OR "housing market")'
                
                macro_articles = await _query_newsapi(client, macro_query, api_key)
                
                for art in macro_articles:
                    # Skip duplicate URLs
                    if any(r["url"] == art["url"] for r in results):
                        continue
                    if _is_relevant(art["headline"]):
                        results.append(art)
                        
        # Remove any duplicates just in case and limit to 5
        seen_urls = set()
        final_results = []
        for art in results:
            if art["url"] not in seen_urls:
                seen_urls.add(art["url"])
                final_results.append(art)
                if len(final_results) >= 5:
                    break
                    
        logger.info("Successfully ingested %d focused news articles for '%s'", len(final_results), city_name)
        return final_results
        
    except Exception as e:
        logger.error("Unexpected error in fetch_news for '%s': %s", city_name, e)
        return []
