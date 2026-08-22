"""Request/response schemas for GET /history — paginated
(constraints.md rule 16)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PredictionHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_hash: str
    predicted_label: str
    confidence: float
    model_version: str
    created_at: datetime


class PaginatedHistoryResponse(BaseModel):
    items: list[PredictionHistoryItem]
    total: int
    page: int
    page_size: int
