"""Categories service module for the Papita Transactions system.

This module provides services for managing category entities in the system. Categories
replace the legacy Types taxonomy and classify income/expense transactions.

Classes:
    CategoriesService: Service for managing category entities in the system.
"""

import logging
import uuid
from typing import Annotated, Any

from pydantic import Field

from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.categories.repository import CategoriesRepository
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.upsert import OnUpsertConflictDo

from .base import BaseService

logger = logging.getLogger(__name__)

_CATEGORY_NOT_FOUND = object()


class CategoriesService(BaseService):
    """Service for managing category entities in the Papita Transactions system.

    Categories may be global or user-owned and are used to classify transaction
    templates and posted transactions.

    Attributes:
        dto_type (type[CategoriesDTO]): Data Transfer Object type for categories.
        repository_type (type[CategoriesRepository]): Repository class for category
            database operations.
        missing_upsertions_tol (float): Tolerance threshold for missing upsertions.
        on_conflict_do (OnUpsertConflictDo | str): Action to take on upsert conflicts.
    """

    dto_type: type[CategoriesDTO] = CategoriesDTO
    repository_type: type[CategoriesRepository] = CategoriesRepository

    missing_upsertions_tol: Annotated[float, Field(ge=0, le=0.5)] = 0.0
    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE

    def _existing_category_owner_id(self, category_id: uuid.UUID, owner: UsersDTO) -> uuid.UUID | None | object:
        """Return owner_id for a visible category row, or ``_MISSING`` when not found."""
        from papita_txnsmodel.model.categories import Categories

        records = self._repository.get_records(
            Categories.id == category_id,
            owner=owner,
            dto_type=self.dto_type,
        )
        if getattr(records, "empty", True):
            return _CATEGORY_NOT_FOUND

        row = records.iloc[0]
        if "owner_id" in records.columns:
            return row.get("owner_id")
        category_row = row.get("Categories")
        return getattr(category_row, "owner_id", None)

    def _reject_global_category_write(self, *, dto: CategoriesDTO, owner: UsersDTO | None) -> None:
        """Block tenant mutations against global (``owner_id IS NULL``) categories."""
        if owner is None:
            return
        if dto.owner_id is None:
            raise ValueError("Tenants cannot create or modify global categories.")
        if dto.id is not None:
            existing_owner_id = self._existing_category_owner_id(dto.id, owner)
            if existing_owner_id is _CATEGORY_NOT_FOUND:
                return
            if existing_owner_id is None:
                raise ValueError("Tenants cannot modify global categories.")

    def create(
        self,
        *,
        obj: CategoriesDTO | dict[str, Any],
        owner: UsersDTO | None = None,
        **kwargs,
    ) -> CategoriesDTO:
        """Create or update a category while protecting global seed rows."""
        parsed = self.parse_dto(obj)
        self._reject_global_category_write(dto=parsed, owner=owner)
        return super().create(obj=parsed, owner=owner, **kwargs)
