"""Request logging middleware.

Starlette middleware that records method, path, HTTP status, and wall-clock duration
for every request. Emits structured INFO logs suitable for local development and B0
operational visibility.

Key exports:
    RequestLoggingMiddleware: ASGI middleware registered on the FastAPI app.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status code, and elapsed time for each request.

    Wraps the downstream ASGI handler, measures latency with ``time.perf_counter``,
    and logs a single INFO line after the response is produced.
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        """Process a request and log timing metadata after the response is ready.

        Args:
            request: Incoming Starlette request.
            call_next: Callable that invokes the next middleware or route handler.

        Returns:
            Response from the downstream handler, unchanged.
        """
        start = time.perf_counter()
        response = await call_next(request)
        rate_headers = getattr(request.state, "rate_limit_headers", None)
        if isinstance(rate_headers, dict):
            for header_name, header_value in rate_headers.items():
                if header_name not in response.headers:
                    response.headers[header_name] = str(header_value)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %s (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
