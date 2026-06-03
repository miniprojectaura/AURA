"""AI Fashion Designer — FastAPI Application Factory."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import close_db, init_db
from app.api.v1.router import api_router
from app.middleware.rate_limit import limiter
from app.utils.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle — startup and shutdown events."""
    # ---- Startup ----
    setup_logging(settings.LOG_LEVEL)
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Initialize Redis connection pool
    try:
        if not settings.REDIS_URL or settings.REDIS_URL == "redis://localhost:6379/0":
            raise ValueError("No production Redis configured")
        app.state.redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
        await app.state.redis.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning("Redis not available: %s — running without cache", e)
        app.state.redis = None

    # Initialize Qdrant client
    try:
        from qdrant_client import QdrantClient

        qdrant_kwargs = {"url": settings.QDRANT_URL, "timeout": 30}
        if settings.QDRANT_API_KEY:
            qdrant_kwargs["api_key"] = settings.QDRANT_API_KEY
        app.state.qdrant = QdrantClient(**qdrant_kwargs)
        logger.info("Qdrant connected at %s", settings.QDRANT_URL)
    except Exception as e:
        logger.warning("Qdrant not available: %s", e)
        app.state.qdrant = None

    logger.info("Application startup complete")
    yield

    # ---- Shutdown ----
    logger.info("Shutting down application")
    if app.state.redis:
        await app.state.redis.close()
        logger.info("Redis disconnected")
    await close_db()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-Powered Personal Fashion Designer — Multi-agent conversational AI for personalized fashion",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ---- Middleware ----

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate Limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Prometheus metrics
    Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/health", "/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics")

    # ---- Exception Handlers ----

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred. Please try again later.",
            },
        )

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "message": f"Path {request.url.path} not found"},
        )

    # ---- Routes ----

    @app.get("/health", tags=["System"])
    async def health_check(request: Request) -> dict:
        """System health check — verifies database, Redis, and Qdrant connectivity."""
        services_status = {}

        # Check database
        try:
            from app.database import engine
            from sqlalchemy import text

            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            services_status["database"] = "connected"
        except Exception:
            services_status["database"] = "disconnected"

        # Check Redis
        try:
            if request.app.state.redis:
                await request.app.state.redis.ping()
                services_status["redis"] = "connected"
            else:
                services_status["redis"] = "not_configured"
        except Exception:
            services_status["redis"] = "disconnected"

        # Check Qdrant
        try:
            if request.app.state.qdrant:
                request.app.state.qdrant.get_collections()
                services_status["qdrant"] = "connected"
            else:
                services_status["qdrant"] = "not_configured"
        except Exception:
            services_status["qdrant"] = "disconnected"

        overall = "healthy" if all(
            v in ("connected", "not_configured")
            for v in services_status.values()
        ) else "degraded"

        return {
            "status": overall,
            "version": settings.APP_VERSION,
            "services": services_status,
        }

    # Include API router
    app.include_router(api_router, prefix="/api/v1")

    return app


# Application instance
app = create_app()
