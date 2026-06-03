"""
Two-tier caching service with L1 (in-process LRU) and L2 (Redis).

L1 provides sub-millisecond lookups for hot keys with a configurable TTL.
L2 uses Redis for shared, distributed caching across API instances.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Callable, Optional

import redis.asyncio as aioredis
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------
DEFAULT_L1_MAX_SIZE = 1024
DEFAULT_L1_TTL_SECONDS = 300  # 5 minutes
DEFAULT_L2_TTL_SECONDS = 3600  # 1 hour
REDIS_URL_DEFAULT = "redis://localhost:6379/0"


# ---------------------------------------------------------------------------
# Pydantic helpers
# ---------------------------------------------------------------------------

class CacheEntry(BaseModel):
    """Wrapper stored inside L1 to track expiry."""
    value: Any
    expires_at: float


# ---------------------------------------------------------------------------
# L1 LRU Cache with TTL
# ---------------------------------------------------------------------------

class L1Cache:
    """Thread-safe, TTL-aware LRU cache backed by an OrderedDict."""

    def __init__(self, max_size: int = DEFAULT_L1_MAX_SIZE, ttl: int = DEFAULT_L1_TTL_SECONDS):
        self._max_size = max_size
        self._ttl = ttl
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()

    # -- public API --------------------------------------------------------

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry.expires_at:
                self._store.pop(key, None)
                return None
            # Mark as recently used
            self._store.move_to_end(key)
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        effective_ttl = ttl if ttl is not None else self._ttl
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = CacheEntry(
                value=value,
                expires_at=time.monotonic() + effective_ttl,
            )
            # Evict oldest if over capacity
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def invalidate_pattern(self, pattern: str) -> int:
        """Remove all keys that contain *pattern* as a substring (glob-lite)."""
        import fnmatch

        removed = 0
        with self._lock:
            keys_to_remove = [
                k for k in self._store if fnmatch.fnmatch(k, pattern)
            ]
            for k in keys_to_remove:
                del self._store[k]
                removed += 1
        return removed

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)


# ---------------------------------------------------------------------------
# Main CacheService
# ---------------------------------------------------------------------------

class CacheService:
    """
    Two-tier cache:
      L1 – in-process LRU (fast, per-worker)
      L2 – Redis (shared across workers)
    """

    def __init__(
        self,
        redis_url: str = REDIS_URL_DEFAULT,
        l1_max_size: int = DEFAULT_L1_MAX_SIZE,
        l1_ttl: int = DEFAULT_L1_TTL_SECONDS,
        l2_ttl: int = DEFAULT_L2_TTL_SECONDS,
        key_prefix: str = "fashion_ai:",
    ):
        self._redis_url = redis_url
        self._l1 = L1Cache(max_size=l1_max_size, ttl=l1_ttl)
        self._l2_ttl = l2_ttl
        self._key_prefix = key_prefix
        self._redis: Optional[aioredis.Redis] = None
        self._redis_available = True
        logger.info(
            "CacheService initialised – L1 max=%d ttl=%ds, L2 ttl=%ds",
            l1_max_size,
            l1_ttl,
            l2_ttl,
        )

    # -- lifecycle ---------------------------------------------------------

    async def connect(self) -> None:
        """Create the Redis connection pool."""
        try:
            self._redis = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )
            await self._redis.ping()
            self._redis_available = True
            logger.info("CacheService connected to Redis at %s", self._redis_url)
        except Exception:
            self._redis_available = False
            logger.warning(
                "Redis unavailable at %s – running with L1 cache only",
                self._redis_url,
                exc_info=True,
            )

    async def disconnect(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()  # type: ignore[union-attr]
            logger.info("CacheService disconnected from Redis")

    # -- key helpers -------------------------------------------------------

    def _full_key(self, key: str) -> str:
        return f"{self._key_prefix}{key}"

    @staticmethod
    def make_key(*parts: str) -> str:
        """Build a deterministic cache key from variable parts."""
        raw = ":".join(str(p) for p in parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    # -- serialisation -----------------------------------------------------

    @staticmethod
    def _serialize(value: Any) -> str:
        return json.dumps(value, default=str)

    @staticmethod
    def _deserialize(raw: str) -> Any:
        return json.loads(raw)

    # -- core API ----------------------------------------------------------

    async def get(self, key: str) -> Optional[Any]:
        """Look up *key* in L1 first, then L2."""
        # L1
        result = self._l1.get(key)
        if result is not None:
            logger.debug("L1 cache HIT: %s", key)
            return result

        # L2
        if self._redis_available and self._redis is not None:
            try:
                raw = await self._redis.get(self._full_key(key))
                if raw is not None:
                    value = self._deserialize(raw)
                    # Promote to L1
                    self._l1.set(key, value)
                    logger.debug("L2 cache HIT (promoted to L1): %s", key)
                    return value
            except Exception:
                logger.warning("Redis GET failed for key %s", key, exc_info=True)

        logger.debug("Cache MISS: %s", key)
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store *value* in both L1 and L2."""
        effective_ttl = ttl if ttl is not None else self._l2_ttl

        # L1
        self._l1.set(key, value, ttl=min(effective_ttl, DEFAULT_L1_TTL_SECONDS))

        # L2
        if self._redis_available and self._redis is not None:
            try:
                serialized = self._serialize(value)
                await self._redis.setex(
                    self._full_key(key),
                    effective_ttl,
                    serialized,
                )
            except Exception:
                logger.warning("Redis SET failed for key %s", key, exc_info=True)

    async def delete(self, key: str) -> None:
        """Remove *key* from both tiers."""
        self._l1.delete(key)
        if self._redis_available and self._redis is not None:
            try:
                await self._redis.delete(self._full_key(key))
            except Exception:
                logger.warning("Redis DELETE failed for key %s", key, exc_info=True)

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: Optional[int] = None,
    ) -> Any:
        """
        Return cached value for *key*, or call *factory* to compute it,
        cache the result, and return it.  *factory* may be sync or async.
        """
        cached = await self.get(key)
        if cached is not None:
            return cached

        # Compute value
        result = factory()
        if asyncio.iscoroutine(result) or asyncio.isfuture(result):
            result = await result

        await self.set(key, result, ttl=ttl)
        return result

    async def invalidate_pattern(self, pattern: str) -> int:
        """Remove all keys matching *pattern* from both tiers."""
        removed_l1 = self._l1.invalidate_pattern(pattern)
        removed_l2 = 0

        if self._redis_available and self._redis is not None:
            try:
                full_pattern = self._full_key(pattern)
                cursor: int = 0  # type: ignore[assignment]
                keys_to_delete: list[str] = []
                while True:
                    cursor, keys = await self._redis.scan(
                        cursor=cursor, match=full_pattern, count=200
                    )
                    keys_to_delete.extend(keys)
                    if cursor == 0:
                        break
                if keys_to_delete:
                    removed_l2 = await self._redis.delete(*keys_to_delete)
            except Exception:
                logger.warning(
                    "Redis pattern invalidation failed for %s", pattern, exc_info=True
                )

        total = removed_l1 + removed_l2
        logger.info(
            "Invalidated pattern '%s': L1=%d L2=%d total=%d",
            pattern,
            removed_l1,
            removed_l2,
            total,
        )
        return total

    # -- diagnostics -------------------------------------------------------

    async def health_check(self) -> dict[str, Any]:
        """Return cache health info."""
        redis_ok = False
        if self._redis_available and self._redis is not None:
            try:
                await self._redis.ping()
                redis_ok = True
            except Exception:
                redis_ok = False

        return {
            "l1_size": self._l1.size,
            "redis_available": redis_ok,
        }
