"""Circuit breaker wrappers for external service calls."""
from __future__ import annotations

import functools
import logging
from typing import Any, Callable

import pybreaker

logger = logging.getLogger(__name__)


class _LogListener(pybreaker.CircuitBreakerListener):
    """Log circuit breaker state transitions."""

    def state_change(self, cb: pybreaker.CircuitBreaker, old_state, new_state) -> None:
        logger.warning(
            "Circuit breaker '%s' state changed: %s -> %s",
            cb.name, old_state.name, new_state.name,
        )

    def failure(self, cb: pybreaker.CircuitBreaker, exc: Exception) -> None:
        logger.warning("Circuit breaker '%s' recorded failure: %s", cb.name, exc)


_listener = _LogListener()


# ---- Named Circuit Breakers ----

groq_breaker = pybreaker.CircuitBreaker(
    name="groq_api",
    fail_max=5,
    reset_timeout=60,
    listeners=[_listener],
)

huggingface_breaker = pybreaker.CircuitBreaker(
    name="huggingface_api",
    fail_max=5,
    reset_timeout=60,
    listeners=[_listener],
)

qdrant_breaker = pybreaker.CircuitBreaker(
    name="qdrant",
    fail_max=5,
    reset_timeout=30,
    listeners=[_listener],
)

ollama_breaker = pybreaker.CircuitBreaker(
    name="ollama",
    fail_max=3,
    reset_timeout=30,
    listeners=[_listener],
)

supabase_breaker = pybreaker.CircuitBreaker(
    name="supabase_storage",
    fail_max=5,
    reset_timeout=60,
    listeners=[_listener],
)


def with_circuit_breaker(breaker: pybreaker.CircuitBreaker):
    """Decorator that wraps an async function with a circuit breaker.

    Usage:
        @with_circuit_breaker(groq_breaker)
        async def call_groq(prompt: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await breaker.call_async(func, *args, **kwargs)
            except pybreaker.CircuitBreakerError:
                logger.error(
                    "Circuit breaker '%s' is OPEN — call to %s rejected",
                    breaker.name, func.__name__,
                )
                raise
        return wrapper
    return decorator
