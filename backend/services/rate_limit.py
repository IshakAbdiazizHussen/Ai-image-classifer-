"""Redis-backed per-client rate limiter (constraints.md rule 21) — a
fixed one-minute window per client id (IP address).

Deliberately fails CLOSED, not open: rate limiting is the abuse-control
gate in front of the one genuinely expensive endpoint (model inference),
so if Redis itself is unreachable we reject cleanly (`RateLimiterUnavailable`
→ the router turns this into a 503) rather than silently letting every
request through unlimited. This is a different choice than the prediction
cache makes (services/prediction_service.py) — the cache is a pure
optimization and fails OPEN (skips caching) on the same kind of error,
since losing the cache doesn't compromise anything.
"""

from __future__ import annotations

import logging
import time

import redis

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    def __init__(self, message: str, retry_after_seconds: int) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class RateLimiterUnavailable(Exception):
    """Raised when the rate limiter's own backing store (Redis) can't be
    reached — a distinct failure from RateLimitExceeded so the caller can
    map it to a 503 rather than a 429."""


class RateLimiter:
    def __init__(self, redis_client: redis.Redis, limit_per_minute: int) -> None:
        self.redis = redis_client
        self.limit = limit_per_minute

    def check(self, client_id: str) -> None:
        window = int(time.time() // 60)
        key = f"ratelimit:{client_id}:{window}"

        try:
            count = self.redis.incr(key)
            if count == 1:
                self.redis.expire(key, 60)
        except redis.RedisError as exc:
            logger.warning("rate limiter backend unavailable", extra={"error": str(exc)})
            raise RateLimiterUnavailable("Rate limiter is temporarily unavailable.") from exc

        if count > self.limit:
            retry_after_seconds = 60 - (int(time.time()) % 60)
            raise RateLimitExceeded(
                f"Rate limit exceeded: {self.limit} requests/minute.",
                retry_after_seconds=retry_after_seconds,
            )
