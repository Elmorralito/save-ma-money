# type: ignore
"""Application configuration for the Papita Transactions API.

Loads typed settings from environment variables and an optional ``.env`` file at the
project root, validates paths and database connectivity, and applies shared logging
configuration for both the API and model packages. Exposes a cached accessor so
settings are constructed once per process.

Key exports:
    APISettings: Pydantic ``BaseSettings`` model for all runtime configuration.
    get_settings: Memoized factory returning a single ``APISettings`` instance.

Module constants:
    PROJECT_ROOT: Backend package project root (three levels above this file).
    DEFAULT_LOGGER_CONFIG_PATH: Packaged default ``logger.yaml`` path used when
        ``LOGGER_CONFIG_PATH`` is unset.
"""

import importlib.resources as importlib_resources
import logging
import os
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Self, Type

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from papita_txnsapi import API_VERSION
from papita_txnsapi import LIB_NAME as API_LIB_NAME
from papita_txnsmodel import LIB_NAME as MODEL_LIB_NAME
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.helpers.enums import FallbackAction
from papita_txnsmodel.utils.configutils import configure_logger

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_LOGGER_CONFIG_PATH = str(importlib_resources.files(f"{API_LIB_NAME}.core.misc").joinpath("logger.yaml"))

logger = logging.getLogger(API_LIB_NAME)


class APISettings(BaseSettings):
    """Strongly typed API runtime settings with env and ``.env`` file support.

    Values are read from the environment (and optional ``.env`` under ``PROJECT_ROOT``)
    with sensible defaults for local development. Database and logger paths are
    normalized at validation time; JWT and CORS-related fields should be set
    explicitly for production.

    Attributes:
        model_config: Pydantic settings config (env file path, encoding, arbitrary
            types allowed for connector classes).
        APP_NAME: Human-readable application name.
        APP_VERSION: API version string from package metadata.
        DEBUG: When True, relaxes some production safeguards (e.g. CORS warnings).
        HOST: Bind address for the ASGI server.
        PORT: Listen port for the ASGI server.
        DATABASE_URL: Connection string, ``SQLDatabaseConnector`` subclass, or None
            (default connector with optional warning).
        LOG_LEVEL: Named log level or numeric level for application loggers.
        LOGGER_CONFIG_PATH: Path to YAML logging configuration; defaults to packaged
            ``logger.yaml`` if omitted.
        DATABASE_POOL_SIZE: Connection pool size bounds (1–100).
        JWT_SECRET_KEY: Secret for signing JWTs (alphanumeric, underscore, hyphen).
        JWT_TOKEN_TYPE: Primary token kind label (e.g. bearer).
        JWT_ALGORITHM: Signing algorithm identifier (e.g. HS256).
        JWT_EXPIRATION_TIME_SECONDS: Access token lifetime in seconds.
        JWT_SLIDING_REFRESH_ENABLED: Whether sliding refresh behavior is enabled.
        JWT_REFRESH_THRESHOLD_SECONDS: Seconds before expiry to trigger refresh when
            sliding refresh is enabled.
        ALLOWED_ORIGINS: List of allowed CORS origins; use explicit hosts in
            production when ``DEBUG`` is False.
        FALLBACK_ACTION: Behavior when configured fallback paths apply (model enum).
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", arbitrary_types_allowed=True
    )

    # Application
    APP_NAME: str = "Save Ma Money API"
    APP_VERSION: str = API_VERSION
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str | Type[SQLDatabaseConnector] | None = None
    LOG_LEVEL: (
        Literal["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | Annotated[int, Field(ge=0, le=50)]
    ) = "DEBUG"
    LOGGER_CONFIG_PATH: str | os.PathLike | None = None
    DATABASE_POOL_SIZE: Annotated[int, Field(ge=1, le=100)] = 10
    JWT_SECRET_KEY: Annotated[str, Field(min_length=1, max_length=512, pattern=r"^[A-Za-z0-9_-]+$")]
    JWT_TOKEN_TYPE: Literal["bearer", "refresh"] = "bearer"
    JWT_ALGORITHM: Annotated[str, Field(min_length=1, max_length=32)] = "HS256"
    JWT_EXPIRATION_TIME_SECONDS: Annotated[int, Field(ge=1)] = 3600
    JWT_SLIDING_REFRESH_ENABLED: bool = False
    JWT_REFRESH_THRESHOLD_SECONDS: Annotated[int, Field(ge=1)] = 600
    # Set explicit origins in production (e.g. via ALLOWED_ORIGINS env JSON or comma-separated).
    ALLOWED_ORIGINS: list[str] = Field(default_factory=list)
    FALLBACK_ACTION: FallbackAction = FallbackAction.LOG

    @field_validator("LOGGER_CONFIG_PATH", mode="before")
    @classmethod
    def validate_logger_config_path(cls, value: str | os.PathLike | None) -> str:
        """Resolve logger config path to an absolute, existing file.

        Args:
            value: User-provided path, or None to use the packaged default YAML.

        Returns:
            Absolute path string to the logger configuration file.

        Raises:
            FileNotFoundError: If the resolved path does not exist on disk.
        """
        value = value or DEFAULT_LOGGER_CONFIG_PATH
        value = Path(value)
        if not value.exists():
            raise FileNotFoundError(f"Logger configuration file not found at {value.absolute()}")

        return str(value.absolute())

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, value: str | Type[SQLDatabaseConnector] | None) -> Type[SQLDatabaseConnector]:
        """Normalize database configuration to a ``SQLDatabaseConnector`` type.

        Accepts an existing connector subclass, a non-empty connection string, or
        None. When None or empty, emits a warning and uses the default storage
        connector from ``SQLDatabaseConnector.establish``.

        Args:
            value: Connection string, connector class, or None.

        Returns:
            A ``SQLDatabaseConnector`` subclass configured for the given connection.

        Note:
            Emits ``UserWarning`` when falling back to the default connection.
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
        """Apply cross-field checks, configure loggers, and log startup.

        Warns when ``ALLOWED_ORIGINS`` contains ``'*'`` while ``DEBUG`` is False.
        Configures logging for both the model and API library names using
        ``LOGGER_CONFIG_PATH`` and ``LOG_LEVEL``.

        Returns:
            The same settings instance after side effects complete.

        Note:
            Emits ``UserWarning`` for permissive CORS in non-debug mode.
        """
        if "*" in self.ALLOWED_ORIGINS and not self.DEBUG:
            warnings.warn(
                "ALLOWED_ORIGINS contains '*' while DEBUG is False; set explicit origins for production.",
                stacklevel=2,
            )
        configure_logger(logger_name=MODEL_LIB_NAME, config=self.LOGGER_CONFIG_PATH, level=self.LOG_LEVEL)
        configure_logger(logger_name=API_LIB_NAME, config=self.LOGGER_CONFIG_PATH, level=self.LOG_LEVEL)
        logger.info("Application %s %s initialized", self.APP_NAME, self.APP_VERSION)
        return self


@lru_cache()
def get_settings() -> APISettings:
    """Return the process-wide ``APISettings`` instance.

    Cached with ``functools.lru_cache`` so repeated calls reuse the same object and
    validators run once.

    Returns:
        Constructed and validated ``APISettings``.
    """
    return APISettings()
