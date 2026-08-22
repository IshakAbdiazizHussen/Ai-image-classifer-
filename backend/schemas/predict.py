"""Request/response schemas for POST /predict — kept separate from the
ORM model (constraints.md rule 3)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PredictResponse(BaseModel):
    predicted_label: str
    confidence: float = Field(ge=0.0, le=1.0)
    probabilities: dict[str, float]
    model_version: str  # rule 15 — every response is traceable to its model
    inference_latency_ms: float
    cached: bool
