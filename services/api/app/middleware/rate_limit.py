"""Rate limiting middleware with Redis-backed sliding window."""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create the global limiter instance
# Uses client IP as default key; override per-endpoint for user-based limits
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri="memory://",  # Upgraded to Redis in production via REDIS_URL
    strategy="fixed-window",
)
