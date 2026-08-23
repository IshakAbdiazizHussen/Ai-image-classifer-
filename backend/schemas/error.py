"""The standardized error response shape every endpoint returns
(Phase 6 hardening) — see core/errors.py for the handlers that produce
this."""

from __future__ import annotations

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
