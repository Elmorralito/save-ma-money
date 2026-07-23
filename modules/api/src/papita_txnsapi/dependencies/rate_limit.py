"""Rate-limit dependencies for auth (per-IP), health probes, and tenant API tiers.

Auth endpoints use a per-IP sliding window. Protected CRUD/report routes use
tenant-scoped Free/Pro/Enterprise quotas (minute + day windows) with Redis when
``REDIS_RATE_LIMIT_ENABLED`` is on. DB-touching health probes use a separate
per-IP window (PPT-044); ``/health/live`` stays unlimited.

Key exports:
    enforce_auth_login_rate_limit / register / oauth: Auth IP guards.
    enforce_health_rate_limit: Per-IP guard for DB/Auth/Redis-touching probes.
    enforce_tenant_api_rate_limit: Tenant API tier guard for protected routers.
"""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.api_tier import limits_for_tier, resolve_api_tier
from papita_txnsapi.core.rate_limit import RateLimitResult, get_rate_limiter_for_request
from papita_txnsapi.core.redis import get_redis_from_app
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsmodel.access.users.dto import UsersDTO


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
    result = get_rate_limiter_for_request(
        request,
        settings,
        fail_closed=settings.AUTH_RATE_LIMIT_FAIL_CLOSED,
    ).check(
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


def enforce_health_rate_limit(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Enforce per-IP rate limits on DB/Auth/Redis-touching health probes.

    Does not apply to ``GET /health/live`` (process liveness stays cheap).

    Args:
        request: Incoming health probe request.
        settings: Injected API settings with health limit configuration.

    Raises:
        HTTPException: 429 when attempts exceed ``HEALTH_RATE_LIMIT_PER_MINUTE``.
    """
    if not settings.HEALTH_RATE_LIMIT_ENABLED:
        return

    key = f"health-probe:{_client_ip(request)}"
    result = get_rate_limiter_for_request(request, settings).check(
        key,
        limit=settings.HEALTH_RATE_LIMIT_PER_MINUTE,
        window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
    )
    headers = _rate_limit_headers(result)
    request.state.rate_limit_headers = headers
    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many health probe requests. Try again later.",
            headers={**headers, "Retry-After": str(max(1, result.reset_at - int(time.time())))},
        )


def _merge_limit_headers(minute: RateLimitResult, day: RateLimitResult) -> dict[str, str]:
    """Prefer the tighter remaining quota for response headers."""
    if minute.limit <= 0 and day.limit <= 0:
        return {}
    if minute.limit <= 0:
        return _rate_limit_headers(day)
    if day.limit <= 0:
        return _rate_limit_headers(minute)
    # Report the window with fewer remaining requests (normalized by limit).
    minute_ratio = minute.remaining / minute.limit if minute.limit else 1.0
    day_ratio = day.remaining / day.limit if day.limit else 1.0
    chosen = minute if minute_ratio <= day_ratio else day
    return _rate_limit_headers(chosen)


def enforce_tenant_api_rate_limit(
    request: Request,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Enforce tenant-scoped Free/Pro/Enterprise API quotas on protected routes.

    Applies rolling per-minute and per-day windows keyed by ``owner_id``. Stores
    ``X-RateLimit-*`` headers on ``request.state`` for response middleware. Enterprise
    (unlimited) is a no-op. When ``API_RATE_LIMIT_ENABLED`` is false, skips checks.

    Args:
        request: Incoming HTTP request.
        owner: Authenticated tenant from JWT.
        settings: API settings with tier quotas and feature flags.

    Raises:
        HTTPException: 401 when owner id is missing; 429 when a quota is exceeded.
    """
    if not settings.API_RATE_LIMIT_ENABLED:
        return
    if owner.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    redis = get_redis_from_app(request.app) if settings.REDIS_ENABLED else None
    tier = resolve_api_tier(settings, owner.id, redis)
    limits = limits_for_tier(settings, tier)
    if limits.unlimited:
        request.state.rate_limit_headers = {
            "X-RateLimit-Limit": "0",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "0",
            "X-RateLimit-Tier": tier.value,
        }
        return

    limiter = get_rate_limiter_for_request(request, settings)
    owner_key = str(owner.id)
    minute = limiter.check(
        f"api:{owner_key}:min",
        limit=limits.per_minute,
        window_seconds=60,
    )
    day = limiter.check(
        f"api:{owner_key}:day",
        limit=limits.per_day,
        window_seconds=86_400,
    )
    headers = {**_merge_limit_headers(minute, day), "X-RateLimit-Tier": tier.value}
    request.state.rate_limit_headers = headers

    if not minute.allowed or not day.allowed:
        denied = minute if not minute.allowed else day
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="API rate limit exceeded for your plan. Try again later.",
            headers={
                **headers,
                "Retry-After": str(max(1, denied.reset_at - int(time.time()))),
            },
        )
