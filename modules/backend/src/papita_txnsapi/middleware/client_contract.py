"""Attach PPT-044 client-contract discovery headers to ``/api/v1`` responses."""

from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from papita_txnsapi.config.settings import Settings
from papita_txnsapi.core.client_contract import contract_discovery_headers


class ClientContractMiddleware(BaseHTTPMiddleware):
    """Advertise PPT-044 limits/status codes on versioned API responses."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        """Process a request and merge contract headers onto ``/api/v1`` responses.

        Args:
            request: Incoming Starlette request.
            call_next: Downstream ASGI handler.

        Returns:
            Response with discovery headers when the path is under ``/api/v1``.
        """
        response = await call_next(request)
        if not request.url.path.startswith("/api/v1"):
            return response

        settings = getattr(request.app.state, "settings", None)
        if isinstance(settings, Settings):
            for header_name, header_value in contract_discovery_headers(settings).items():
                if header_name not in response.headers:
                    response.headers[header_name] = header_value

        extra = getattr(request.state, "extra_response_headers", None)
        if isinstance(extra, dict):
            for header_name, header_value in extra.items():
                if header_name not in response.headers:
                    response.headers[header_name] = str(header_value)
        return response
