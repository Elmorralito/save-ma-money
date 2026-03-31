# type: ignore

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
        value = value or DEFAULT_LOGGER_CONFIG_PATH
        value = Path(value)
        if not value.exists():
            raise FileNotFoundError(f"Logger configuration file not found at {value.absolute()}")

        return str(value.absolute())

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, value: str | Type[SQLDatabaseConnector] | None) -> Type[SQLDatabaseConnector]:
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
    return APISettings()
