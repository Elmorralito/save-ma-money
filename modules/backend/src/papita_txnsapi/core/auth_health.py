"""Self-hosted authentication readiness probes for health endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class AuthProbeDetail(StrEnum):
    """Allowlisted Auth probe detail strings returned to HTTP clients."""

    HEALTHY = "local auth healthy"
    SKIPPED_LOCAL = "local auth active"


@dataclass(frozen=True, slots=True)
class AuthProbeResult:
    """Outcome of the self-hosted Auth readiness probe."""

    reachable: bool
    latency_ms: float | None
    detail: AuthProbeDetail
    provider: Literal["local"] = "local"


def probe_local_auth(*, auth_provider: str = "local") -> AuthProbeResult:
    """Return skipped readiness for self-hosted HS256 + Google OAuth PKCE auth.

    Local mode has no external Auth network dependency, so the probe reports
    reachable with ``SKIPPED_LOCAL`` (no RTT).
    """
    _ = auth_provider
    return AuthProbeResult(
        reachable=True,
        latency_ms=None,
        detail=AuthProbeDetail.SKIPPED_LOCAL,
        provider="local",
    )
