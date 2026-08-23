"""Unit tests for the prediction cache in services/prediction_service.py —
covers cache hit/miss behavior and that `model_version` is always part of
the cache key (architecture.md's caching strategy)."""

from __future__ import annotations

import redis

from backend.services import prediction_service


class _BrokenRedis:
    """Stands in for a Redis client whose connection is down."""

    def get(self, *args, **kwargs):
        raise redis.ConnectionError("simulated Redis outage")

    def set(self, *args, **kwargs):
        raise redis.ConnectionError("simulated Redis outage")


def test_cache_key_includes_model_version() -> None:
    key_v1 = prediction_service.build_cache_key("v1", "hash123")
    key_v2 = prediction_service.build_cache_key("v2", "hash123")
    assert key_v1 != key_v2
    assert "v1" in key_v1 and "hash123" in key_v1


def test_miss_on_unknown_key_returns_none(test_redis) -> None:
    assert prediction_service.get_cached_prediction(test_redis, "v1", "unknown") is None


def test_set_then_get_is_a_hit(test_redis) -> None:
    payload = {"predicted_label": "cat", "confidence": 0.9}
    prediction_service.cache_prediction(test_redis, "v1", "hash123", payload)
    assert prediction_service.get_cached_prediction(test_redis, "v1", "hash123") == payload


def test_different_model_version_is_a_miss(test_redis) -> None:
    payload = {"predicted_label": "cat", "confidence": 0.9}
    prediction_service.cache_prediction(test_redis, "v1", "hash123", payload)
    # Same image hash, different model_version -> different key -> miss.
    assert prediction_service.get_cached_prediction(test_redis, "v2", "hash123") is None


def test_fails_open_on_read_when_redis_is_unreachable() -> None:
    # The cache is a pure optimization — an outage must degrade to a
    # cache miss, never take /predict down with it.
    result = prediction_service.get_cached_prediction(_BrokenRedis(), "v1", "hash123")
    assert result is None


def test_fails_open_on_write_when_redis_is_unreachable() -> None:
    # Must not raise — a failed cache write is a no-op, not a request failure.
    prediction_service.cache_prediction(_BrokenRedis(), "v1", "hash123", {"a": 1})
