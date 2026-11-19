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
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach baseline security headers without breaking JSON or Swagger responses."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        """Process a request and merge security headers onto the response.

        Args:
            request: Incoming Starlette request.
            call_next: Downstream ASGI handler.

        Returns:
            Response with security headers set when not already present.
        """
        response = await call_next(request)
        for header_name, header_value in _SECURITY_HEADERS.items():
            if header_name not in response.headers:
                response.headers[header_name] = header_value
        return response
