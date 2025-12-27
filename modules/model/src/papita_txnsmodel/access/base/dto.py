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
from typing import Annotated, List, Self

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, WrapValidator, model_validator

from papita_txnsmodel.model.base import BaseSQLModel
from papita_txnsmodel.utils import datautils, modelutils


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
    model_config = ConfigDict(ignored_types=(pd.Timestamp,), arbitrary_types_allowed=True, extra="allow")

    id: uuid.UUID | None = Field(default_factory=uuid.uuid4)
    active: Annotated[bool | str | int, WrapValidator(modelutils.validate_bool)] = True
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

        data = {
            field.alias if field.alias else field_name: getattr(
                obj, field_name, getattr(obj, field.alias, None) if field.alias else None
            )
            for field_name, field in cls.model_fields.items()
            if field_name in obj.model_fields_set or field.alias in obj.model_fields_set
        }
        return cls.model_validate(data)

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
        return self.__dao_type__.model_validate(self.model_dump(mode="python", exclude_unset=True, exclude_none=True))


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

    name: Annotated[str, Field(min_length=3)]
    description: Annotated[str, Field(min_length=3)]
    tags: Annotated[List[str], Field(min_length=1)] | Annotated[str, Field(min_length=3)]

    @model_validator(mode="after")
    def _normalize_model(self) -> Self:
        """Normalize and validate entity fields after model initialization.

        This validator strips whitespace from the name and description, and
        normalizes the tags by combining them with the lowercase name and
        optional classification value.

        Returns:
            Self: The normalized entity DTO instance.
        """
        self.name = self.name.strip()
        self.description = self.description.strip()
        if isinstance(self.tags, str):
            tag_sources = [self.tags]
        else:
            tag_sources = list(self.tags)

        tag_sources.append(self.name.lower())
        if hasattr(self, "classification") and hasattr(self.classification, "value"):
            tag_sources.append(self.classification.value.lower())

        self.tags = list(modelutils.normalize_tags(tag_sources))
        return self
