"""Supabase Auth readiness probes for health endpoints.

Probes the GoTrue Auth service at ``{SUPABASE_URL}/auth/v1/health`` when
``AUTH_PROVIDER=supabase``. Used by ``GET /health``, ``GET /health/auth``, and
``GET /health/ready`` so operators can see whether register/login/refresh can
reach Supabase Auth.

When ``auth_provider`` is ``local``, the probe is skipped as healthy so HS256
test mode does not require a live Auth project.

Security notes:
    * Probe URL is built only from configured ``SUPABASE_URL`` (no request input).
    * HTTP clients receive allowlisted ``AuthProbeDetail`` values only — exception
      and Auth response bodies are logged server-side and never reflected.

Public API:
    ``AuthProbeDetail``, ``AuthProbeResult``, :func:`probe_supabase_auth`.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)

_MAX_LATENCY_MS = 60_000.0
_DEFAULT_TIMEOUT_SECONDS = 5.0


class AuthProbeDetail(StrEnum):
    """Allowlisted Auth probe detail strings returned to HTTP clients.

    Members are stable wire labels for OpenAPI / operators — never raw exception
    text. Values:

    * ``HEALTHY`` — GoTrue health returned a success status.
    * ``SKIPPED_LOCAL`` — ``AUTH_PROVIDER=local``; no network call.
    * ``NOT_CONFIGURED`` — Supabase URL or anon key missing.
    * ``UNREACHABLE`` — timeout or transport failure reaching Auth.
    * ``PROBE_FAILED`` — unexpected error or Auth HTTP 4xx on the probe.
    * ``UNHEALTHY_STATUS`` — Auth HTTP 5xx on the health endpoint.
    """

    HEALTHY = "supabase auth healthy"
    SKIPPED_LOCAL = "auth provider is local — supabase probe skipped"
    NOT_CONFIGURED = "supabase auth not configured"
    UNREACHABLE = "supabase auth unreachable"
    PROBE_FAILED = "supabase auth probe failed"
    UNHEALTHY_STATUS = "supabase auth reported unhealthy"


@dataclass(frozen=True, slots=True)
class AuthProbeResult:
    """Outcome of a Supabase Auth connectivity probe.

    Attributes:
        reachable: ``True`` when Auth answered successfully (or local skip).
        latency_ms: Round-trip duration in ms when a network probe succeeded
            enough to measure; ``None`` on skip / config / transport failure.
        detail: Allowlisted status code (never raw exception / response text).
        provider: Active auth provider label echoed for operators.
    """

    reachable: bool
    latency_ms: float | None
    detail: AuthProbeDetail
    provider: Literal["local", "supabase"]


def _safe_latency_ms(elapsed_seconds: float) -> float:
    """Convert elapsed seconds to a finite, non-negative millisecond latency."""
    latency_ms = round(elapsed_seconds * 1000.0, 3)
    if not math.isfinite(latency_ms) or latency_ms < 0.0:
        return 0.0
    return min(latency_ms, _MAX_LATENCY_MS)


def _auth_health_url(supabase_url: str) -> str:
    base = supabase_url.rstrip("/") + "/"
    return urljoin(base, "auth/v1/health")


def _auth_probe_result(
    *,
    reachable: bool,
    detail: AuthProbeDetail,
    provider: Literal["local", "supabase"],
    latency_ms: float | None = None,
) -> AuthProbeResult:
    return AuthProbeResult(
        reachable=reachable,
        latency_ms=latency_ms,
        detail=detail,
        provider=provider,
    )


def _result_from_auth_http_status(status_code: int, latency_ms: float) -> AuthProbeResult:
    """Map Auth health HTTP status to an allowlisted probe result."""
    if status_code >= 500:
        logger.warning("Supabase Auth health returned HTTP %s", status_code)
        return _auth_probe_result(
            reachable=False,
            latency_ms=latency_ms,
            detail=AuthProbeDetail.UNHEALTHY_STATUS,
            provider="supabase",
        )
    if status_code >= 400:
        logger.warning("Supabase Auth health probe rejected HTTP %s", status_code)
        return _auth_probe_result(
            reachable=False,
            latency_ms=latency_ms,
            detail=AuthProbeDetail.PROBE_FAILED,
            provider="supabase",
        )
    return _auth_probe_result(
        reachable=True,
        latency_ms=latency_ms,
        detail=AuthProbeDetail.HEALTHY,
        provider="supabase",
    )


def probe_supabase_auth(
    *,
    auth_provider: Literal["local", "supabase"],
    supabase_url: str | None,
    anon_key: str | None,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    client: httpx.Client | None = None,
) -> AuthProbeResult:
    """Probe Supabase Auth (GoTrue) health.

    When ``auth_provider`` is ``local``, returns a successful skip result so local
    unit tests / HS256 mode do not require a live Auth project. Otherwise issues
    ``GET {SUPABASE_URL}/auth/v1/health`` with the anon key as ``apikey`` and
    bearer. Latency is clamped to a safe non-negative millisecond range.

    Args:
        auth_provider: Active API auth mode (``local`` or ``supabase``).
        supabase_url: Project URL when using Supabase Auth.
        anon_key: Anon key used as ``apikey`` / bearer for the Auth HTTP API.
        timeout_seconds: HTTP timeout for the probe request (default 5s).
        client: Optional httpx client (tests); when omitted, a short-lived client
            is created and closed after the probe.

    Returns:
        :class:`AuthProbeResult` with connectivity, optional latency, and an
        allowlisted detail code. ``reachable`` is ``False`` for missing config,
        transport errors, or Auth HTTP 4xx/5xx on the health endpoint.
    """
    if auth_provider != "supabase":
        return _auth_probe_result(
            reachable=True,
            detail=AuthProbeDetail.SKIPPED_LOCAL,
            provider="local",
        )

    if not supabase_url or not anon_key:
        return _auth_probe_result(
            reachable=False,
            detail=AuthProbeDetail.NOT_CONFIGURED,
            provider="supabase",
        )

    url = _auth_health_url(supabase_url)
    headers = {
        "apikey": anon_key,
        "Authorization": f"Bearer {anon_key}",
    }
    owns_client = client is None
    http_client = client or httpx.Client(timeout=timeout_seconds)
    result: AuthProbeResult | None = None
    try:
        started = time.perf_counter()
        response = http_client.get(url, headers=headers)
        latency_ms = _safe_latency_ms(time.perf_counter() - started)
        result = _result_from_auth_http_status(response.status_code, latency_ms)
    except httpx.TimeoutException:
        logger.warning("Supabase Auth health probe timed out url=%s", url)
        result = _auth_probe_result(
            reachable=False,
            detail=AuthProbeDetail.UNREACHABLE,
            provider="supabase",
        )
    except httpx.HTTPError:
        logger.exception("Supabase Auth health probe failed url=%s", url)
        result = _auth_probe_result(
            reachable=False,
            detail=AuthProbeDetail.UNREACHABLE,
            provider="supabase",
        )
    except Exception:
        logger.exception("Supabase Auth health probe unexpected error")
        result = _auth_probe_result(
            reachable=False,
            detail=AuthProbeDetail.PROBE_FAILED,
            provider="supabase",
        )
    finally:
        if owns_client:
            http_client.close()
    assert result is not None
    return result
