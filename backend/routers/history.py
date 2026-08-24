"""GET /history — paginated (constraints.md rule 16). Request parsing/
response shaping only; the query itself lives in
services/prediction_service.py."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.error import ErrorResponse
from backend.schemas.history import PaginatedHistoryResponse, PredictionHistoryItem
from backend.services import prediction_service

router = APIRouter()


@router.get(
    "/history",
    response_model=PaginatedHistoryResponse,
    responses={"default": {"model": ErrorResponse, "description": "Standardized error response"}},
)
def get_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PaginatedHistoryResponse:
    items, total = prediction_service.list_predictions(db, page=page, page_size=page_size)
    return PaginatedHistoryResponse(
        items=[PredictionHistoryItem.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
