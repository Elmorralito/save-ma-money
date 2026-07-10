"""FastAPI exception handlers aligned with PPT-031 auth contract §9.

Registers global handlers that normalize error payloads to ``{"detail": ...}`` JSON
responses. Maps domain ``ValueError`` messages for duplicate registration to HTTP 409,
validation failures to 422, and unhandled exceptions to 500 with server-side logging.

Key exports:
    register_exception_handlers: Attach all handlers to a ``FastAPI`` application instance.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_CONFLICT_MESSAGES = frozenset({"Username already registered", "Email already registered"})


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI application.

    Installs handlers for ``HTTPException``, ``RequestValidationError``, ``ValueError``,
    and a catch-all ``Exception`` handler that logs stack traces before returning 500.

    Args:
        app: FastAPI application to mutate in place.

    Returns:
        None. Handlers are registered as side effects on ``app``.
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Return ``{"detail": ...}`` for explicit HTTP errors raised by routes.

        Args:
            _request: Incoming request (unused).
            exc: Starlette/FastAPI HTTP exception with status, detail, and headers.

        Returns:
            JSON response preserving the exception status code and detail payload.
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        """Map Pydantic/request validation failures to HTTP 422.

        Args:
            _request: Incoming request (unused).
            exc: Validation error with structured ``errors()`` list.

        Returns:
            JSON response with ``detail`` set to the validation error list.
        """
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": exc.errors()})

    @app.exception_handler(ValueError)
    async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
        """Translate domain ``ValueError`` messages to 409 or 400 responses.

        Args:
            _request: Incoming request (unused).
            exc: Value error raised from services or validators.

        Returns:
            JSON response; duplicate registration messages map to HTTP 409, others to 400.
        """
        message = str(exc)
        if message in _CONFLICT_MESSAGES:
            return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": message})
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": message})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        """Log and mask unexpected exceptions as HTTP 500.

        Args:
            _request: Incoming request (unused).
            exc: Unhandled exception propagated from any route or dependency.

        Returns:
            Generic internal error JSON without leaking exception details to clients.
        """
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
