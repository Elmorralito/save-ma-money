"""Health probe response schemas.

Pydantic models for aggregate health, database communication, Kubernetes readiness,
and liveness endpoints. These are response-only shapes with no conversion to model DTOs.

Status and detail fields use ``Literal`` / enum constraints so clients only ever see
allowlisted labels — never reflected exception text or request-influenced strings.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from papita_txnsapi.core.db_health import DatabaseProbeDetail

__all__ = [
    "DatabaseProbeDetail",
    "DatabaseHealthResponse",
    "HealthResponse",
    "LivenessResponse",
    "ReadinessResponse",
]


class HealthResponse(BaseModel):
    """Aggregate health status for ``GET /health``.

    Attributes:
        status: Overall service health label (``healthy`` or ``degraded``).
        version: Application version string from package metadata.
        timestamp: UTC time when the probe was evaluated.
        database: Database connectivity label (``connected`` or ``disconnected``).
        database_latency_ms: Round-trip probe latency in milliseconds when connected.
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["healthy", "degraded"] = "healthy"
    version: str = Field(min_length=1, max_length=64)
    timestamp: datetime
    database: Literal["connected", "disconnected"]
    database_latency_ms: float | None = Field(default=None, ge=0.0, le=60_000.0)


class DatabaseHealthResponse(BaseModel):
    """API↔database communication health for ``GET /health/database``.

    Attributes:
        status: ``healthy`` when the probe succeeds; ``unhealthy`` otherwise.
        connected: Whether the API could execute the constant probe against PostgreSQL.
        latency_ms: Round-trip duration in milliseconds when connected.
        checked_at: UTC time when the probe ran.
        detail: Allowlisted explanation of the communication status (never raw errors).
    """

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    status: Literal["healthy", "unhealthy"]
    connected: bool
    latency_ms: float | None = Field(
        default=None,
        ge=0.0,
        le=60_000.0,
        description="Round-trip probe latency in ms (parameterized SELECT of literal 1)",
    )
    checked_at: datetime
    detail: DatabaseProbeDetail


class ReadinessResponse(BaseModel):
    """Kubernetes readiness probe payload.

    Attributes:
        ready: ``True`` when the process can accept traffic (dependencies up).
    """

    model_config = ConfigDict(extra="forbid")

    ready: bool


class LivenessResponse(BaseModel):
    """Kubernetes liveness probe payload.

    Attributes:
        alive: ``True`` when the process is running (default ``True``).
    """

    model_config = ConfigDict(extra="forbid")

    alive: bool = True
