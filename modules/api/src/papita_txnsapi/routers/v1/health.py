"""Health check endpoints (P1).

Operational probes under ``/health`` for load balancers and orchestrators. These routes
are unauthenticated and do not apply tenant scoping; they report process and database
readiness only.

Routes:
    ``GET /health`` — composite status with app version and database connectivity.
    ``GET /health/database`` — API↔database communication probe with latency.
    ``GET /health/ready`` — readiness probe; 503 when the database is unreachable.
    ``GET /health/live`` — liveness probe; always 200 when the process is running.

Service delegation:
    Database checks delegate to :func:`~papita_txnsapi.core.db_health.probe_database`
    with a request-scoped :class:`~papita_txnsmodel.database.connector.SQLDatabaseConnector`
    from ``get_connector``. Application metadata comes from ``get_settings``.

Security:
    Handlers accept no query/body input that reaches SQL. Probe failures return
    allowlisted ``detail`` values only; exception text stays in server logs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal, Type

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.db_health import probe_database
from papita_txnsapi.dependencies.services import get_connector
from papita_txnsapi.schemas.health import (
    DatabaseHealthResponse,
    HealthResponse,
    LivenessResponse,
    ReadinessResponse,
)
from papita_txnsmodel.database.connector import SQLDatabaseConnector

router = APIRouter(prefix="/health", tags=["Health"])

_JSON_CONTENT_TYPE = "application/json; charset=utf-8"


def _json_response(
    status_code: int,
    payload: HealthResponse | DatabaseHealthResponse | ReadinessResponse,
) -> JSONResponse:
    """Serialize a health schema as JSON without HTML content type.

    Args:
        status_code: HTTP status for the response.
        payload: Pydantic response model to dump in JSON mode.

    Returns:
        JSONResponse with an explicit ``application/json`` content type.
    """
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        media_type=_JSON_CONTENT_TYPE,
    )


@router.get("", response_model=HealthResponse, response_class=JSONResponse)
def get_health(
    settings: Annotated[Settings, Depends(get_settings)],
    connector: Annotated[Type[SQLDatabaseConnector], Depends(get_connector)],
) -> HealthResponse:
    """Return application status, version, and database connectivity.

    Args:
        settings: Application settings supplying version metadata.
        connector: Database connector class used for a lightweight readiness query.

    Returns:
        Composite health payload marked ``degraded`` when the database is disconnected.
    """
    probe = probe_database(connector)
    database: Literal["connected", "disconnected"] = "connected" if probe.connected else "disconnected"
    status_label: Literal["healthy", "degraded"] = "healthy" if probe.connected else "degraded"
    return HealthResponse(
        status=status_label,
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc),
        database=database,
        database_latency_ms=probe.latency_ms,
    )


@router.get("/database", response_model=DatabaseHealthResponse, response_class=JSONResponse)
def get_database_health(
    connector: Annotated[Type[SQLDatabaseConnector], Depends(get_connector)],
) -> DatabaseHealthResponse | JSONResponse:
    """Probe API↔database communication health.

    Runs a constant parameterized probe against PostgreSQL and reports whether the
    link is up plus round-trip latency. Accepts no client-supplied SQL or detail text.

    Args:
        connector: Database connector class used for the probe query.

    Returns:
        DatabaseHealthResponse with ``status=healthy`` when connected; otherwise a
        503 JSONResponse with ``status=unhealthy`` and an allowlisted detail code.
    """
    probe = probe_database(connector)
    status_label: Literal["healthy", "unhealthy"] = "healthy" if probe.connected else "unhealthy"
    payload = DatabaseHealthResponse(
        status=status_label,
        connected=probe.connected,
        latency_ms=probe.latency_ms,
        checked_at=datetime.now(timezone.utc),
        detail=probe.detail,
    )
    if probe.connected:
        return payload
    return _json_response(status.HTTP_503_SERVICE_UNAVAILABLE, payload)


@router.get("/ready", response_model=ReadinessResponse, response_class=JSONResponse)
def get_readiness(
    connector: Annotated[Type[SQLDatabaseConnector], Depends(get_connector)],
) -> ReadinessResponse | JSONResponse:
    """Readiness probe — returns 503 when the database is unreachable.

    Args:
        connector: Database connector class used for a lightweight readiness query.

    Returns:
        ReadinessResponse with ``ready=True`` when the database accepts connections;
        otherwise a 503 JSONResponse with ``ready=False``.
    """
    if probe_database(connector).connected:
        return ReadinessResponse(ready=True)
    return _json_response(status.HTTP_503_SERVICE_UNAVAILABLE, ReadinessResponse(ready=False))


@router.get("/live", response_model=LivenessResponse, response_class=JSONResponse)
def get_liveness() -> LivenessResponse:
    """Liveness probe — process is running.

    Returns:
        LivenessResponse with ``alive=True`` indicating the API process is responsive.
    """
    return LivenessResponse(alive=True)
