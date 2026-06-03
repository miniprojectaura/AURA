"""AI Fashion Designer — Async Database Engine and Session."""
from __future__ import annotations

import asyncio
import logging
import ssl
from typing import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

# Naming convention for constraints — makes Alembic migrations deterministic
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy models."""

    metadata = metadata


def _build_connect_args() -> dict:
    """Build connect_args for asyncpg based on the DATABASE_URL.

    For cloud databases (Supabase, Neon, etc.) we need SSL and may need
    to work around IPv6 issues on hosts that only have IPv4 (like Render).
    """
    db_url = settings.DATABASE_URL
    connect_args: dict = {}

    # Enable SSL for cloud databases (anything not localhost/127.0.0.1)
    is_cloud = not any(
        host in db_url
        for host in ("localhost", "127.0.0.1", "postgres:", "host.docker.internal")
    )
    if is_cloud:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_ctx
        # Force IPv4 resolution for Render/Railway compatibility
        connect_args["server_settings"] = {"application_name": "fashion_ai"}

    return connect_args


# Async engine with connection pool
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=_build_connect_args(),
)

# Async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a database session.

    Yields an async session and ensures it is closed after use.
    The session is rolled back on exception, committed on success.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database — create tables if they don't exist.

    Retries up to 3 times with exponential backoff to handle
    transient network issues during cold starts (e.g., on Render).
    """
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables initialized (attempt %d)", attempt)
            return
        except Exception as e:
            if attempt == max_retries:
                logger.error(
                    "Database init failed after %d attempts: %s", max_retries, e
                )
                raise
            wait = 2 ** attempt
            logger.warning(
                "Database init attempt %d failed: %s — retrying in %ds",
                attempt, e, wait,
            )
            await asyncio.sleep(wait)


async def close_db() -> None:
    """Dispose of the database engine connection pool."""
    await engine.dispose()
    logger.info("Database connection pool closed")

