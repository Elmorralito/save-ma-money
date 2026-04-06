"""Base module for SQLModel definitions in the Papita Transactions system.

This module defines the base SQLModel class and schema configuration for the
Papita Transactions database. It provides a foundation for all database models
in the system with common fields like active status and deletion tracking.

Classes:
    BaseSQLModel: Base class for all SQL models in the Papita Transactions system.
"""

from datetime import datetime as builtin_datetime
from datetime import timezone
from typing import List, Self

import pandas as pd
from pydantic import field_validator, model_validator
from sqlalchemy import ARRAY, TIMESTAMP, String
from sqlmodel import Field, SQLModel, Table

from papita_txnsmodel.utils import datautils, modelutils

from .constants import SCHEMA_NAME

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
    deleted_at: builtin_datetime | None = Field(sa_type=TIMESTAMP, nullable=True, default=None)
    created_at: builtin_datetime = Field(
        sa_type=TIMESTAMP, nullable=False, default_factory=modelutils.current_timestamp
    )
    updated_at: builtin_datetime = Field(
        sa_type=TIMESTAMP, nullable=False, default_factory=modelutils.current_timestamp
    )

    @model_validator(mode="after")
    def _normalize_model(self) -> Self:
        """Normalize the model after initialization.

        This method normalizes the model by setting the created_at and updated_at fields to the current time in the
        UTC timezone if they are not set.

        It also validates the timestamps and sets the updated_at field to the created_at field if it is not set.
        It also validates the deleted_at field and sets the active field to False if it is not set.

        Returns:
            Self: The normalized model.
        """
        if self.created_at and self.created_at.tzinfo != timezone.utc:
            self.created_at = self.created_at.astimezone(timezone.utc)

        if self.updated_at and self.updated_at.tzinfo != timezone.utc:
            self.updated_at = self.updated_at.astimezone(timezone.utc)

        if self.deleted_at and self.deleted_at.tzinfo != timezone.utc:
            self.deleted_at = self.deleted_at.astimezone(timezone.utc)

        self.updated_at = max(self.created_at, self.updated_at)
        if self.deleted_at and not self.active:
            raise ValueError("The deleted_at timestamp must be after the created_at timestamp")

        if self.deleted_at and self.deleted_at < self.created_at:
            raise ValueError("The deleted_at timestamp must be after the created_at timestamp")

        if self.deleted_at and self.deleted_at < self.updated_at:
            raise ValueError("The deleted_at timestamp must be before the updated_at timestamp")

        return self

    @classmethod
    def get_table_name(cls) -> str:
        """Get the table name for the model.

        This method returns the table name for the model.

        Returns:
            str: The table name.
        """
        return cls.__tablename__

    @classmethod
    def get_table(cls) -> Table:
        """Get the table for the model.

        This method returns the table for the model.

        Returns:
            Table: The table.
        """
        return Table(cls.__tablename__, cls.__table_args__)

    @classmethod
    def standardized_dataframe(
        cls, df: pd.DataFrame, drops: list[str] | None = None, by_alias: bool = False, **kwargs
    ) -> pd.DataFrame:
        """Standardize a DataFrame to match the DTO's structure.

        Args:
            df: The DataFrame to standardize.
            drops: List of column names to drop from the DataFrame.
            by_alias: Whether to use field aliases when standardizing.
            **kwargs: Additional keyword arguments to pass to standardize_dataframe.

        Returns:
            pd.DataFrame: The standardized DataFrame.
        """
        return datautils.standardize_dataframe(cls, df, drops=drops, by_alias=by_alias, **kwargs)


class CoreTableSQLModel(BaseSQLModel, table=False):  # type: ignore
    """Base SQLModel class for all core database models in the Papita Transactions system.

    This class provides common fields and configuration for all core database models,
    including name, description, and tags. All model classes should inherit from this base class to ensure consistent
    behavior. It also validates the string fields and sets the tags field to the normalized tags.

    Attributes:
        name (str): The name of the record.
        description (str): The description of the record.
        tags (List[str]): The tags of the record.
    """

    name: str = Field(nullable=False, index=True, unique=True)
    description: str = Field(nullable=False, index=True, unique=True)
    tags: List[str] = Field(
        default_factory=list,
        sa_type=ARRAY(String),
        nullable=False,
        min_items=0,
        unique_items=True,
    )

    @field_validator("name", "description", mode="before")
    @classmethod
    def _validate_string_fields(cls, value: str) -> str:
        """Validate the string fields.

        This method validates the string fields by ensuring they are not empty.

        Args:
            value: The string to validate.

        Raises:
            ValueError: If the string field is empty.

        Returns:
            str: The validated string.
        """
        if not value.strip():
            raise ValueError("The string field must not be empty")

        return value.strip()

    @model_validator(mode="after")
    def _normalize_model(self) -> Self:
        """Normalize the model after initialization.

        This method normalizes the model by setting the tags field to the normalized tags.

        Returns:
            Self: The normalized model.
        """
        super()._normalize_model()
        if isinstance(self.tags, str):
            tag_sources = [self.tags]
        else:
            tag_sources = list(self.tags)

        tag_sources.append(self.name.lower())
        self.tags = list(modelutils.normalize_tags(tag_sources))
        return self
