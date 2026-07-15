"""Rate-limit dependencies for authentication routes.

FastAPI dependencies that enforce per-IP sliding-window limits on login, register,
OAuth/SSO, and refresh endpoints. Emits ``X-RateLimit-*`` and ``Retry-After``
headers; no-ops when rate limiting is disabled in settings.

Key exports:
    enforce_auth_login_rate_limit: Guard ``/auth/login`` attempts.
    enforce_auth_register_rate_limit: Guard ``/auth/register`` attempts.
    enforce_auth_oauth_rate_limit: Guard OAuth start/callback/SSO/refresh.
"""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.rate_limit import RateLimitResult, get_rate_limiter


def _client_ip(request: Request) -> str:
    """Resolve client IP for rate-limit bucket keys.

    Uses the direct Starlette client host in B0; does not parse proxy headers.

    Args:
        request: Incoming HTTP request.

    Returns:
        Client host string, or ``"unknown"`` when ``request.client`` is unset.
    """
    if request.client is None:
        return "unknown"
    return request.client.host


def _rate_limit_headers(result: RateLimitResult) -> dict[str, str]:
    """Build standard rate-limit response headers from a check result.

    Args:
        result: Outcome of the in-memory limiter check.

    Returns:
        Mapping of ``X-RateLimit-Limit``, ``Remaining``, and ``Reset`` header values.
    """
    return {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
        "X-RateLimit-Reset": str(result.reset_at),
    }


def _enforce_rate_limit(request: Request, settings: Settings, *, scope: str, limit: int) -> None:
    """Apply a scoped per-IP rate limit when enabled in settings.

    Args:
        request: Incoming HTTP request used to derive the client IP.
        settings: API settings controlling enable flag, window, and limits.
        scope: Logical bucket prefix (e.g. ``auth-login``).
        limit: Maximum requests per window for this scope.

    Raises:
        HTTPException: 429 when the client exceeds the configured limit.
    """
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
    """Enforce per-IP rate limits on login attempts.

    Args:
        request: Incoming login request.
        settings: Injected API settings with login limit and window configuration.

    Raises:
        HTTPException: 429 when login attempts exceed ``AUTH_LOGIN_RATE_LIMIT_PER_MINUTE``.
    """
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
    """Enforce per-IP rate limits on registration attempts.

    Args:
        request: Incoming registration request.
        settings: Injected API settings with register limit and window configuration.

    Raises:
        HTTPException: 429 when register attempts exceed ``AUTH_REGISTER_RATE_LIMIT_PER_MINUTE``.
    """
    _enforce_rate_limit(
        request,
        settings,
        scope="auth-register",
        limit=settings.AUTH_REGISTER_RATE_LIMIT_PER_MINUTE,
    )


def enforce_auth_oauth_rate_limit(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Enforce per-IP rate limits on OAuth start/callback, SSO, and refresh.

    Args:
        request: Incoming OAuth/SSO/refresh request.
        settings: Injected API settings with OAuth limit and window configuration.

    Raises:
        HTTPException: 429 when attempts exceed ``AUTH_OAUTH_RATE_LIMIT_PER_MINUTE``.
    """
    _enforce_rate_limit(
        request,
        settings,
        scope="auth-oauth",
        limit=settings.AUTH_OAUTH_RATE_LIMIT_PER_MINUTE,
    )
