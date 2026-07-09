"""FastAPI application factory for papita_txnsapi."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.handlers import register_exception_handlers
from papita_txnsapi.middleware.request_logging import RequestLoggingMiddleware
from papita_txnsapi.routers.v1 import api_v1_router
from papita_txnsmodel.services.users import UsersService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Bootstrap password manager before auth routes run (NFR-08)."""
    UsersService.ensure_password_manager()
    logger.info("Application lifespan started — password manager ready")
    yield
    logger.info("Application lifespan shutdown")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application.

    Args:
        settings: Optional settings override (used in tests).

    Returns:
        Configured FastAPI instance with v1 routes mounted at ``/api/v1``.
    """
    app_settings = settings or get_settings()

    app = FastAPI(
        title=app_settings.APP_NAME,
        version=app_settings.APP_VERSION,
        debug=app_settings.DEBUG,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()
