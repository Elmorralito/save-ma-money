"""Rate-limit dependencies for authentication routes."""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.rate_limit import RateLimitResult, get_rate_limiter


def _client_ip(request: Request) -> str:
    """Resolve client IP for rate-limit keys (direct connection in B0)."""
    if request.client is None:
        return "unknown"
    return request.client.host


def _rate_limit_headers(result: RateLimitResult) -> dict[str, str]:
    return {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
        "X-RateLimit-Reset": str(result.reset_at),
    }


def _enforce_rate_limit(request: Request, settings: Settings, *, scope: str, limit: int) -> None:
    if not settings.AUTH_RATE_LIMIT_ENABLED:
        return

    key = f"{scope}:{_client_ip(request)}"
    result = get_rate_limiter().check(
        key,
        limit=limit,
        window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
    )
    headers = _rate_limit_headers(result)
    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Try again later.",
            headers={**headers, "Retry-After": str(max(1, result.reset_at - int(time.time())))},
        )


def enforce_auth_login_rate_limit(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Limit login attempts per client IP."""
    _enforce_rate_limit(
        request,
        settings,
        scope="auth-login",
        limit=settings.AUTH_LOGIN_RATE_LIMIT_PER_MINUTE,
    )


def enforce_auth_register_rate_limit(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Limit registration attempts per client IP."""
    _enforce_rate_limit(
        request,
        settings,
        scope="auth-register",
        limit=settings.AUTH_REGISTER_RATE_LIMIT_PER_MINUTE,
    )
