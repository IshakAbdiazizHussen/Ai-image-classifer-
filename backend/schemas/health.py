"""Response schema for GET /healthz (constraints.md rule 28 — reports
liveness of each dependency, not just process uptime)."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str  # "ok" | "degraded"
    database: bool
    redis: bool
    model_loaded: bool
    model_version: str | None
