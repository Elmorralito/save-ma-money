"""Redis connection pool helpers for optional shared infrastructure (PPT-043).

Provides a **sync** ``redis`` client lifecycle for FastAPI lifespan and
dependencies. Sync calls from async routes are acceptable for now (Starlette
runs sync endpoints in a threadpool); migrate to ``redis.asyncio`` when more
routes are async-heavy. When ``REDIS_ENABLED`` is false, helpers are no-ops so
the API keeps in-memory fallbacks. Postgres remains the source of truth.

Key naming uses ``papita:{PAPITA_ENV}:…`` (see :mod:`redis_keys`).

Fail policy (by concern):
    * Cache / rate-limit — **fail open** (miss / allow) on Redis errors.
    * JWT denylist — **fail closed** when Redis is required (503), so revoked
      tokens cannot be resurrected during a Redis blip.
    * BFF session map — **fail closed** when Redis is required (PPT-059); no
      silent process-memory fallback (``BffSessionStoreUnavailableError`` → 503).

Key exports:
    init_redis: Create a pooled client when Redis is enabled.
    close_redis: Close the client and its connection pool.
    get_redis_from_app: Read ``app.state.redis`` safely.
    ping_redis: Lightweight readiness probe with latency.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from redis import Redis
from redis.connection import ConnectionPool
from redis.exceptions import RedisError

if TYPE_CHECKING:
    from fastapi import FastAPI

    from papita_txnsapi.config.settings import Settings

logger = logging.getLogger(__name__)

_MAX_LATENCY_MS = 60_000.0


class RedisProbeDetail(StrEnum):
    """Allowlisted Redis probe detail strings returned to HTTP clients."""

    HEALTHY = "api-redis link healthy"
    DISABLED = "redis disabled"
    CLIENT_UNAVAILABLE = "redis client unavailable"
    PROBE_FAILED = "probe failed"


@dataclass(frozen=True, slots=True)
class RedisProbeResult:
    """Outcome of a Redis connectivity probe.

    Attributes:
        connected: ``True`` when ``PING`` succeeded.
        latency_ms: Round-trip duration in milliseconds when connected.
        detail: Allowlisted status label (never raw exception text).
        required: Whether Redis is required for readiness (``REDIS_ENABLED``).
    """

    connected: bool
    latency_ms: float | None
    detail: RedisProbeDetail
    required: bool = False


def _safe_latency_ms(elapsed_seconds: float) -> float:
    """Convert elapsed seconds to a finite, non-negative millisecond latency."""
    latency_ms = round(elapsed_seconds * 1000.0, 3)
    if not math.isfinite(latency_ms) or latency_ms < 0.0:
        return 0.0
    return min(latency_ms, _MAX_LATENCY_MS)


def init_redis(settings: Settings) -> Redis | None:
    """Create a pooled Redis client when ``REDIS_ENABLED`` is true.

    Args:
        settings: Application settings with Redis URL and pool size.

    Returns:
        Connected ``Redis`` client, or ``None`` when Redis is disabled.

    Raises:
        ValueError: When Redis is enabled without a ``REDIS_URL``.
        RedisError: When the initial ``PING`` fails (caller may treat as startup failure).
    """
    if not settings.REDIS_ENABLED:
        logger.info("Redis disabled (REDIS_ENABLED=false)")
        return None

    if not settings.REDIS_URL:
        raise ValueError("REDIS_URL is required when REDIS_ENABLED=true")

    pool = ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
        decode_responses=True,
    )
    client = Redis(connection_pool=pool)
    client.ping()
    logger.info("Redis connection pool ready (max_connections=%s)", settings.REDIS_MAX_CONNECTIONS)
    return client


def close_redis(client: Redis | None) -> None:
    """Close a Redis client and its underlying connection pool.

    Args:
        client: Client previously returned by :func:`init_redis`, or ``None``.
    """
    if client is None:
        return
    try:
        client.close()
        pool = getattr(client, "connection_pool", None)
        if pool is not None:
            pool.disconnect()
    except Exception:
        logger.exception("Error while closing Redis client")
    else:
        logger.info("Redis connection pool closed")


def get_redis_from_app(app: FastAPI) -> Redis | None:
    """Return the Redis client stored on ``app.state``, if any.

    Args:
        app: FastAPI application instance.

    Returns:
        ``Redis`` client or ``None`` when unset/disabled.
    """
    return getattr(app.state, "redis", None)


def ping_redis(client: Redis | None, *, required: bool = False) -> RedisProbeResult:
    """Probe Redis connectivity and measure round-trip latency.

    Args:
        client: Optional Redis client from application state.
        required: Whether Redis is required for readiness (``REDIS_ENABLED``).

    Returns:
        :class:`RedisProbeResult` with allowlisted detail only.
    """
    if not required and client is None:
        return RedisProbeResult(
            connected=True,
            latency_ms=None,
            detail=RedisProbeDetail.DISABLED,
            required=False,
        )

    if client is None:
        return RedisProbeResult(
            connected=False,
            latency_ms=None,
            detail=RedisProbeDetail.CLIENT_UNAVAILABLE,
            required=required,
        )

    try:
        started = time.perf_counter()
        client.ping()
        return RedisProbeResult(
            connected=True,
            latency_ms=_safe_latency_ms(time.perf_counter() - started),
            detail=RedisProbeDetail.HEALTHY,
            required=required,
        )
    except RedisError:
        logger.exception("Redis readiness check failed")
        return RedisProbeResult(
            connected=False,
            latency_ms=None,
            detail=RedisProbeDetail.PROBE_FAILED,
            required=required,
        )
