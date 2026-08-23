"""GET /healthz — reports DB, Redis, and model-loaded status individually
(constraints.md rule 28), not just process uptime.

Phase 6 fix: this used to always return HTTP 200 even when `status` in
the body said "degraded" — which meant nothing actually watching the
HTTP status code (including our own docker-compose healthcheck) could
ever detect a real dependency outage. It now returns 503 whenever
anything is unhealthy, body included, so both the JSON payload and the
status code agree.
"""

from __future__ import annotations

import logging

import redis as redis_lib
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.redis import get_redis_client
from backend.schemas.health import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/healthz", response_model=HealthResponse)
def healthz(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    redis_client: redis_lib.Redis = Depends(get_redis_client),
) -> HealthResponse:
    db_ok = _check_database(db)
    redis_ok = _check_redis(redis_client)
    inference_service = getattr(request.app.state, "inference_service", None)
    model_loaded = inference_service is not None

    healthy = db_ok and redis_ok and model_loaded
    if not healthy:
        response.status_code = 503

    return HealthResponse(
        status="ok" if healthy else "degraded",
        database=db_ok,
        redis=redis_ok,
        model_loaded=model_loaded,
        model_version=inference_service.model_version if inference_service else None,
        model_promotable=inference_service.meets_threshold if inference_service else None,
    )


def _check_database(db: Session) -> bool:
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("healthz: database check failed", extra={"error": str(exc)})
        return False


def _check_redis(redis_client: redis_lib.Redis) -> bool:
    try:
        return bool(redis_client.ping())
    except Exception as exc:
        logger.warning("healthz: redis check failed", extra={"error": str(exc)})
        return False
