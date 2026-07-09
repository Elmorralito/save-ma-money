"""Health check endpoints (P1)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Type

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.db_health import check_database_ready
from papita_txnsapi.dependencies.services import get_connector
from papita_txnsapi.schemas.health import HealthResponse, LivenessResponse, ReadinessResponse
from papita_txnsmodel.database.connector import SQLDatabaseConnector

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
def get_health(
    settings: Annotated[Settings, Depends(get_settings)],
    connector: Annotated[Type[SQLDatabaseConnector], Depends(get_connector)],
) -> HealthResponse:
    """Return application status, version, and database connectivity."""
    db_status = "connected" if check_database_ready(connector) else "disconnected"
    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc),
        database=db_status,
    )


@router.get("/ready", response_model=ReadinessResponse)
def get_readiness(
    connector: Annotated[Type[SQLDatabaseConnector], Depends(get_connector)],
) -> ReadinessResponse | JSONResponse:
    """Readiness probe — returns 503 when the database is unreachable."""
    if check_database_ready(connector):
        return ReadinessResponse(ready=True)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=ReadinessResponse(ready=False).model_dump(),
    )


@router.get("/live", response_model=LivenessResponse)
def get_liveness() -> LivenessResponse:
    """Liveness probe — process is running."""
    return LivenessResponse(alive=True)
