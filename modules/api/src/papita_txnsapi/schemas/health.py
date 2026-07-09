"""Health probe response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Aggregate health status for ``GET /health``."""

    status: str = "healthy"
    version: str
    timestamp: datetime
    database: str


class ReadinessResponse(BaseModel):
    """Kubernetes readiness probe payload."""

    ready: bool


class LivenessResponse(BaseModel):
    """Kubernetes liveness probe payload."""

    alive: bool = True
