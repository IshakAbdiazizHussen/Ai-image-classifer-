"""Every endpoint's error response follows the same
`{"error": {"code", "message"}}` shape (Phase 6 hardening) — whether it's
an explicit APIError, a rate-limit rejection, a validation error, or a
404 on an unknown route."""

from __future__ import annotations

from pathlib import Path

import pytest
import redis
from fastapi.testclient import TestClient

from backend.core.database import get_db
from backend.core.redis import get_redis_client
from backend.main import app
from backend.routers.predict import get_rate_limiter
from backend.services.rate_limit import RateLimiter


class _BrokenRedis:
    def incr(self, *args, **kwargs):
        raise redis.ConnectionError("simulated Redis outage")

    def expire(self, *args, **kwargs):
        raise redis.ConnectionError("simulated Redis outage")


def _assert_standard_error_shape(body: dict, expected_code: str) -> None:
    assert "error" in body
    assert body["error"]["code"] == expected_code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]


@pytest.fixture()
def client(db_session, test_redis):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = lambda: test_redis
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_unsupported_file_type_error_shape(client: TestClient) -> None:
    response = client.post("/predict", files={"file": ("t.txt", b"x", "text/plain")})
    assert response.status_code == 400
    _assert_standard_error_shape(response.json(), "unsupported_file_type")


def test_oversized_upload_error_shape(client: TestClient) -> None:
    payload = b"0" * (6 * 1024 * 1024)
    response = client.post("/predict", files={"file": ("big.png", payload, "image/png")})
    assert response.status_code == 413
    _assert_standard_error_shape(response.json(), "payload_too_large")


def test_corrupt_image_error_shape(client: TestClient) -> None:
    response = client.post("/predict", files={"file": ("f.png", b"garbage", "image/png")})
    assert response.status_code == 400
    _assert_standard_error_shape(response.json(), "invalid_image")


def test_missing_file_field_error_shape(client: TestClient) -> None:
    # No "file" field at all — FastAPI's own request validation rejects
    # this before the route body ever runs (confirmed live against the
    # running container during the audit).
    response = client.post("/predict", data={"notfile": "hello"})
    assert response.status_code == 422
    _assert_standard_error_shape(response.json(), "validation_error")


def test_empty_file_field_error_shape(client: TestClient) -> None:
    # "file" present but as a plain empty form value, not an uploaded
    # file — a type mismatch against the `file: UploadFile` parameter.
    response = client.post("/predict", data={"file": ""})
    assert response.status_code == 422
    _assert_standard_error_shape(response.json(), "validation_error")


def test_malformed_multipart_body_error_shape(client: TestClient) -> None:
    # Content-Type claims multipart/form-data, but the body isn't valid
    # multipart at all — Starlette's own parser rejects this at a lower
    # level than FastAPI's field validation, landing on the
    # StarletteHTTPException handler (the same one the Phase 6 404 bug
    # was in) rather than the RequestValidationError one above.
    response = client.post(
        "/predict",
        content=b"garbage not multipart",
        headers={"Content-Type": "multipart/form-data; boundary=xyz"},
    )
    assert response.status_code == 400
    _assert_standard_error_shape(response.json(), "bad_request")


def test_rate_limited_error_shape_and_retry_after_header(client: TestClient, test_redis) -> None:
    app.dependency_overrides[get_rate_limiter] = lambda: RateLimiter(test_redis, limit_per_minute=1)
    try:
        sample_dir = Path("ml/data/raw/cat")
        samples = list(sample_dir.glob("*.png"))

        first = client.post("/predict", files={"file": ("a.png", samples[0].read_bytes(), "image/png")})
        assert first.status_code == 200

        # A different image (distinct hash) so this isn't served from
        # cache — it must hit the rate limiter, not just the cache path.
        second = client.post("/predict", files={"file": ("b.png", samples[1].read_bytes(), "image/png")})
        assert second.status_code == 429
        _assert_standard_error_shape(second.json(), "rate_limited")
        assert "retry-after" in {k.lower() for k in second.headers.keys()}
    finally:
        app.dependency_overrides.pop(get_rate_limiter, None)


def test_rate_limiter_unavailable_error_shape(client: TestClient) -> None:
    app.dependency_overrides[get_rate_limiter] = lambda: RateLimiter(_BrokenRedis(), 30)
    try:
        sample_path = next(Path("ml/data/raw/cat").glob("*.png"))
        response = client.post(
            "/predict", files={"file": ("a.png", sample_path.read_bytes(), "image/png")}
        )
        assert response.status_code == 503
        _assert_standard_error_shape(response.json(), "rate_limiter_unavailable")
    finally:
        app.dependency_overrides.pop(get_rate_limiter, None)


def test_validation_error_shape_on_bad_query_param(client: TestClient) -> None:
    response = client.get("/history?page=0")  # page must be >= 1
    assert response.status_code == 422
    _assert_standard_error_shape(response.json(), "validation_error")


def test_not_found_error_shape_on_unknown_route(client: TestClient) -> None:
    response = client.get("/this-route-does-not-exist")
    assert response.status_code == 404
    _assert_standard_error_shape(response.json(), "not_found")
