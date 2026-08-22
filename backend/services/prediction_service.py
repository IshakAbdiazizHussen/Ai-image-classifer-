"""Persists/reads PredictionRecord rows, and owns the Redis prediction
cache. Cache keys always include `model_version` (constraints.md rule 19
in architecture.md's caching strategy) so a newly promoted model version
can never be served a stale prediction from an older one."""

from __future__ import annotations

import json
from typing import Any

import redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.prediction import PredictionRecord

CACHE_TTL_SECONDS = 3600


def build_cache_key(model_version: str, image_hash: str) -> str:
    return f"predict:{model_version}:{image_hash}"


def get_cached_prediction(
    redis_client: redis.Redis, model_version: str, image_hash: str
) -> dict[str, Any] | None:
    raw = redis_client.get(build_cache_key(model_version, image_hash))
    return json.loads(raw) if raw else None


def cache_prediction(
    redis_client: redis.Redis,
    model_version: str,
    image_hash: str,
    payload: dict[str, Any],
) -> None:
    redis_client.set(
        build_cache_key(model_version, image_hash),
        json.dumps(payload),
        ex=CACHE_TTL_SECONDS,
    )


def save_prediction(
    db: Session,
    *,
    image_hash: str,
    predicted_label: str,
    confidence: float,
    probabilities: dict[str, float],
    model_version: str,
    inference_latency_ms: float,
) -> PredictionRecord:
    record = PredictionRecord(
        image_hash=image_hash,
        predicted_label=predicted_label,
        confidence=confidence,
        probabilities=probabilities,
        model_version=model_version,
        inference_latency_ms=inference_latency_ms,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_predictions(
    db: Session, *, page: int, page_size: int
) -> tuple[list[PredictionRecord], int]:
    total = db.scalar(select(func.count()).select_from(PredictionRecord)) or 0
    items = (
        db.execute(
            select(PredictionRecord)
            .order_by(PredictionRecord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return list(items), total
