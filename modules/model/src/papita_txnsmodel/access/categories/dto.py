"""Categories DTO module for the Papita Transactions system.

This module defines Data Transfer Objects (DTOs) for category entities in the system.
Categories replace the legacy Types taxonomy and classify income/expense transactions.

Classes:
    CategoriesDTO: DTO for category entities with optional hierarchy and ownership.
"""

from __future__ import annotations

import uuid

from pydantic import ConfigDict, Field, field_serializer

from papita_txnsmodel.access.base.dto import CoreTableDTO, TableDTO
from papita_txnsmodel.model.categories import Categories
from papita_txnsmodel.model.enums import CategoryKind


class CategoriesDTO(CoreTableDTO):
    """DTO for category entities in the Papita Transactions system.

    Categories may be global (owner_id is null) or owned by a user. They support
    optional parent/child hierarchy and visual metadata (icon, color).

    Attributes:
        model_config (ConfigDict): Configuration allowing extra fields beyond those defined.
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        category_kind (CategoryKind): Income vs expense taxonomy discriminator.
        owner_id (uuid.UUID | None): Optional owner; null indicates a global category.
        parent_id (uuid.UUID | CategoriesDTO | None): Optional parent category reference.
        icon (str | None): Optional icon identifier.
        color (str | None): Optional hex color code.
    """

    model_config = ConfigDict(extra="allow")
    __dao_type__ = Categories

    category_kind: CategoryKind
    owner_id: uuid.UUID | None = None
    parent_id: uuid.UUID | CategoriesDTO | None = Field(default=None, serialization_alias="parent_id")
    icon: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=7)

    @field_serializer("parent_id")
    def _serialize_parent_id(self, value: uuid.UUID | TableDTO | None) -> uuid.UUID | None:
        """Serialize parent_id to its UUID value.

        Args:
            value: Parent category as UUID, DTO, or None.

        Returns:
            uuid.UUID | None: The parent category UUID, or None.
        """
        if value is None:
            return None

        return value.id if isinstance(value, TableDTO) else value
