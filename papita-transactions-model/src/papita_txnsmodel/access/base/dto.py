import uuid
from datetime import datetime
from typing import List

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlmodel import SQLModel

from papita_txnsmodel.utils import datautils


class TableDTO(BaseModel):
    __dao_type__ = SQLModel
    model_config = ConfigDict(ignored_types=(pd.Timestamp,), arbitrary_types_allowed=True)

    id: uuid.UUID | None = Field(default_factory=uuid.uuid4)
    active: bool = True
    deleted_at: datetime | None = None

    @classmethod
    def from_dao(cls, obj: SQLModel) -> "TableDTO":
        if not isinstance(obj, cls.__dao_type__):
            raise TypeError(f"Unsupported DAO type: {type(obj)}")

        return cls.model_validate(obj, strict=True)

    @classmethod
    def standardized_dataframe(
        cls, df: pd.DataFrame, drops: list[str] | None = None, by_alias: bool = False, **kwargs
    ) -> pd.DataFrame:
        return datautils.standardize_dataframe(cls, df, drops=drops, by_alias=by_alias, **kwargs)

    def to_dao(self) -> SQLModel:
        return self.__dao_type__.model_validate(**self.model_dump(mode="python", exclude_unset=True, exclude_none=True))


class CoreTableDTO(TableDTO):

    name: str
    description: str
    active: bool = True
    tags: List[str]

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, value: str) -> str:
        if not value or value.isspace():
            raise ValueError("name cannot be empty")
        return value

    @field_validator("description")
    @classmethod
    def description_must_not_be_empty(cls, value: str) -> str:
        if not value or value.isspace():
            raise ValueError("description cannot be empty")
        return value

    @field_validator("tags")
    @classmethod
    def tags_must_have_at_least_one_item(cls, value: List[str]) -> List[str]:
        if not value or len(value) < 1:
            raise ValueError("tags must have at least one item")

        # Check for unique items
        if len(value) != len(set(value)):
            raise ValueError("tags must contain unique items")

        return value
