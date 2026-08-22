"""End-to-end tests for POST /predict (and a health-check sanity test),
run against the real app (real model, real Postgres/Redis via the
lifespan startup) with `get_db` swapped for a rolled-back test session."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.core.database import get_db
from backend.core.redis import get_redis_client
from backend.main import app


@pytest.fixture()
def client(db_session, test_redis):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = lambda: test_redis
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_predict_rejects_wrong_content_type(client: TestClient) -> None:
    response = client.post(
        "/predict", files={"file": ("test.txt", b"not an image", "text/plain")}
    )
    assert response.status_code == 400


def test_predict_rejects_oversized_upload(client: TestClient) -> None:
    oversized_payload = b"0" * (6 * 1024 * 1024)  # over the 5 MB default limit
    response = client.post(
        "/predict", files={"file": ("big.png", oversized_payload, "image/png")}
    )
    assert response.status_code == 413


def test_predict_rejects_corrupt_image_bytes(client: TestClient) -> None:
    # Correct content-type header, garbage body — must never reach the model.
    response = client.post(
        "/predict", files={"file": ("fake.png", b"garbage-bytes", "image/png")}
    )
    assert response.status_code == 400


def test_predict_success_returns_expected_shape(client: TestClient) -> None:
    sample_path = next(Path("ml/data/raw/cat").glob("*.png"))
    response = client.post(
        "/predict",
        files={"file": ("cat.png", sample_path.read_bytes(), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["predicted_label"] == "cat"
    assert "model_version" in body
    assert "probabilities" in body
    assert body["cached"] is False


def test_predict_second_identical_upload_is_a_cache_hit(client: TestClient) -> None:
    sample_path = next(Path("ml/data/raw/cat").glob("*.png"))
    image_bytes = sample_path.read_bytes()

    first = client.post("/predict", files={"file": ("cat.png", image_bytes, "image/png")})
    second = client.post("/predict", files={"file": ("cat.png", image_bytes, "image/png")})

    assert first.json()["cached"] is False
    assert second.json()["cached"] is True
    assert second.json()["predicted_label"] == first.json()["predicted_label"]


def test_healthz_reports_all_dependencies(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] is True
    assert body["redis"] is True
    assert body["model_loaded"] is True
