"""Password hashing and OTP generation."""
from __future__ import annotations

import logging
import secrets
import string
from typing import Optional

from passlib.context import CryptContext

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP for phone verification."""
    return "".join(secrets.choice(string.digits) for _ in range(length))


async def store_otp(redis_client, phone: str, otp: str, ttl: int = 300) -> None:
    """Store OTP in Redis with 5-minute TTL."""
    if redis_client:
        await redis_client.setex(f"otp:{phone}", ttl, otp)
        logger.info("OTP stored for phone: %s***", phone[:4])


async def verify_otp(redis_client, phone: str, otp: str) -> bool:
    """Verify OTP from Redis and delete on success."""
    if redis_client is None:
        logger.warning("Redis not available — OTP verification skipped")
        return False
    stored_otp = await redis_client.get(f"otp:{phone}")
    if stored_otp and stored_otp == otp:
        await redis_client.delete(f"otp:{phone}")
        return True
    return False
