"""FastAPI application factory for papita_txnsapi.

Constructs the runnable API with CORS, security headers, optional TrustedHost,
request logging, global exception handlers, and v1 routers mounted at ``/api/v1``.
Bootstraps password hashing and optional Redis on startup via the application lifespan.

Key exports:
    lifespan: Async context manager for startup/shutdown hooks.
    create_app: Build a configured ``FastAPI`` instance (optionally with test settings).
    app: Module-level application used by ASGI servers (e.g. uvicorn).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.handlers import register_exception_handlers
from papita_txnsapi.core.rate_limit import bind_rate_limiters
from papita_txnsapi.core.redis import close_redis, init_redis
from papita_txnsapi.middleware.client_contract import ClientContractMiddleware
from papita_txnsapi.middleware.request_logging import RequestLoggingMiddleware
from papita_txnsapi.middleware.security_headers import SecurityHeadersMiddleware
from papita_txnsapi.routers.v1 import api_v1_router
from papita_txnsmodel.services.users import UsersService

logger = logging.getLogger(__name__)

_PROD_CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
_PROD_CORS_HEADERS = [
    "Authorization",
    "Content-Type",
    "Accept",
    "Idempotency-Key",
    "X-Request-ID",
]


def _build_lifespan(settings: Settings):
    """Build a lifespan context that binds Redis to the given settings."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Bootstrap shared resources on startup and release them on shutdown.

        Ensures ``UsersService`` password manager is initialized before auth routes
        accept traffic (NFR-08). Optionally opens a Redis pool when enabled (PPT-043).

        Args:
            app: FastAPI application instance; ``app.state.redis`` is set when enabled.

        Yields:
            Control back to FastAPI while the application is serving requests.
        """
        UsersService.ensure_password_manager()
        app.state.redis = init_redis(settings)
        bind_rate_limiters(app, settings)
        logger.info(
            "Application lifespan started — password manager ready (redis=%s)",
            "on" if app.state.redis is not None else "off",
        )
        try:
            yield
        finally:
            close_redis(getattr(app.state, "redis", None))
            app.state.redis = None
            app.state.rate_limiter = None
            app.state.rate_limiter_fail_closed = None
            logger.info("Application lifespan shutdown")

    return lifespan


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application.

    Registers CORS, security headers, optional TrustedHost, request-logging middleware,
    global exception handlers, OpenAPI documentation paths (when enabled), and the v1
    API router.

    Args:
        settings: Optional settings override (used in tests); defaults to ``get_settings()``.

    Returns:
        Configured ``FastAPI`` instance with v1 routes mounted at ``/api/v1``.
    """
    app_settings = settings or get_settings()
    docs_enabled = app_settings.DEBUG or app_settings.DOCS_ENABLED

    app = FastAPI(
        title=app_settings.APP_NAME,
        version=app_settings.APP_VERSION,
        debug=app_settings.DEBUG,
        lifespan=_build_lifespan(app_settings),
        docs_url="/api/docs" if docs_enabled else None,
        redoc_url="/api/redoc" if docs_enabled else None,
        openapi_url="/api/openapi.json" if docs_enabled else None,
    )
    app.state.settings = app_settings

    origins = list(app_settings.ALLOWED_ORIGINS)
    # Never combine wildcard origins with credentialed CORS (browser-unsafe).
    allow_credentials = "*" not in origins
    allow_methods = ["*"] if app_settings.DEBUG else _PROD_CORS_METHODS
    allow_headers = ["*"] if app_settings.DEBUG else _PROD_CORS_HEADERS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=allow_methods,
        allow_headers=allow_headers,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(ClientContractMiddleware)
    # Settings requires non-empty ALLOWED_HOSTS when DEBUG=false (staging/prod).
    if not app_settings.DEBUG:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(app_settings.ALLOWED_HOSTS))
    app.add_middleware(RequestLoggingMiddleware)

    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()
