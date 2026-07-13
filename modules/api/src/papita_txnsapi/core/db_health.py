"""Database readiness probes for health endpoints.

Provides lightweight connectivity checks against the model-layer SQLAlchemy engine.
Used by ``/health``, ``/health/ready``, and ``/health/database`` routes to report
whether the API can reach PostgreSQL and how fast the round-trip is.

Security notes:
    * The probe uses SQLAlchemy ``select(literal(1))`` only — no request input and no
      interpolated SQL text (defense against SQL injection).
    * HTTP clients receive allowlisted ``detail`` codes only — exception messages are
      logged server-side and never reflected (defense against XSS / info disclosure).

Key exports:
    DatabaseProbeDetail: Allowlisted human-readable probe statuses.
    DatabaseProbeResult: Structured outcome of a connectivity probe.
    probe_database: Execute a constant probe and return connectivity plus latency.
    check_database_ready: Boolean wrapper over :func:`probe_database`.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Type

from sqlalchemy import literal, select
from sqlmodel import Session

from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.enums import FallbackAction

logger = logging.getLogger(__name__)

# Bound probe latency for JSON safety (reject NaN/inf before serialization).
_MAX_LATENCY_MS = 60_000.0


class DatabaseProbeDetail(StrEnum):
    """Allowlisted probe detail strings returned to HTTP clients.

    Values are fixed constants so responses never echo exception text, connection
    URLs, or other attacker-/environment-influenced content.
    """

    HEALTHY = "api-database link healthy"
    CONNECTOR_NOT_INITIALIZED = "connector not initialized"
    ENGINE_UNAVAILABLE = "database engine unavailable"
    PROBE_FAILED = "probe failed"


@dataclass(frozen=True, slots=True)
class DatabaseProbeResult:
    """Outcome of a database connectivity probe.

    Attributes:
        connected: ``True`` when the constant probe query succeeded.
        latency_ms: Round-trip duration in milliseconds when connected; ``None`` otherwise.
        detail: Allowlisted status of the API↔database link (never raw error text).
    """

    connected: bool
    latency_ms: float | None
    detail: DatabaseProbeDetail


def _safe_latency_ms(elapsed_seconds: float) -> float:
    """Convert elapsed seconds to a finite, non-negative millisecond latency.

    Args:
        elapsed_seconds: Wall-clock duration from ``time.perf_counter``.

    Returns:
        Latency in milliseconds clamped to ``[0, _MAX_LATENCY_MS]``.
    """
    latency_ms = round(elapsed_seconds * 1000.0, 3)
    if not math.isfinite(latency_ms) or latency_ms < 0.0:
        return 0.0
    return min(latency_ms, _MAX_LATENCY_MS)


def probe_database(connector: Type[SQLDatabaseConnector]) -> DatabaseProbeResult:
    """Probe database connectivity and measure round-trip latency.

    Verifies that the connector is initialized, an engine exists, and a session can
    execute a constant, parameterized probe without raising. On success, records
    wall-clock latency for operators judging API↔database communication health.

    Args:
        connector: Model ``SQLDatabaseConnector`` class bound to a configured engine.

    Returns:
        :class:`DatabaseProbeResult` with connectivity, optional latency, and an
        allowlisted detail code. Exception payloads are never included in the result.
    """
    if not connector.connected(on_disconnected=FallbackAction.LOG, custom_logger=logger):
        return DatabaseProbeResult(
            connected=False,
            latency_ms=None,
            detail=DatabaseProbeDetail.CONNECTOR_NOT_INITIALIZED,
        )

    if connector.engine is None:
        return DatabaseProbeResult(
            connected=False,
            latency_ms=None,
            detail=DatabaseProbeDetail.ENGINE_UNAVAILABLE,
        )

    try:
        started = time.perf_counter()
        # Expression API only — never build SQL from strings or request data.
        with Session(connector.engine) as session:
            session.connection().execute(select(literal(1)))
        return DatabaseProbeResult(
            connected=True,
            latency_ms=_safe_latency_ms(time.perf_counter() - started),
            detail=DatabaseProbeDetail.HEALTHY,
        )
    except Exception:
        # Log full traceback server-side; clients get a fixed detail only.
        logger.exception("Database readiness check failed")
        return DatabaseProbeResult(
            connected=False,
            latency_ms=None,
            detail=DatabaseProbeDetail.PROBE_FAILED,
        )


def check_database_ready(connector: Type[SQLDatabaseConnector]) -> bool:
    """Probe database connectivity with a constant parameterized query.

    Args:
        connector: Model ``SQLDatabaseConnector`` class bound to a configured engine.

    Returns:
        ``True`` when the engine is connected and the probe succeeds; ``False`` on
        disconnect, missing engine, or any execution error (errors are logged).
    """
    return probe_database(connector).connected
