"""Health probe response schemas.

Pydantic models for aggregate health, Kubernetes readiness, and liveness
endpoints. These are response-only shapes with no conversion to model DTOs.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Aggregate health status for ``GET /health``.

    Attributes:
        status: Overall service health label (default ``healthy``).
        version: Application version string from package metadata.
        timestamp: UTC time when the probe was evaluated.
        database: Database connectivity label (e.g. ``connected`` or ``unavailable``).
    """

    status: str = "healthy"
    version: str
    timestamp: datetime
    database: str


class ReadinessResponse(BaseModel):
    """Kubernetes readiness probe payload.

    Attributes:
        ready: ``True`` when the process can accept traffic (dependencies up).
    """

    ready: bool


class LivenessResponse(BaseModel):
    """Kubernetes liveness probe payload.

    Attributes:
        alive: ``True`` when the process is running (default ``True``).
    """

    alive: bool = True
