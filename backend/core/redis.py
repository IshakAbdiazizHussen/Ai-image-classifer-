"""Redis client setup — shared by the prediction cache and the rate
limiter."""

from __future__ import annotations

import redis

from backend.core.config import settings

redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def get_redis_client() -> redis.Redis:
    """FastAPI dependency wrapping the module-level client, so tests can
    swap it out (`app.dependency_overrides`) the same way `get_db` is
    swapped for an isolated session — instead of routers importing the
    singleton directly and being untestable in isolation."""
    return redis_client
