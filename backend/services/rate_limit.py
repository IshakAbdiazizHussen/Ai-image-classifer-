"""Redis-backed per-client rate limiter (constraints.md rule 21) — a
fixed one-minute window per client id (IP address). Cheap, easy to reason
about, and fails safe: if Redis itself is unavailable, `check` raises so
the caller can decide how to degrade rather than silently allowing
unlimited requests."""

from __future__ import annotations

import time

import redis


class RateLimitExceeded(Exception):
    pass


class RateLimiter:
    def __init__(self, redis_client: redis.Redis, limit_per_minute: int) -> None:
        self.redis = redis_client
        self.limit = limit_per_minute

    def check(self, client_id: str) -> None:
        window = int(time.time() // 60)
        key = f"ratelimit:{client_id}:{window}"

        count = self.redis.incr(key)
        if count == 1:
            self.redis.expire(key, 60)

        if count > self.limit:
            raise RateLimitExceeded(
                f"Rate limit exceeded: {self.limit} requests/minute."
            )
