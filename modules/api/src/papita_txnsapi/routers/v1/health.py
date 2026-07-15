"""Health check endpoints for load balancers and orchestrators (P1).

Unauthenticated probes under ``/health`` report process, database, and (when
``AUTH_PROVIDER=supabase``) Supabase Auth readiness. Routes do not apply tenant
scoping and never accept client input that reaches SQL or Auth URLs.

Routes:
    ``GET /health`` — composite status with app version, database, and Auth.
    ``GET /health/database`` — API↔database probe with latency (503 when down).
    ``GET /health/auth`` — API↔Supabase Auth probe with latency (503 when down).
    ``GET /health/ready`` — readiness; 503 when DB or required Auth is down.
    ``GET /health/live`` — liveness; always 200 while the process is running.

Service delegation:
    Database checks use :func:`~papita_txnsapi.core.db_health.probe_database`.
    Auth checks use :func:`~papita_txnsapi.core.auth_health.probe_supabase_auth`.

Security:
    Failures return allowlisted ``detail`` / connectivity labels only. Exception
    text and Auth response bodies stay in server logs and are never reflected.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal, Type

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.auth_health import AuthProbeDetail, AuthProbeResult, probe_supabase_auth
from papita_txnsapi.core.db_health import probe_database
from papita_txnsapi.dependencies.services import get_connector
from papita_txnsapi.schemas.health import (
    AuthHealthResponse,
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
    payload: HealthResponse | DatabaseHealthResponse | AuthHealthResponse | ReadinessResponse,
) -> JSONResponse:
    """Serialize a health schema as JSON without an HTML content type.

    Args:
        status_code: HTTP status for the response (typically 503 for failed probes).
        payload: Pydantic response model to dump in JSON mode.

    Returns:
        ``JSONResponse`` with an explicit ``application/json`` content type.
    """
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        media_type=_JSON_CONTENT_TYPE,
    )


def _probe_auth(settings: Settings) -> AuthProbeResult:
    """Run the configured Auth probe using application settings.

    Args:
        settings: App settings with ``AUTH_PROVIDER`` and optional Supabase keys.

    Returns:
        Allowlisted Auth connectivity result (local mode skips the network call).
    """
    return probe_supabase_auth(
        auth_provider=settings.AUTH_PROVIDER,
        supabase_url=settings.SUPABASE_URL,
        anon_key=settings.SUPABASE_ANON_KEY,
    )


def _auth_connectivity_label(probe: AuthProbeResult) -> Literal["connected", "disconnected", "skipped"]:
    """Map an Auth probe result to the composite ``GET /health`` auth label."""
    if probe.detail == AuthProbeDetail.SKIPPED_LOCAL:
        return "skipped"
    return "connected" if probe.reachable else "disconnected"


@router.get("", response_model=HealthResponse, response_class=JSONResponse)
def get_health(
    settings: Annotated[Settings, Depends(get_settings)],
    connector: Annotated[Type[SQLDatabaseConnector], Depends(get_connector)],
) -> HealthResponse:
    """Return application status, version, database, and Auth connectivity.

    Always returns HTTP 200 with ``status`` of ``healthy`` or ``degraded``. Use
    ``/health/ready`` when orchestrators should fail traffic on dependency loss.

    Args:
        settings: Application settings supplying version and Auth configuration.
        connector: Database connector class used for a lightweight readiness query.

    Returns:
        Composite ``HealthResponse`` marked ``degraded`` when the database is down
        or required Supabase Auth is unreachable (local Auth probe counts as ok).
    """
    db_probe = probe_database(connector)
    auth_probe = _probe_auth(settings)
    database: Literal["connected", "disconnected"] = "connected" if db_probe.connected else "disconnected"
    dependencies_ok = db_probe.connected and auth_probe.reachable
    status_label: Literal["healthy", "degraded"] = "healthy" if dependencies_ok else "degraded"
    return HealthResponse(
        status=status_label,
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc),
        database=database,
        database_latency_ms=db_probe.latency_ms,
        auth=_auth_connectivity_label(auth_probe),
        auth_latency_ms=auth_probe.latency_ms,
        auth_detail=auth_probe.detail,
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
        ``DatabaseHealthResponse`` with ``status=healthy`` when connected; otherwise
        a 503 ``JSONResponse`` with ``status=unhealthy`` and an allowlisted detail.
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


@router.get("/auth", response_model=AuthHealthResponse, response_class=JSONResponse)
def get_auth_health(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthHealthResponse | JSONResponse:
    """Probe API↔Supabase Auth (GoTrue) communication health.

    Calls ``GET {SUPABASE_URL}/auth/v1/health`` when ``AUTH_PROVIDER=supabase``.
    Local HS256 mode reports healthy with a skipped detail (no network call).

    Args:
        settings: Application settings with Auth provider and Supabase credentials.

    Returns:
        ``AuthHealthResponse`` with ``status=healthy`` when Auth is up (or skipped);
        otherwise a 503 ``JSONResponse`` with ``status=unhealthy``.
    """
    probe = _probe_auth(settings)
    status_label: Literal["healthy", "unhealthy"] = "healthy" if probe.reachable else "unhealthy"
    payload = AuthHealthResponse(
        status=status_label,
        provider=probe.provider,
        reachable=probe.reachable,
        latency_ms=probe.latency_ms,
        checked_at=datetime.now(timezone.utc),
        detail=probe.detail,
    )
    if probe.reachable:
        return payload
    return _json_response(status.HTTP_503_SERVICE_UNAVAILABLE, payload)


@router.get("/ready", response_model=ReadinessResponse, response_class=JSONResponse)
def get_readiness(
    settings: Annotated[Settings, Depends(get_settings)],
    connector: Annotated[Type[SQLDatabaseConnector], Depends(get_connector)],
) -> ReadinessResponse | JSONResponse:
    """Readiness probe — fail open traffic when the database or required Auth is down.

    Both database connectivity and Auth reachability (including local skip as ok)
    must succeed for ``ready=True``. Suitable for Kubernetes readiness gates.

    Args:
        settings: Application settings selecting Auth provider requirements.
        connector: Database connector class used for a lightweight readiness query.

    Returns:
        ``ReadinessResponse`` with ``ready=True`` when dependencies accept traffic;
        otherwise a 503 ``JSONResponse`` with ``ready=False``.
    """
    db_ok = probe_database(connector).connected
    auth_ok = _probe_auth(settings).reachable
    if db_ok and auth_ok:
        return ReadinessResponse(ready=True)
    return _json_response(status.HTTP_503_SERVICE_UNAVAILABLE, ReadinessResponse(ready=False))


@router.get("/live", response_model=LivenessResponse, response_class=JSONResponse)
def get_liveness() -> LivenessResponse:
    """Liveness probe — confirm the API process is running.

    Does not check database or Auth. Use ``/health/ready`` for dependency gates.

    Returns:
        ``LivenessResponse`` with ``alive=True`` when the process can serve HTTP.
    """
    return LivenessResponse(alive=True)
