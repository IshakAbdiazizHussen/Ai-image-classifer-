"""POST /predict — request parsing/response shaping only (constraints.md
rule 11). Upload validation, rate limiting, caching, inference, and
persistence are all delegated to services/."""

from __future__ import annotations

import hashlib
import logging

import redis as redis_lib
from fastapi import APIRouter, Depends, Request, UploadFile, status
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.errors import APIError
from backend.core.redis import get_redis_client
from backend.schemas.predict import PredictResponse
from backend.services import prediction_service
from backend.services.inference_service import InferenceService
from backend.services.rate_limit import RateLimitExceeded, RateLimiter, RateLimiterUnavailable

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def get_inference_service(request: Request) -> InferenceService:
    return request.app.state.inference_service


def get_rate_limiter(request: Request) -> RateLimiter:
    return request.app.state.rate_limiter


@router.post("/predict", response_model=PredictResponse)
async def predict(
    request: Request,
    file: UploadFile,
    db: Session = Depends(get_db),
    inference_service: InferenceService = Depends(get_inference_service),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    redis_client: redis_lib.Redis = Depends(get_redis_client),
) -> PredictResponse:
    client_id = request.client.host if request.client else "unknown"
    try:
        rate_limiter.check(client_id)
    except RateLimitExceeded as exc:
        raise APIError(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "rate_limited",
            str(exc),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except RateLimiterUnavailable as exc:
        # Fails CLOSED (constraints.md rule 21) — a clean 503, not a
        # crash/hang, and not silently letting the request through.
        raise APIError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "rate_limiter_unavailable",
            "Rate limiter is temporarily unavailable. Try again shortly.",
        ) from exc

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise APIError(
            status.HTTP_400_BAD_REQUEST,
            "unsupported_file_type",
            f"Unsupported file type '{file.content_type}'. "
            f"Allowed: {sorted(ALLOWED_CONTENT_TYPES)}.",
        )

    image_bytes = await file.read()
    if len(image_bytes) > settings.max_upload_bytes:
        raise APIError(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "payload_too_large",
            f"File exceeds the {settings.max_upload_bytes}-byte limit.",
        )

    image_hash = hashlib.sha256(image_bytes).hexdigest()
    model_version = inference_service.model_version

    # Fails OPEN (a cache-read error is treated as a miss) — see
    # services/prediction_service.py's module docstring for why this and
    # the rate limiter make opposite choices.
    cached = prediction_service.get_cached_prediction(
        redis_client, model_version, image_hash
    )
    if cached is not None:
        logger.info(
            "prediction cache hit",
            extra={"image_hash": image_hash, "model_version": model_version},
        )
        return PredictResponse(**cached, cached=True)

    try:
        result = inference_service.predict(image_bytes)
    except ValueError as exc:
        raise APIError(
            status.HTTP_400_BAD_REQUEST, "invalid_image", str(exc)
        ) from exc

    prediction_service.save_prediction(
        db,
        image_hash=image_hash,
        predicted_label=result.predicted_label,
        confidence=result.confidence,
        probabilities=result.probabilities,
        model_version=model_version,
        inference_latency_ms=result.inference_latency_ms,
    )

    payload = {
        "predicted_label": result.predicted_label,
        "confidence": result.confidence,
        "probabilities": result.probabilities,
        "model_version": model_version,
        "inference_latency_ms": result.inference_latency_ms,
    }
    prediction_service.cache_prediction(redis_client, model_version, image_hash, payload)

    logger.info(
        "prediction served",
        extra={
            "image_hash": image_hash,
            "model_version": model_version,
            "predicted_label": result.predicted_label,
        },
    )

    return PredictResponse(**payload, cached=False)
