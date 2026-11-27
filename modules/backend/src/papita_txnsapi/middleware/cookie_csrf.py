"""Origin/Referer & Fetch-Metadata CSRF guard for cookie-authenticated API mutations.

Only activates on unsafe HTTP methods (``POST``, ``PUT``, ``PATCH``, ``DELETE``)
when the request carries the ``papita_access_token`` cookie without an explicit
``Authorization: Bearer`` header. Pure Bearer-token API clients are unaffected.
"""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from papita_txnsapi.dependencies.auth import AUTH_ACCESS_COOKIE

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _normalize_origin(raw: str) -> str | None:
    parsed = urlsplit(raw.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def _allowed_origins_for_request(request: Request) -> set[str]:
    allowed: set[str] = set()
    settings = getattr(request.app.state, "settings", None)
    if settings is not None:
        for origin in getattr(settings, "ALLOWED_ORIGINS", ()):
            norm = _normalize_origin(str(origin))
            if norm:
                allowed.add(norm)
    host = (request.headers.get("host") or "").strip().lower()
    if host:
        proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "http").split(",")[0].strip().lower()
        allowed.add(f"{proto}://{host}")
        allowed.add(f"http://{host}")
        allowed.add(f"https://{host}")
    return allowed


class CookieCsrfMiddleware(BaseHTTPMiddleware):
    """Reject cross-site state-changing requests authenticated via HttpOnly session cookies."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        if request.method.upper() not in _UNSAFE_METHODS:
            return await call_next(request)

        # Bearer-authenticated requests are immune to ambient cookie CSRF.
        auth_header = (request.headers.get("authorization") or "").strip()
        if auth_header.lower().startswith("bearer "):
            return await call_next(request)

        if not request.cookies.get(AUTH_ACCESS_COOKIE):
            return await call_next(request)

        # Reject explicit browser cross-site fetch metadata immediately.
        sec_fetch_site = (request.headers.get("sec-fetch-site") or "").strip().lower()
        if sec_fetch_site == "cross-site":
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-site state-changing request rejected (CSRF protection)."},
            )

        origin_raw = request.headers.get("origin")
        referer_raw = request.headers.get("referer")
        allowed = _allowed_origins_for_request(request)

        if origin_raw:
            origin = _normalize_origin(origin_raw)
            if not origin or origin not in allowed:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Origin header rejected by CSRF protection."},
                )
        elif referer_raw:
            referer_origin = _normalize_origin(referer_raw)
            if not referer_origin or referer_origin not in allowed:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Referer header rejected by CSRF protection."},
                )
        else:
            # When both Origin and Referer are absent (e.g. stripped by Referrer-Policy),
            # require a non-simple custom header or same-origin Fetch Metadata.
            x_requested_with = (request.headers.get("x-requested-with") or "").strip()
            if sec_fetch_site != "same-origin" and not x_requested_with:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Missing Origin/Referer and X-Requested-With header (CSRF protection)."},
                )

        return await call_next(request)
