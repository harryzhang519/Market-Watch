"""
APScheduler-based background jobs for Market Watch.

Orchestrates the full data refresh cycle:
1. Fetch market data (FRED for US, StatCan+CMHC+BoC for CA)
2. Fetch news for every city
3. Run Gemini interpretation for each city
4. Persist results to the database
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from database import SessionLocal
from models import MarketSignal, NewsItem

logger = logging.getLogger(__name__)

# Module-level scheduler instance
scheduler = BackgroundScheduler(daemon=True)


# ---------------------------------------------------------------------------
# Async helpers — APScheduler's BackgroundScheduler uses threads, so we spin
# up a fresh event loop for each job execution to run async ingest functions.
# ---------------------------------------------------------------------------

def _run_async(coro):
    """Run an async coroutine synchronously in a new event loop.

    Safe to call from an APScheduler thread pool.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _fetch_us_city_data(city_info: dict) -> Optional[Dict[str, Any]]:
    """Fetch FRED data for a single US city."""
    from ingest.fred import fetch_fred_data
    return await fetch_fred_data(city_info)


async def _fetch_ca_city_data(city_info: dict) -> Optional[Dict[str, Any]]:
    """Fetch StatCan + CMHC + BoC data for a single Canadian city.

    Merges results from all three sources into a unified dict that matches
    the structure expected by the interpreter.
    """
    from ingest.statcan import fetch_statcan_data
    from ingest.cmhc import fetch_cmhc_data
    from ingest.boc import fetch_boc_rate

    statcan = await fetch_statcan_data(city_info)
    cmhc = await fetch_cmhc_data(city_info)
    boc = await fetch_boc_rate()

    # Build unified market data dict
    result: Dict[str, Any] = {
        "price": None,
        "price_change_pct": None,
        "inventory": None,
        "inventory_change_pct": None,
        "days_on_market": None,
        "rate": None,
        "bank": None,
    }

    # From StatCan NHPI
    if statcan:
        result["price"] = statcan.get("price_index")
        result["price_change_pct"] = statcan.get("price_change_pct")

    # From CMHC — use starts as a proxy for inventory/supply
    if cmhc:
        result["inventory"] = cmhc.get("starts")
        result["inventory_change_pct"] = cmhc.get("inventory_change_pct")
        # Absorption rate can proxy days-on-market behavior
        absorption = cmhc.get("absorption_rate")
        if absorption is not None:
            try:
                # Convert absorption rate (%) to rough days-on-market equivalent
                # Higher absorption → lower DOM, lower absorption → higher DOM
                result["days_on_market"] = max(1, int(100 / max(absorption, 1)))
            except (ValueError, TypeError, ZeroDivisionError):
                pass

    # From Bank of Canada
    if boc:
        result["rate"] = boc.get("rate")
        result["bank"] = boc.get("bank")

    has_data = any(
        result[k] is not None for k in ("price", "inventory", "rate")
    )
    return result if has_data else None


async def _fetch_city_news(city_name: str) -> List[Dict[str, Any]]:
    """Fetch news for a single city."""
    from ingest.news import fetch_news
    return await fetch_news(city_name)


async def _interpret(
    city_name: str,
    region: str,
    market_data: Optional[Dict[str, Any]],
    headlines: List[str],
) -> Optional[dict]:
    """Run Gemini interpretation for a single city."""
    from interpret import interpret_city
    return await interpret_city(city_name, region, market_data, headlines)


# ---------------------------------------------------------------------------
# Database persistence
# ---------------------------------------------------------------------------

def _upsert_market_signal(
    db: Session,
    city_info: dict,
    region: str,
    market_data: Optional[Dict[str, Any]],
    signal: Optional[dict],
) -> None:
    """Create or update the MarketSignal row for a city."""
    slug = city_info["slug"]
    now = datetime.now(timezone.utc)

    try:
        existing = db.query(MarketSignal).filter(
            MarketSignal.city_slug == slug
        ).first()

        if signal:
            values = {
                "city": city_info["name"],
                "region": region,
                "city_slug": slug,
                "direction": signal.get("direction", "stable"),
                "confidence": signal.get("confidence", "low"),
                "explanation": signal.get("explanation", ""),
                "key_driver": signal.get("key_driver", ""),
                "severity": signal.get("severity", 1),
                "notable_event": signal.get("notable_event"),
                "last_updated": now,
                "is_stale": False,
            }
        elif existing:
            # No new signal — mark existing as stale
            existing.is_stale = True
            existing.last_updated = now
            # Update market data even when signal fails
            values = None
        else:
            # No existing record and no signal — create a minimal stub
            values = {
                "city": city_info["name"],
                "region": region,
                "city_slug": slug,
                "direction": "stable",
                "confidence": "low",
                "explanation": "Awaiting initial analysis.",
                "key_driver": "Insufficient data",
                "severity": 1,
                "notable_event": None,
                "last_updated": now,
                "is_stale": True,
            }

        # Attach market data if available
        md = market_data or {}
        market_fields = {
            "median_price": md.get("price"),
            "price_change_pct": md.get("price_change_pct"),
            "inventory": md.get("inventory"),
            "inventory_change_pct": md.get("inventory_change_pct"),
            "days_on_market": md.get("days_on_market"),
            "rate": md.get("rate"),
            "bank": md.get("bank"),
        }

        if existing:
            if values:
                for k, v in {**values, **market_fields}.items():
                    setattr(existing, k, v)
            else:
                # Only update market data fields
                for k, v in market_fields.items():
                    if v is not None:
                        setattr(existing, k, v)
        else:
            if values:
                record = MarketSignal(**{**values, **market_fields})
                db.add(record)

        db.commit()
        logger.info("Upserted MarketSignal for %s (stale=%s)", slug, not bool(signal))

    except Exception as e:
        db.rollback()
        logger.error("Failed to upsert MarketSignal for %s: %s", slug, e)


def _save_news_items(
    db: Session,
    city_info: dict,
    news_articles: List[Dict[str, Any]],
) -> None:
    """Persist fetched news articles to the database."""
    slug = city_info["slug"]
    now = datetime.now(timezone.utc)

    try:
        for article in news_articles:
            # Skip duplicates based on URL
            existing = db.query(NewsItem).filter(
                NewsItem.city_slug == slug,
                NewsItem.url == article.get("url", ""),
            ).first()
            if existing:
                continue

            item = NewsItem(
                city=city_info["name"],
                city_slug=slug,
                headline=article.get("headline", ""),
                url=article.get("url", ""),
                source_name=article.get("source_name", "Unknown"),
                published_at=article.get("published_at"),
                fetched_at=now,
            )
            db.add(item)

        db.commit()
        logger.info("Saved %d news items for %s", len(news_articles), slug)

    except Exception as e:
        db.rollback()
        logger.error("Failed to save news items for %s: %s", slug, e)


# ---------------------------------------------------------------------------
# Main refresh orchestration
# ---------------------------------------------------------------------------

def run_full_refresh() -> None:
    """Execute a complete data refresh for all 12 cities.

    This function is called by the scheduler and can also be triggered manually.
    It runs synchronously (spins up event loops for async operations).
    """
    from ingest import get_all_cities

    logger.info("=== Starting full market data refresh ===")
    cities = get_all_cities()
    db = SessionLocal()

    try:
        for region, city_info in cities:
            slug = city_info["slug"]
            city_name = city_info["name"]
            country = city_info["country"]

            logger.info("Processing %s (%s, %s)", city_name, region, country)

            # --- Step 1: Fetch market data ---
            market_data: Optional[Dict[str, Any]] = None
            try:
                if country == "US":
                    market_data = _run_async(_fetch_us_city_data(city_info))
                else:
                    market_data = _run_async(_fetch_ca_city_data(city_info))
            except Exception as e:
                logger.error("Market data fetch failed for %s: %s", slug, e)

            # --- Step 2: Fetch news ---
            news_articles: List[Dict[str, Any]] = []
            try:
                news_articles = _run_async(_fetch_city_news(city_name))
            except Exception as e:
                logger.error("News fetch failed for %s: %s", slug, e)

            # --- Step 3: Run Gemini interpretation ---
            headlines = [a.get("headline", "") for a in news_articles if a.get("headline")]
            signal: Optional[dict] = None
            try:
                signal = _run_async(
                    _interpret(city_name, region, market_data, headlines)
                )
            except Exception as e:
                logger.error("Interpretation failed for %s: %s", slug, e)

            # --- Step 4: Persist to database ---
            _upsert_market_signal(db, city_info, region, market_data, signal)
            _save_news_items(db, city_info, news_articles)

        logger.info("=== Full market data refresh complete ===")

    except Exception as e:
        logger.error("Critical error during full refresh: %s", e)
    finally:
        db.close()


def run_news_only_refresh() -> None:
    """Fetch and persist news for all cities without re-running interpretation."""
    from ingest import get_all_cities

    logger.info("=== Starting news-only refresh ===")
    cities = get_all_cities()
    db = SessionLocal()

    try:
        for _region, city_info in cities:
            city_name = city_info["name"]
            slug = city_info["slug"]

            try:
                news_articles = _run_async(_fetch_city_news(city_name))
                _save_news_items(db, city_info, news_articles)
            except Exception as e:
                logger.error("News refresh failed for %s: %s", slug, e)

        logger.info("=== News-only refresh complete ===")

    except Exception as e:
        logger.error("Critical error during news refresh: %s", e)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Scheduler setup
# ---------------------------------------------------------------------------

def start_scheduler() -> None:
    """Configure and start the background scheduler.

    Jobs:
    - Full data refresh: every 6 hours
    - News-only refresh: once per day (at hour 3, 9, 15, 21 offsets from full)
    """
    if scheduler.running:
        logger.warning("Scheduler is already running")
        return

    # Full refresh every 6 hours
    scheduler.add_job(
        run_full_refresh,
        trigger=IntervalTrigger(hours=6),
        id="full_refresh",
        name="Full market data refresh",
        replace_existing=True,
        max_instances=1,
    )

    # News-only refresh daily (offset from full refresh)
    scheduler.add_job(
        run_news_only_refresh,
        trigger=IntervalTrigger(hours=24),
        id="news_refresh",
        name="News-only refresh",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    logger.info("Background scheduler started with full (6h) and news (24h) refresh jobs")


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
