"""AI Fashion Designer — Application Configuration."""
from __future__ import annotations

import json
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    APP_NAME: str = "AI Fashion Designer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ---- Database ----
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fashionai"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/fashionai"

    # ---- Redis ----
    REDIS_URL: str = "redis://localhost:6379/0"

    # ---- Qdrant ----
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str = "fashion_products"

    # ---- Groq (Primary LLM) ----
    GROQ_API_KEY: str = ""

    # ---- Hugging Face ----
    HF_API_KEY: str = ""

    # ---- Ollama (Local Fallback) ----
    OLLAMA_URL: str = "http://localhost:11434"

    # ---- Supabase ----
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # ---- Cloudflare R2 ----
    R2_ENDPOINT: str = ""
    R2_ACCESS_KEY: str = ""
    R2_SECRET_KEY: str = ""
    R2_BUCKET: str = "fashion-ai-assets"

    # ---- JWT ----
    JWT_SECRET_KEY: str = "change_this_to_a_64_char_random_hex_string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---- Rate Limiting ----
    RATE_LIMIT_PER_USER: int = 30
    RATE_LIMIT_PER_IP: int = 100

    # ---- Langfuse ----
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # ---- PostHog ----
    POSTHOG_API_KEY: str = ""
    POSTHOG_HOST: str = "https://app.posthog.com"

    # ---- FCM ----
    FCM_SERVER_KEY: str = ""

    # ---- CORS ----
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v


# Singleton instance
settings = Settings()
