# type: ignore
"""Environment-backed application settings for the Papita Transactions API.

Loads configuration from ``modules/api/src/.env`` (via :data:`PROJECT_ROOT`) using
Pydantic Settings. Establishes the shared SQLAlchemy connector, configures model and
API loggers, and exposes JWT, CORS, database pool, and auth rate-limit parameters
consumed by :mod:`papita_txnsapi.main` and FastAPI dependencies.
"""

import logging
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Literal, Self, Type

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from papita_txnsapi import LIB_NAME as API_LIB_NAME
from papita_txnsapi import __version__ as API_VERSION
from papita_txnsmodel import LIB_NAME as MODEL_LIB_NAME
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.configutils import configure_logger
from papita_txnsmodel.utils.enums import FallbackAction

PROJECT_ROOT = Path(__file__).parent.parent.parent
LOGGER_CONFIG_PATH = Path(__file__).parent / "logger.yaml"

logger = logging.getLogger(API_LIB_NAME)


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables and ``.env``.

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
        DATABASE_POOL_SIZE: SQLAlchemy connection pool size for PostgreSQL.
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

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8")

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
    def validate_database_url(cls, value: str | Type[SQLDatabaseConnector] | None) -> Type[SQLDatabaseConnector]:
        """Normalize ``DATABASE_URL`` into an established ``SQLDatabaseConnector`` class.

        Args:
            value: Raw env string, an already-established connector class, or ``None``.

        Returns:
            The connector class bound to the resolved database URL.

        Note:
            Emits a runtime warning when ``DATABASE_URL`` is missing so local tests
            without Postgres still boot with the model default storage fallback.
        """
        if isinstance(value, type) and issubclass(value, SQLDatabaseConnector):
            return value

        if isinstance(value, str) and value.strip() != "":
            return SQLDatabaseConnector.establish(connection=value)

        warnings.warn(
            "The connection has been set with the default storage option, since the provided DATABASE_URL is None",
            stacklevel=2,
        )
        return SQLDatabaseConnector.establish(connection=None)

    @model_validator(mode="after")
    def build_model(self) -> Self:
        """Configure loggers and emit a startup info line after field validation.

        Returns:
            The validated settings instance (unchanged aside from side effects).
        """
        log_config = Path(self.LOG_FILE) if self.LOG_FILE else LOGGER_CONFIG_PATH
        configure_logger(logger_name=MODEL_LIB_NAME, config=log_config, level=self.LOG_LEVEL)
        configure_logger(logger_name=API_LIB_NAME, config=log_config, level=self.LOG_LEVEL)
        logger.info("Application %s %s initialized", self.APP_NAME, self.APP_VERSION)
        return self


@lru_cache()
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance for dependency injection.

    Returns:
        Singleton settings loaded once per process from environment and ``.env``.
    """
    return Settings()
