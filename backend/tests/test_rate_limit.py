"""Unit tests for services/rate_limit.py."""

from __future__ import annotations

import pytest

from backend.services.rate_limit import RateLimitExceeded, RateLimiter


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


def test_tracks_clients_independently(test_redis) -> None:
    limiter = RateLimiter(test_redis, limit_per_minute=1)
    limiter.check("client-a")
    limiter.check("client-b")  # different client — should not raise
