"""Base DTO module for the Papita Transactions system.

This module defines the base Data Transfer Object (DTO) classes used throughout the system.
It provides the foundation for all DTOs with common functionality for data validation,
conversion between DTOs and database models, and standardization of data formats.

Classes:
    TableDTO: Base class for all table DTOs with common fields and functionality.
    CoreTableDTO: Extended base class with additional common fields for core entities.
"""

import uuid
from datetime import datetime
from typing import List

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator

from papita_txnsmodel.model.base import BaseSQLModel
from papita_txnsmodel.utils import datautils


class TableDTO(BaseModel):
    """Base class for all table DTOs in the Papita Transactions system.

    This class provides common fields and functionality for all DTOs that represent
    database tables. It includes methods for converting between DTOs and database
    models, as well as standardizing DataFrame representations of the data.

    Attributes:
        __dao_type__ (type): The SQLModel class this DTO corresponds to.
        id (uuid.UUID | None): Unique identifier for the record. Defaults to a new UUID.
        active (bool): Whether the record is active. Defaults to True.
        deleted_at (datetime | None): Timestamp when the record was soft-deleted.
            Defaults to None, indicating the record is not deleted.
    """

    __dao_type__ = BaseSQLModel
    model_config = ConfigDict(ignored_types=(pd.Timestamp,), arbitrary_types_allowed=True)

    id: uuid.UUID | None = Field(default_factory=uuid.uuid4)
    active: bool = True
    deleted_at: datetime | None = None

    @classmethod
    def from_dao(cls, obj: BaseSQLModel) -> "TableDTO":
        """Convert a database model instance to a DTO instance.

        Args:
            obj: The database model instance to convert.

        Returns:
            TableDTO: The converted DTO instance.

        Raises:
            TypeError: If the provided object is not of the expected database model type.
        """
        if not isinstance(obj, cls.__dao_type__):
            raise TypeError(f"Unsupported DAO type: {type(obj)}")

        return cls.model_validate(obj, strict=True)

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

    def to_dao(self) -> BaseSQLModel:
        """Convert this DTO instance to a database model instance.

        Returns:
            BaseSQLModel: The converted database model instance.
        """
        return self.__dao_type__.model_validate(**self.model_dump(mode="python", exclude_unset=True, exclude_none=True))


class CoreTableDTO(TableDTO):
    """Extended base class for core entity DTOs with additional common fields.

    This class extends TableDTO with additional fields and validation rules that
    are common to core entities in the system, such as name, description, and tags.

    Attributes:
        name (str): Name of the entity.
        description (str): Description of the entity.
        active (bool): Whether the entity is active. Defaults to True.
        tags (List[str]): List of tags associated with the entity.
    """

    name: str
    description: str
    active: bool = True
    tags: List[str]

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, value: str) -> str:
        """Validate that the name is not empty.

        Args:
            value: The name value to validate.
        Returns:
            str: The validated name.

        Raises:
            ValueError: If the name is empty or contains only whitespace.
        """
        if not value or value.isspace():
            raise ValueError("name cannot be empty")
        return value

    @field_validator("description")
    @classmethod
    def description_must_not_be_empty(cls, value: str) -> str:
        """Validate that the description is not empty.

        Args:
            value: The description value to validate.

        Returns:
            str: The validated description.

        Raises:
            ValueError: If the description is empty or contains only whitespace.
        """
        if not value or value.isspace():
            raise ValueError("description cannot be empty")
        return value

    @field_validator("tags")
    @classmethod
    def tags_must_have_at_least_one_item(cls, value: List[str]) -> List[str]:
        """Validate that the tags list has at least one item and contains unique items.

        Args:
            value: The tags list to validate.

        Returns:
            List[str]: The validated tags list.

        Raises:
            ValueError: If the tags list is empty or contains duplicate items.
        """
        if not value or len(value) < 1:
            raise ValueError("tags must have at least one item")

        # Check for unique items
        if len(value) != len(set(value)):
            raise ValueError("tags must contain unique items")

        return value
