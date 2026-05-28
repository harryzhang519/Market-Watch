"""
FastAPI application for Market Watch — real estate market intelligence dashboard.

Endpoints:
  GET /api/markets           — all city summaries
  GET /api/markets/{slug}    — full detail for one city
  GET /api/refresh           — trigger manual data refresh
"""

import logging
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

# Load environment variables from .env in the backend directory
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_env_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Local imports (after dotenv so env vars are available)
from database import SessionLocal, create_tables, get_db  # noqa: E402
from models import MarketSignal, NewsItem  # noqa: E402
from scheduler import run_full_refresh, start_scheduler, stop_scheduler  # noqa: E402


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup / shutdown lifecycle."""
    logger.info("Market Watch backend starting up…")

    # 1. Create database tables
    try:
        create_tables()
    except Exception as e:
        logger.error("Failed to create database tables: %s", e)

    # 2. Start the background scheduler
    try:
        start_scheduler()
    except Exception as e:
        logger.error("Failed to start scheduler: %s", e)

    # 3. If the DB is empty, kick off an initial fetch in the background
    try:
        db = SessionLocal()
        count = db.query(MarketSignal).count()
        db.close()
        if count == 0:
            logger.info("Database is empty — running initial data fetch in background")
            t = threading.Thread(target=run_full_refresh, daemon=True)
            t.start()
    except Exception as e:
        logger.error("Error checking initial DB state: %s", e)

    yield  # Application is running

    # Shutdown
    logger.info("Market Watch backend shutting down…")
    try:
        stop_scheduler()
    except Exception as e:
        logger.error("Error stopping scheduler: %s", e)


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Market Watch API",
    description="Real estate market intelligence for 12 cities across 4 regions.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all local and remote dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/markets", response_class=JSONResponse)
def get_all_markets(db: Session = Depends(get_db)):
    """Return summary signals for all tracked cities.

    Each city summary includes the latest news headline (if available).
    """
    try:
        signals: List[MarketSignal] = (
            db.query(MarketSignal)
            .order_by(MarketSignal.region, MarketSignal.city)
            .all()
        )

        results = []
        for signal in signals:
            summary = signal.to_summary_dict()

            # Attach the most recent headline for this city
            latest_news: Optional[NewsItem] = (
                db.query(NewsItem)
                .filter(NewsItem.city_slug == signal.city_slug)
                .order_by(NewsItem.fetched_at.desc())
                .first()
            )
            summary["top_news_headline"] = (
                latest_news.headline if latest_news else None
            )

            results.append(summary)

        return results

    except Exception as e:
        logger.error("Error in GET /api/markets: %s", e)
        return JSONResponse(
            status_code=200,
            content={"cities": [], "error": "Data temporarily unavailable"},
        )


@app.get("/api/markets/{city_slug}", response_class=JSONResponse)
def get_market_detail(city_slug: str, db: Session = Depends(get_db)):
    """Return full market detail and recent news for a single city."""
    try:
        signal: Optional[MarketSignal] = (
            db.query(MarketSignal)
            .filter(MarketSignal.city_slug == city_slug)
            .first()
        )

        if not signal:
            return JSONResponse(
                status_code=404,
                content={"error": f"City '{city_slug}' not found"},
            )

        detail = signal.to_detail_dict()

        # Fetch 5 most recent news items
        news_items: List[NewsItem] = (
            db.query(NewsItem)
            .filter(NewsItem.city_slug == city_slug)
            .order_by(NewsItem.fetched_at.desc())
            .limit(5)
            .all()
        )

        detail["news"] = [item.to_dict() for item in news_items]

        return detail

    except Exception as e:
        logger.error("Error in GET /api/markets/%s: %s", city_slug, e)
        return JSONResponse(
            status_code=200,
            content={
                "city_slug": city_slug,
                "error": "Data temporarily unavailable",
                "news": [],
            },
        )


class SimulationRequest(BaseModel):
    headline: str


@app.post("/api/markets/{city_slug}/simulate")
async def simulate_market_signal(city_slug: str, req: SimulationRequest, db: Session = Depends(get_db)):
    """Simulate a market signal interpretation with a custom news headline in real-time.

    This endpoint ALWAYS returns a valid result. If Gemini is unavailable
    (rate limit, quota, key issues), it falls back to a rule-based local
    interpretation engine so the sandbox never shows an error.
    """
    try:
        from interpret import interpret_city

        signal: Optional[MarketSignal] = (
            db.query(MarketSignal)
            .filter(MarketSignal.city_slug == city_slug)
            .first()
        )

        if not signal:
            return JSONResponse(
                status_code=404,
                content={"error": f"City '{city_slug}' not found. Try refreshing market data first."},
            )

        # Build market data block from the current database values
        market_data = {
            "price": signal.median_price,
            "price_change_pct": signal.price_change_pct,
            "inventory": signal.inventory,
            "inventory_change_pct": signal.inventory_change_pct,
            "days_on_market": signal.days_on_market,
            "rate": signal.rate,
            "bank": signal.bank,
        }

        # Run interpretation using the custom headline
        # interpret_city now always returns a result (never None) via
        # retry → model fallback → local rule-based fallback
        interpreted = await interpret_city(
            city_name=signal.city,
            region=signal.region,
            market_data=market_data,
            news_headlines=[req.headline]
        )

        # Determine the interpretation source for UI transparency
        source = interpreted.get("_source", "gemini")
        is_fallback = source == "local_fallback"

        # Merge it with city metadata to match standard detail structure
        simulated_detail = {
            "city": signal.city,
            "region": signal.region,
            "city_slug": signal.city_slug,
            "direction": interpreted.get("direction", "stable"),
            "confidence": interpreted.get("confidence", "low"),
            "explanation": interpreted.get("explanation", "Simulation explanation."),
            "key_driver": interpreted.get("key_driver", "Simulated driver"),
            "severity": interpreted.get("severity", 3),
            "notable_event": interpreted.get("notable_event", req.headline),
            "median_price": signal.median_price,
            "price_change_pct": signal.price_change_pct,
            "inventory": signal.inventory,
            "inventory_change_pct": signal.inventory_change_pct,
            "days_on_market": signal.days_on_market,
            "rate": signal.rate,
            "bank": signal.bank,
            "last_updated": signal.last_updated.isoformat() if signal.last_updated else None,
            "is_stale": False,
            "is_simulation": True,
            "interpretation_source": source,
            "is_fallback": is_fallback,
            "news": [
                {
                    "id": 9999,
                    "city": signal.city,
                    "headline": req.headline,
                    "url": "#",
                    "source_name": "Broker Simulation Sandbox",
                    "published_at": None,
                    "fetched_at": None
                }
            ]
        }

        return simulated_detail

    except Exception as e:
        logger.error("Error in POST /api/markets/%s/simulate: %s", city_slug, e, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"Server error during simulation. Please try again in a moment. Detail: {str(e)}"},
        )


@app.get("/api/refresh", response_class=JSONResponse)
def trigger_refresh():
    """Manually trigger a full data refresh in the background.

    Returns immediately — the refresh runs asynchronously.
    """
    try:
        t = threading.Thread(target=run_full_refresh, daemon=True)
        t.start()
        logger.info("Manual refresh triggered")
        return {"status": "refresh started"}
    except Exception as e:
        logger.error("Error triggering manual refresh: %s", e)
        return JSONResponse(
            status_code=200,
            content={"status": "refresh failed to start", "error": str(e)},
        )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "market-watch-backend"}


# ---------------------------------------------------------------------------
# Development entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
