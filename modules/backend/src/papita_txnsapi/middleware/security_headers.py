"""Security-headers middleware for papita_txnsapi (PPT-044).

Adds conservative browser-facing headers on every response. Avoids Content-Security-Policy
so Swagger UI under ``/api/docs`` keeps working when docs are enabled.
"""

from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=()",
    "X-Permitted-Cross-Domain-Policies": "none",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach baseline security headers without breaking JSON or Swagger responses."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        """Process a request and merge security headers onto the response."""
        response = await call_next(request)
        for header_name, header_value in _SECURITY_HEADERS.items():
            if header_name not in response.headers:
                response.headers[header_name] = header_value

        # Prevent shared proxies or browsers from caching sensitive financial API responses.
        if request.url.path.startswith("/api/v1/") and "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"

        # Enforce HSTS when served over HTTPS (direct or behind TLS-terminating proxy).
        proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").split(",")[0].strip().lower()
        if proto == "https" and "Strict-Transport-Security" not in response.headers:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
