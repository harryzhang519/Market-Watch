"""
Database configuration and session management for Market Watch.

Uses SQLite with SQLAlchemy 2.0+ style engine and session factory.
"""

import logging
import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)

# Database file lives alongside this module
DB_DIR = Path(__file__).resolve().parent
DB_PATH = DB_DIR / "market_watch.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite + FastAPI
    echo=False,
    pool_pre_ping=True,
)


# Enable WAL mode for better concurrent read performance
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """Create all tables defined by ORM models.

    Safe to call multiple times — SQLAlchemy will skip existing tables.
    """
    # Import models so they register with Base.metadata
    import models  # noqa: F401

    logger.info("Creating database tables (if not existing) at %s", DB_PATH)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready.")
