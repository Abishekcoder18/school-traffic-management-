"""
GateFlow AI — PostgreSQL Database Connection
-----------------------------------------
Uses SQLAlchemy 2.x with psycopg driver.
Connection target: configured PostgreSQL schooltraffic database.

Usage:
    from app.db import get_db, engine
    # In a FastAPI route:
    def my_route(db: Session = Depends(get_db)):
        ...
"""
from __future__ import annotations

import logging

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,       # reconnect if connection dropped
    pool_recycle=3600,         # recycle connections every hour
    pool_size=5,
    max_overflow=10,
    echo=settings.debug,       # log SQL when debug=True
    connect_args={
        "connect_timeout": 10,
    },
)

# ── Session Factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ── ORM Base ──────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Dependency — use in FastAPI routes via Depends(get_db) ───────────────────
def get_db():
    """Yield a database session and ensure it is closed after use."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Connectivity Check ────────────────────────────────────────────────────────
def check_db_connection() -> bool:
    """
    Returns True if the PostgreSQL database is reachable, False otherwise.
    Called on startup so the health endpoint can report DB status.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(
            f"✅ PostgreSQL connected: {settings.db_host}:{settings.db_port}/{settings.db_name}"
        )
        return True
    except Exception as exc:
        logger.error(f"❌ PostgreSQL connection failed: {exc}")
        return False
