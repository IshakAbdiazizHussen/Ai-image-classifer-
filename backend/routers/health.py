"""GET /healthz — reports DB, Redis, and model-loaded status individually
(constraints.md rule 28), not just process uptime."""

from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import Depends

from backend.core.database import get_db
from backend.core.redis import redis_client
from backend.schemas.health import HealthResponse

router = APIRouter()


@router.get("/healthz", response_model=HealthResponse)
def healthz(request: Request, db: Session = Depends(get_db)) -> HealthResponse:
    db_ok = _check_database(db)
    redis_ok = _check_redis()
    inference_service = getattr(request.app.state, "inference_service", None)
    model_loaded = inference_service is not None

    return HealthResponse(
        status="ok" if (db_ok and redis_ok and model_loaded) else "degraded",
        database=db_ok,
        redis=redis_ok,
        model_loaded=model_loaded,
        model_version=inference_service.model_version if inference_service else None,
    )


def _check_database(db: Session) -> bool:
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _check_redis() -> bool:
    try:
        return bool(redis_client.ping())
    except Exception:
        return False
