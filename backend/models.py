"""
SQLAlchemy ORM models for Market Watch.

Two core tables:
- MarketSignal: one row per city, updated every refresh cycle
- NewsItem: recent headlines per city, appended on each news fetch
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class MarketSignal(Base):
    """Represents the current market signal for a single city."""

    __tablename__ = "market_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    city_slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)

    # AI-interpreted signal
    direction: Mapped[str] = mapped_column(String(20), nullable=False, default="stable")
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    key_driver: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    severity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notable_event: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Market data
    median_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_change_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    inventory: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    inventory_change_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    days_on_market: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bank: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Metadata
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def to_summary_dict(self) -> dict:
        """Compact representation for the /api/markets list endpoint."""
        return {
            "city": self.city,
            "region": self.region,
            "city_slug": self.city_slug,
            "direction": self.direction,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "severity": self.severity,
            "key_driver": self.key_driver,
            "notable_event": self.notable_event,
            "median_price": self.median_price,
            "price_change_pct": self.price_change_pct,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "is_stale": self.is_stale,
        }

    def to_detail_dict(self) -> dict:
        """Full representation for the /api/markets/{slug} endpoint."""
        return {
            "city": self.city,
            "region": self.region,
            "city_slug": self.city_slug,
            "direction": self.direction,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "key_driver": self.key_driver,
            "severity": self.severity,
            "notable_event": self.notable_event,
            "median_price": self.median_price,
            "price_change_pct": self.price_change_pct,
            "inventory": self.inventory,
            "inventory_change_pct": self.inventory_change_pct,
            "days_on_market": self.days_on_market,
            "rate": self.rate,
            "bank": self.bank,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "is_stale": self.is_stale,
        }


class NewsItem(Base):
    """A single news headline associated with a city."""

    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    city_slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    headline: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Composite index for efficient city+date queries
    __table_args__ = (
        Index("ix_news_city_fetched", "city_slug", "fetched_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "city": self.city,
            "headline": self.headline,
            "url": self.url,
            "source_name": self.source_name,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
        }
