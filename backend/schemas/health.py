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
    # None = no evaluation_report.json found for this version (can't say);
    # True/False = what that report's own meets_threshold said
    # (constraints.md rule 8). Surfaced honestly rather than silently
    # served — does NOT flip `status` to degraded on its own, since
    # serving a known sub-threshold model is a deliberate operator choice
    # (e.g. a demo dataset), not an outage.
    model_promotable: bool | None
