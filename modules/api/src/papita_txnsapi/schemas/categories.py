"""Category request/response schemas for PPT-036."""

from __future__ import annotations

import uuid
from datetime import datetime

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from papita_txnsapi.schemas.converters import enum_to_api_slug, parse_category_kind
from papita_txnsmodel.access.categories.dto import CategoriesDTO


class CategorySubcategoryResponse(BaseModel):
    """Nested subcategory summary on list responses."""

    id: uuid.UUID
    name: str
    category_type: str


class CategoryCreate(BaseModel):
    """Request body for ``POST /categories``."""

    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    category_type: str
    parent_id: uuid.UUID | None = None
    icon: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=7)

    def to_categories_dto(self) -> CategoriesDTO:
        """Build a ``CategoriesDTO`` for the model service layer."""
        return CategoriesDTO(
            name=self.name.strip(),
            description=self.description,
            category_kind=parse_category_kind(self.category_type),
            parent_id=self.parent_id,
            icon=self.icon,
            color=self.color,
        )


class CategoryUpdate(BaseModel):
    """Request body for ``PUT /categories/{category_id}``."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category_type: str | None = None
    parent_id: uuid.UUID | None = None
    icon: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=7)
    is_active: bool | None = None

    def apply_to(self, existing: CategoriesDTO) -> CategoriesDTO:
        """Merge partial update fields onto an existing category DTO."""
        updates = self.model_dump(exclude_unset=True, exclude={"category_type", "is_active"})
        if self.category_type is not None:
            updates["category_kind"] = parse_category_kind(self.category_type)
        if self.is_active is not None:
            updates["active"] = self.is_active
        return existing.model_copy(update=updates)


class CategoryResponse(BaseModel):
    """Category resource returned by CRUD endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category_type: str
    parent_id: uuid.UUID | None = None
    icon: str | None = None
    color: str | None = None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    subcategories: list[CategorySubcategoryResponse] = Field(default_factory=list)

    @classmethod
    def from_dto(
        cls,
        category: CategoriesDTO,
        *,
        subcategories: list[CategorySubcategoryResponse] | None = None,
    ) -> CategoryResponse:
        """Build an API response from a ``CategoriesDTO``."""
        return cls(
            id=category.id,
            name=category.name,
            category_type=enum_to_api_slug(category.category_kind),
            parent_id=category.parent_id if isinstance(category.parent_id, uuid.UUID) else None,
            icon=category.icon,
            color=category.color,
            is_active=bool(category.active),
            created_at=category.created_at,
            updated_at=category.updated_at,
            subcategories=subcategories or [],
        )


def categories_from_dataframe(df: pd.DataFrame) -> list[CategoriesDTO]:
    """Convert a categories query DataFrame to DTO instances."""
    if getattr(df, "empty", True):
        return []
    dao_type = CategoriesDTO.__dao_type__
    categories: list[CategoriesDTO] = []
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        if "Categories" in row_dict and isinstance(row_dict["Categories"], dao_type):
            categories.append(CategoriesDTO.from_dao(row_dict["Categories"]))
            continue
        if len(row_dict) == 1:
            only_value = next(iter(row_dict.values()))
            if isinstance(only_value, dao_type):
                categories.append(CategoriesDTO.from_dao(only_value))
                continue
        categories.append(CategoriesDTO.model_validate(row_dict))
    return categories


def paginate_dataframe(df: pd.DataFrame, skip: int, limit: int) -> tuple[pd.DataFrame, int]:
    """Slice a DataFrame for skip/limit pagination."""
    total = len(df)
    if total == 0:
        return df, 0
    return df.iloc[skip : skip + limit], total


def build_subcategory_map(categories: list[CategoriesDTO]) -> dict[uuid.UUID, list[CategorySubcategoryResponse]]:
    """Group direct children by parent category id."""
    children: dict[uuid.UUID, list[CategorySubcategoryResponse]] = {}
    for category in categories:
        parent_id = category.parent_id
        if parent_id is None or not isinstance(parent_id, uuid.UUID):
            continue
        children.setdefault(parent_id, []).append(
            CategorySubcategoryResponse(
                id=category.id,
                name=category.name,
                category_type=enum_to_api_slug(category.category_kind),
            )
        )
    return children
