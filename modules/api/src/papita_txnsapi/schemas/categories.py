"""Category request/response schemas for PPT-036 categories CRUD.

Maps REST category payloads to ``CategoriesDTO`` from ``papita_txnsmodel`` and
builds nested subcategory summaries for list responses. Helpers mirror the
account schemas for DataFrame pagination and repository-row conversion.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from papita_txnsapi.schemas.converters import enum_to_api_slug, parse_category_kind
from papita_txnsmodel.access.categories.dto import CategoriesDTO


class CategorySubcategoryResponse(BaseModel):
    """Nested subcategory summary on list responses.

    Attributes:
        id: Child category UUID.
        name: Child display name.
        category_type: Lowercase API slug for the child's ``CategoryKind``.
    """

    id: uuid.UUID
    name: str
    category_type: str


class CategoryCreate(BaseModel):
    """Request body for ``POST /categories``.

    Attributes:
        name: Display name; 1–255 characters after trimming.
        description: Optional free-text description.
        category_type: Lowercase slug parsed to ``CategoryKind``.
        parent_id: Optional parent category for hierarchical trees.
        icon: Optional icon key or identifier (max 64 chars).
        color: Optional hex color (max 7 chars, e.g. ``#FF00AA``).
    """

    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    category_type: str
    parent_id: uuid.UUID | None = None
    icon: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=7)

    def to_categories_dto(self) -> CategoriesDTO:
        """Build a ``CategoriesDTO`` for the model service layer.

        Returns:
            DTO ready for ``CategoriesService`` create/upsert; name is trimmed and
            ``category_type`` is parsed to ``category_kind``.

        Raises:
            ValueError: When ``category_type`` is not a valid slug.
        """
        return CategoriesDTO(
            name=self.name.strip(),
            description=self.description,
            category_kind=parse_category_kind(self.category_type),
            parent_id=self.parent_id,
            icon=self.icon,
            color=self.color,
        )


class CategoryUpdate(BaseModel):
    """Request body for ``PUT /categories/{category_id}``.

    All fields are optional; only set fields are merged onto the existing DTO.

    Attributes:
        name: New display name; 1–255 characters when provided.
        description: Replacement description text.
        category_type: New kind slug; maps to DTO ``category_kind``.
        parent_id: New parent reference or ``None`` to clear hierarchy.
        icon: Updated icon key (max 64 chars).
        color: Updated hex color (max 7 chars).
        is_active: Soft-active flag; maps to DTO ``active``.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category_type: str | None = None
    parent_id: uuid.UUID | None = None
    icon: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=7)
    is_active: bool | None = None

    def apply_to(self, existing: CategoriesDTO) -> CategoriesDTO:
        """Merge partial update fields onto an existing category DTO.

        Args:
            existing: Current category row from the repository.

        Returns:
            New ``CategoriesDTO`` with only supplied fields overwritten;
            ``category_type`` becomes ``category_kind`` and ``is_active`` becomes
            ``active``.

        Raises:
            ValueError: When a provided ``category_type`` slug is invalid.
        """
        updates = self.model_dump(exclude_unset=True, exclude={"category_type", "is_active"})
        if self.category_type is not None:
            updates["category_kind"] = parse_category_kind(self.category_type)
        if self.is_active is not None:
            updates["active"] = self.is_active
        return existing.model_copy(update=updates)


class CategoryResponse(BaseModel):
    """Category resource returned by CRUD endpoints.

    Attributes:
        id: Category UUID.
        name: Display name.
        category_type: Lowercase API slug for ``CategoryKind``.
        parent_id: Parent category UUID when nested; otherwise ``None``.
        icon: Optional icon key.
        color: Optional hex color.
        is_active: Whether the category is soft-active.
        created_at: Row creation timestamp.
        updated_at: Last modification timestamp.
        subcategories: Direct child summaries for list enrichment.
    """

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
        """Build an API response from a ``CategoriesDTO``.

        Args:
            category: Core category row from the repository.
            subcategories: Optional pre-built child summaries; defaults to empty list.

        Returns:
            Serialized category with ``category_type`` slug and nested children.
        """
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
    """Convert a categories query DataFrame to DTO instances.

    Handles repository row shapes: nested ``Categories`` DAO column, single DAO
    column, or flat dict rows validated by Pydantic.

    Args:
        df: DataFrame from ``CategoryRepository`` query methods.

    Returns:
        List of ``CategoriesDTO`` instances; empty list when the frame is empty.
    """
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
    """Slice a DataFrame for skip/limit pagination.

    Args:
        df: Full result set before pagination.
        skip: Number of leading rows to omit.
        limit: Maximum rows to include in the page.

    Returns:
        Tuple of (page slice, total row count). When empty, returns the original
        frame and total ``0``.
    """
    total = len(df)
    if total == 0:
        return df, 0
    return df.iloc[skip : skip + limit], total


def build_subcategory_map(categories: list[CategoriesDTO]) -> dict[uuid.UUID, list[CategorySubcategoryResponse]]:
    """Group direct children by parent category id.

    Args:
        categories: Flat list of category DTOs (typically an entire tenant tree).

    Returns:
        Mapping from parent UUID to child summary objects. Categories without a
        UUID ``parent_id`` are omitted from the map values.
    """
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
