# type: ignore

import contextlib
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

logger = logging.getLogger(API_LIB_NAME)


class Settings(BaseSettings):

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

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, value: str | Type[SQLDatabaseConnector] | None) -> Type[SQLDatabaseConnector]:
        with contextlib.suppress(ValueError):
            if issubclass(value, SQLDatabaseConnector):
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
        configure_logger(logger_name=MODEL_LIB_NAME, config=Path(self.LOG_FILE), level=self.LOG_LEVEL)
        configure_logger(logger_name=API_LIB_NAME, config=Path(self.LOG_FILE), level=self.LOG_LEVEL)
        logger.info("Application %s %s initialized", self.APP_NAME, self.APP_VERSION)
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
