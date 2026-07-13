# type: ignore
"""Environment-backed application settings for the Papita Transactions API.

Loads configuration from ``environments/$PAPITA_ENV/.env`` (see
:mod:`papita_txnsapi.config.environment`) via Pydantic Settings. Establishes the
shared SQLAlchemy connector, configures model and API loggers, and exposes JWT,
CORS, database pool, and auth rate-limit parameters consumed by
:mod:`papita_txnsapi.main` and FastAPI dependencies.
"""

from __future__ import annotations

import logging
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Literal, Self, Type
from urllib.parse import urlparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from papita_txnsapi import LIB_NAME as API_LIB_NAME
from papita_txnsapi import __version__ as API_VERSION
from papita_txnsapi.config.environment import ENV_VAR_NAME, active_environment, env_file_for_settings
from papita_txnsmodel import LIB_NAME as MODEL_LIB_NAME
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.configutils import configure_logger
from papita_txnsmodel.utils.enums import FallbackAction

# API package root (modules/api/src) — logger YAML only; secrets live under environments/.
PROJECT_ROOT = Path(__file__).parent.parent.parent
LOGGER_CONFIG_PATH = Path(__file__).parent / "logger.yaml"

logger = logging.getLogger(API_LIB_NAME)


def is_supabase_transaction_pooler_url(url: str) -> bool:
    """Return True when ``url`` targets a Supabase transaction pooler (B1).

    Args:
        url: SQLAlchemy / PostgreSQL connection URL.

    Returns:
        True for ``:6543``, ``*.pooler.supabase.com``, or ``pgbouncer=true`` query.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host == "pooler.supabase.com" or host.endswith(".pooler.supabase.com"):
        return True
    if parsed.port == 6543:
        return True
    return "pgbouncer=true" in url.lower()


def postgres_engine_kwargs(*, url: str, pool_size: int) -> dict:
    """Build SQLAlchemy ``create_engine`` kwargs for PostgreSQL (PPT-039).

    Always enables ``pool_pre_ping``. Uses a bounded ``pool_size`` from Settings.
    On transaction-pooler URLs, sets ``max_overflow=0`` so workers do not burst
    extra connections against PgBouncer transaction mode.

    Args:
        url: PostgreSQL SQLAlchemy URL.
        pool_size: Configured ``DATABASE_POOL_SIZE``.

    Returns:
        Keyword arguments passed to :meth:`SQLDatabaseConnector.establish`.
    """
    kwargs: dict = {"pool_pre_ping": True, "pool_size": pool_size}
    if is_supabase_transaction_pooler_url(url):
        kwargs["max_overflow"] = 0
    return kwargs


class Settings(BaseSettings):
    """Runtime configuration loaded from process env and ``environments/$PAPITA_ENV/.env``.

    Set ``PAPITA_ENV`` to ``local`` (default), ``staging``, or ``production``. Prefer
    ``get_settings()`` so the correct env file is bound for the active environment.

    Attributes:
        APP_NAME: Human-readable application title used in startup logs.
        APP_VERSION: Semantic version re-exported from package metadata.
        DEBUG: When ``True``, enables verbose diagnostics (reserved for future use).
        HOST: Uvicorn bind address.
        PORT: Uvicorn bind port.
        DATABASE_URL: PostgreSQL SQLAlchemy URL or an established connector class.
            When unset, falls back to the model default storage with a warning.
        LOG_LEVEL: Root log level applied to model and API loggers on init.
        LOG_FILE: Optional path to a logging YAML file; defaults to ``logger.yaml``.
        DATABASE_POOL_SIZE: SQLAlchemy connection pool size for PostgreSQL
            (wired into ``create_engine`` via PPT-039; default 5).
        JWT_SECRET_KEY: Symmetric signing key for access tokens (required).
        JWT_TOKEN_TYPE: Expected ``type`` claim for bearer tokens.
        JWT_ALGORITHM: JWT signing algorithm (default HS256).
        JWT_EXPIRATION_TIME_SECONDS: Access token lifetime in seconds.
        ALLOWED_ORIGINS: CORS allowed origins list.
        FALLBACK_ACTION: Behavior when optional model fallbacks trigger.
        AUTH_RATE_LIMIT_ENABLED: Toggle per-IP auth endpoint rate limiting (B0).
        AUTH_RATE_LIMIT_WINDOW_SECONDS: Sliding window length for auth limits.
        AUTH_LOGIN_RATE_LIMIT_PER_MINUTE: Max login attempts per window per IP.
        AUTH_REGISTER_RATE_LIMIT_PER_MINUTE: Max register attempts per window per IP.
    """

    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    # Application
    APP_NAME: str = "Save Ma Money API"
    APP_VERSION: str = API_VERSION
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str | Type[SQLDatabaseConnector] | None = None
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG"
    LOG_FILE: str | None = None
    DATABASE_POOL_SIZE: int = 5
    JWT_SECRET_KEY: str
    JWT_TOKEN_TYPE: Literal["bearer", "refresh"] = "bearer"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_TIME_SECONDS: int = 3600
    ALLOWED_ORIGINS: list[str] = ["*"]
    FALLBACK_ACTION: FallbackAction = FallbackAction.LOG

    # Auth hardening — per-IP sliding window (single-instance B0; use Redis post-MVP)
    AUTH_RATE_LIMIT_ENABLED: bool = True
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60
    AUTH_LOGIN_RATE_LIMIT_PER_MINUTE: int = 10
    AUTH_REGISTER_RATE_LIMIT_PER_MINUTE: int = 5

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def coerce_database_url(
        cls, value: str | Type[SQLDatabaseConnector] | None
    ) -> str | Type[SQLDatabaseConnector] | None:
        """Accept a connector class, a non-empty URL string, or ``None``.

        Engine establishment is deferred to :meth:`build_model` so ``DATABASE_POOL_SIZE``
        and pooler-safe options can be applied together (PPT-039).

        Args:
            value: Raw env string, an already-established connector class, or ``None``.

        Returns:
            Normalized URL string, connector class, or ``None``.
        """
        if isinstance(value, type) and issubclass(value, SQLDatabaseConnector):
            return value
        if isinstance(value, str) and value.strip() != "":
            return value.strip()
        return None

    @model_validator(mode="after")
    def build_model(self) -> Self:
        """Establish the DB connector with pooler-safe engine opts, then configure loggers.

        Returns:
            The validated settings instance with ``DATABASE_URL`` as a connector class.
        """
        url_or_connector = self.DATABASE_URL
        if isinstance(url_or_connector, type) and issubclass(url_or_connector, SQLDatabaseConnector):
            connector: Type[SQLDatabaseConnector] = url_or_connector
        elif isinstance(url_or_connector, str):
            connector = SQLDatabaseConnector.establish(
                connection=url_or_connector,
                **postgres_engine_kwargs(url=url_or_connector, pool_size=self.DATABASE_POOL_SIZE),
            )
        else:
            warnings.warn(
                "The connection has been set with the default storage option, since the provided DATABASE_URL is None",
                stacklevel=2,
            )
            connector = SQLDatabaseConnector.establish(connection=None)

        object.__setattr__(self, "DATABASE_URL", connector)

        log_config = Path(self.LOG_FILE) if self.LOG_FILE else LOGGER_CONFIG_PATH
        configure_logger(logger_name=MODEL_LIB_NAME, config=log_config, level=self.LOG_LEVEL)
        configure_logger(logger_name=API_LIB_NAME, config=log_config, level=self.LOG_LEVEL)
        logger.info("Application %s %s initialized", self.APP_NAME, self.APP_VERSION)
        return self


@lru_cache()
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance for dependency injection.

    Loads ``environments/$PAPITA_ENV/.env`` when present; otherwise process env only.
    Clear the cache after changing ``PAPITA_ENV`` in tests.

    Returns:
        Singleton settings for the active :data:`PAPITA_ENV`.
    """
    env_path = env_file_for_settings()
    if env_path is not None:
        logger.debug("Loading settings from %s (%s=%s)", env_path, ENV_VAR_NAME, active_environment())
        return Settings(_env_file=env_path)
    return Settings()
