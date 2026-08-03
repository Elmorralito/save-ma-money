"""CSRF guard for cookie-authenticated BFF / API mutations (PPT-049).

When a request carries the BFF session cookie and **no** ``Authorization: Bearer``
header, unsafe methods must include ``X-Papita-CSRF`` matching the server-side
session CSRF token. SameSite cookies alone are not enough for all browsers/tools.

Login/register are exempt so a stale cookie cannot block a new sign-in.
Token-path clients (``make auth-smoke``, Bearer) skip this middleware path.
"""

from __future__ import annotations

import hmac
import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from papita_txnsapi.config.settings import Settings
from papita_txnsapi.core.bff_session import (
    BFF_CSRF_HEADER,
    BFF_SESSION_COOKIE,
    DEFAULT_BFF_SESSION_MAX_AGE_SECONDS,
    BffSessionStore,
    BffSessionStoreUnavailableError,
)
from papita_txnsapi.core.redis import get_redis_from_app

logger = logging.getLogger(__name__)

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
_CSRF_EXEMPT_PATHS = frozenset(
    {
        "/api/v1/bff/auth/login",
        "/api/v1/bff/auth/register",
    }
)


def _csrf_required(request: Request) -> bool:
    """Return whether this request must present a matching CSRF header.

    Safe methods, login/register, and Bearer-authenticated calls are exempt.
    """
    if request.method in _SAFE_METHODS:
        return False
    if request.url.path in _CSRF_EXEMPT_PATHS:
        return False
    authorization = request.headers.get("authorization") or ""
    if authorization.lower().startswith("bearer "):
        return False
    return bool(request.cookies.get(BFF_SESSION_COOKIE))


class BffCsrfMiddleware(BaseHTTPMiddleware):
    """Reject cookie-session mutations that omit or mismatch the CSRF header."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Enforce CSRF for cookie-session mutations; otherwise continue."""
        if not _csrf_required(request):
            return await call_next(request)

        session_id = request.cookies.get(BFF_SESSION_COOKIE) or ""
        settings: Settings | None = getattr(request.app.state, "settings", None)
        redis_enabled = bool(settings.REDIS_ENABLED) if settings is not None else False
        ttl = (
            int(getattr(settings, "BFF_SESSION_MAX_AGE_SECONDS", DEFAULT_BFF_SESSION_MAX_AGE_SECONDS))
            if settings is not None
            else DEFAULT_BFF_SESSION_MAX_AGE_SECONDS
        )
        client = get_redis_from_app(request.app) if redis_enabled else None
        store = BffSessionStore(client, default_ttl_seconds=ttl, fail_closed=redis_enabled)
        try:
            record = store.get(session_id)
        except BffSessionStoreUnavailableError:
            logger.warning("BFF CSRF skipped: session store unavailable path=%s", request.url.path)
            return JSONResponse(
                status_code=503,
                content={"detail": "BFF session store unavailable"},
            )
        if record is None:
            return await call_next(request)

        provided = (request.headers.get(BFF_CSRF_HEADER) or "").strip()
        if not provided or not secrets_compare(provided, record.csrf_token):
            logger.info("BFF CSRF rejected method=%s path=%s", request.method, request.url.path)
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF validation failed"},
                headers={"X-Papita-Error-Code": "csrf_failed"},
            )
        return await call_next(request)


def secrets_compare(left: str, right: str) -> bool:
    """Constant-time string compare for CSRF tokens."""
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


__all__ = ["BffCsrfMiddleware", "BFF_CSRF_HEADER", "BFF_SESSION_COOKIE"]
