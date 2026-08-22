"""Unit tests for the prediction cache in services/prediction_service.py —
covers cache hit/miss behavior and that `model_version` is always part of
the cache key (architecture.md's caching strategy)."""

from __future__ import annotations

from backend.services import prediction_service


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
