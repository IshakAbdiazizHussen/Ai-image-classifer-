"""FastAPI app entrypoint: wires routers, loads the inference model once
at startup (constraints.md rule 17), and attaches a request-ID to every
request for structured logging (rule 27).

Run with: uvicorn backend.main:app --reload
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.errors import register_exception_handlers
from backend.core.logging import request_id_var, setup_logging
from backend.core.redis import redis_client
from backend.routers import health, history, predict
from backend.services.inference_service import InferenceService
from backend.services.rate_limit import RateLimiter

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    logger.info("starting up", extra={"model_version": settings.model_version})

    app.state.inference_service = InferenceService(
        artifacts_dir=settings.artifacts_dir, model_version=settings.model_version
    )
    app.state.rate_limiter = RateLimiter(
        redis_client, limit_per_minute=settings.rate_limit_per_minute
    )
    yield


app = FastAPI(title="Image Classifier API", lifespan=lifespan)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict.router)
app.include_router(history.router)
app.include_router(health.router)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    token = request_id_var.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)
    response.headers["X-Request-ID"] = request_id
    return response
