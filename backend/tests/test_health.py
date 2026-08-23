"""Tests for GET /healthz — specifically that it reports UNHEALTHY via
the HTTP status code (not just the JSON body) when a dependency is down
(constraints.md rule 28; Phase 6 fixed a real bug here — see
routers/health.py's module docstring)."""

from __future__ import annotations

import redis
from fastapi.testclient import TestClient

from backend.core.database import get_db
from backend.core.redis import get_redis_client
from backend.main import app


class _BrokenSession:
    def execute(self, *args, **kwargs):
        raise Exception("simulated DB outage")


class _BrokenRedis:
    def ping(self, *args, **kwargs):
        raise redis.ConnectionError("simulated Redis outage")


def test_healthz_is_200_when_everything_is_up(db_session, test_redis) -> None:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = lambda: test_redis
    try:
        with TestClient(app) as client:
            response = client.get("/healthz")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] is True
    assert body["redis"] is True
    assert body["model_loaded"] is True


def test_healthz_is_503_when_database_is_down(test_redis) -> None:
    def override_get_db():
        yield _BrokenSession()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = lambda: test_redis
    try:
        with TestClient(app) as client:
            response = client.get("/healthz")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] is False
    assert body["redis"] is True


def test_healthz_is_503_when_redis_is_down(db_session) -> None:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = lambda: _BrokenRedis()
    try:
        with TestClient(app) as client:
            response = client.get("/healthz")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] is True
    assert body["redis"] is False
