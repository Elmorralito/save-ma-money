"""FastAPI exception handlers aligned with PPT-031 auth contract §9.

Registers global handlers that normalize error payloads to ``{"detail": ...}`` JSON
responses. Maps domain ``ValueError`` messages for duplicate registration to HTTP 409,
tenancy misses to 404 (or temporary compat 400), validation failures to 422, and
unhandled exceptions to 500 with server-side logging. Attaches ``X-Papita-Error-Code``
for PPT-044 client migration (see :mod:`papita_txnsapi.core.client_contract`).

Key exports:
    register_exception_handlers: Attach all handlers to a ``FastAPI`` application instance.
"""

from __future__ import annotations

import logging
import re

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from papita_txnsapi.config.settings import Settings
from papita_txnsapi.core.client_contract import (
    COMPAT_SUNSET_DATE,
    ERROR_INVALID_REQUEST,
    ERROR_REPORT_ACCOUNT_NOT_FOUND,
    HEADER_DEPRECATION,
    HEADER_ERROR_CODE,
    HEADER_SUNSET,
    error_code_for_validation_errors,
    error_code_for_value_error,
    reports_foreign_account_status,
)

logger = logging.getLogger(__name__)

_CONFLICT_MESSAGES = frozenset({"Username already registered", "Email already registered"})
_TENANCY_NOT_FOUND_MESSAGES = frozenset(
    {
        "Account not found for tenant.",
        "Category not found for tenant.",
        "Transaction not found for tenant.",
    }
)
_INTERNAL_LEAK_PATTERN = re.compile(
    r"(psycopg|sqlalchemy|asyncpg|operationalerror|programmingerror|traceback|postgres://|postgresql\+)",
    re.IGNORECASE,
)


def _settings_from_request(request: Request) -> Settings | None:
    """Return app-bound settings when present on ``request.app.state``."""
    settings = getattr(request.app.state, "settings", None)
    return settings if isinstance(settings, Settings) else None


def _safe_client_message(message: str) -> str:
    """Return a client-safe detail string for domain ``ValueError`` messages.

    Args:
        message: Raw exception text.

    Returns:
        Original message when it looks like a domain error; otherwise a generic detail.
    """
    if not message or _INTERNAL_LEAK_PATTERN.search(message):
        return "Invalid request"
    return message


def _with_error_code(headers: dict[str, str] | None, code: str | None) -> dict[str, str] | None:
    """Merge an error-code header into an optional header mapping."""
    if code is None:
        return headers
    merged = dict(headers or {})
    merged[HEADER_ERROR_CODE] = code
    return merged


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
            JSON response with ``detail`` set to the validation error list and an
            optional ``X-Papita-Error-Code`` for bulk/extra-field failures.
        """
        errors = exc.errors()
        headers = _with_error_code(None, error_code_for_validation_errors(errors))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": errors},
            headers=headers,
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """Translate domain ``ValueError`` messages to 409, 404/400, or 400 responses.

        Args:
            request: Incoming request (reads ``app.state.settings`` for compat flags).
            exc: Value error raised from services or validators.

        Returns:
            JSON response; duplicate registration → 409, tenancy misses → 404
            (or temporary compat 400), other safe domain messages → 400,
            suspected driver leaks → generic 400. Adds ``X-Papita-Error-Code`` when known.
        """
        message = str(exc)
        settings = _settings_from_request(request)
        if message in _CONFLICT_MESSAGES:
            return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": message})
        if message in _TENANCY_NOT_FOUND_MESSAGES:
            status_code = (
                reports_foreign_account_status(settings)
                if settings is not None and message == "Account not found for tenant."
                else status.HTTP_404_NOT_FOUND
            )
            headers: dict[str, str] = {HEADER_ERROR_CODE: ERROR_REPORT_ACCOUNT_NOT_FOUND}
            if (
                settings is not None
                and message == "Account not found for tenant."
                and settings.API_COMPAT_LEGACY_REPORT_ACCOUNT_400
            ):
                headers[HEADER_DEPRECATION] = "true"
                headers[HEADER_SUNSET] = COMPAT_SUNSET_DATE
            return JSONResponse(status_code=status_code, content={"detail": message}, headers=headers)

        safe = _safe_client_message(message)
        code = error_code_for_value_error(message)
        if safe == "Invalid request":
            code = ERROR_INVALID_REQUEST
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": safe},
            headers=_with_error_code(None, code),
        )

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
