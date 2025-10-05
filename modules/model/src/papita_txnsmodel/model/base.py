"""Base module for SQLModel definitions in the Papita Transactions system.

This module defines the base SQLModel class and schema configuration for the
Papita Transactions database. It provides a foundation for all database models
in the system with common fields like active status and deletion tracking.

Classes:
    BaseSQLModel: Base class for all SQL models in the Papita Transactions system.
"""

from datetime import datetime as base_datetime

from sqlalchemy import TIMESTAMP
from sqlmodel import Field, SQLModel

SCHEMA_NAME = "papita_transactions"
SQLModel.metadata.schema = SCHEMA_NAME


class BaseSQLModel(SQLModel, table=False):  # type: ignore
    """Base SQLModel class for all database models in the Papita Transactions system.

    This class provides common fields and configuration for all database models,
    including soft deletion support and schema configuration. All model classes
    should inherit from this base class to ensure consistent behavior.

    Attributes:
        __table_args__: Dictionary containing SQLAlchemy table arguments,
            specifically setting the database schema.
        active (bool): Flag indicating if the record is active. Defaults to True.
        deleted_at (datetime | None): Timestamp when the record was soft-deleted.
            Null value indicates the record is not deleted.
    """

    __table_args__ = {"schema": SCHEMA_NAME}

    active: bool = Field(nullable=False, default=True)
    deleted_at: base_datetime | None = Field(sa_type=TIMESTAMP, nullable=True, default=None)
