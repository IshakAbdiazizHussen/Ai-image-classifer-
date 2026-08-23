"""Unit tests for services/rate_limit.py."""

from __future__ import annotations

import redis
import pytest

from backend.services.rate_limit import RateLimitExceeded, RateLimiter, RateLimiterUnavailable


class _BrokenRedis:
    """Stands in for a Redis client whose connection is down — every call
    raises, like the real client would against an unreachable server."""

    def incr(self, *args, **kwargs):
        raise redis.ConnectionError("simulated Redis outage")

    def expire(self, *args, **kwargs):
        raise redis.ConnectionError("simulated Redis outage")


def test_allows_requests_up_to_the_limit(test_redis) -> None:
    limiter = RateLimiter(test_redis, limit_per_minute=3)
    for _ in range(3):
        limiter.check("client-a")  # should not raise


def test_rejects_requests_over_the_limit(test_redis) -> None:
    limiter = RateLimiter(test_redis, limit_per_minute=3)
    for _ in range(3):
        limiter.check("client-a")

    with pytest.raises(RateLimitExceeded):
        limiter.check("client-a")


def test_exceeded_error_carries_a_positive_retry_after(test_redis) -> None:
    limiter = RateLimiter(test_redis, limit_per_minute=1)
    limiter.check("client-a")

    with pytest.raises(RateLimitExceeded) as exc_info:
        limiter.check("client-a")
    assert 1 <= exc_info.value.retry_after_seconds <= 60


def test_tracks_clients_independently(test_redis) -> None:
    limiter = RateLimiter(test_redis, limit_per_minute=1)
    limiter.check("client-a")
    limiter.check("client-b")  # different client — should not raise


def test_fails_closed_when_redis_is_unreachable() -> None:
    # Rate limiting is the abuse-control gate — an unreachable backing
    # store must reject cleanly, never silently allow every request
    # through (constraints.md rule 21).
    limiter = RateLimiter(_BrokenRedis(), limit_per_minute=30)
    with pytest.raises(RateLimiterUnavailable):
        limiter.check("client-a")
