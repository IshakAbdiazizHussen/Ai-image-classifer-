"""Regression test for CORS: the frontend calls this API directly from
the browser (client components fetch the backend URL), so a missing/
misconfigured CORS policy is a silent, browser-only failure that curl-
based testing can't catch. Caught for real via Playwright during Phase 4
manual verification — this test locks the fix in."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.main import app


def test_predict_allows_configured_frontend_origin() -> None:
    origin = settings.cors_origins_list[0]
    with TestClient(app) as client:
        response = client.options(
            "/predict",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
            },
        )
    assert response.headers.get("access-control-allow-origin") == origin
