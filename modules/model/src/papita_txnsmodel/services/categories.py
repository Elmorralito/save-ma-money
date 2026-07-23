"""Categories service module for the Papita Transactions system.

This module provides services for managing category entities in the system. Categories
replace the legacy Types taxonomy and classify income/expense transactions.

Classes:
    CategoriesService: Service for managing category entities in the system.
"""

import logging
import uuid
from collections.abc import Sequence
from typing import Annotated, Any

import pandas as pd
from pydantic import Field

from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.categories.repository import CategoriesRepository
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.model.categories import Categories
from papita_txnsmodel.model.enums import CategoryKind
from papita_txnsmodel.utils.datautils import standardize_dataframe

from .base import BaseService

logger = logging.getLogger(__name__)

_CATEGORY_NOT_FOUND = object()


class CategoriesService(BaseService):
    """Service for managing category entities in the Papita Transactions system.

    Categories may be global or user-owned and are used to classify transaction
    templates and posted transactions. All service operations require ``owner=``
    so reads stay tenant-scoped (owner + global) and tenants cannot mutate global
    seed rows via create/update/delete.

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

    def _requires_owner(self) -> bool:
        """Categories are hybrid global+tenant; service ops always need a tenant owner."""
        return True

    def _category_list_filters(
        self,
        *,
        parent_id: uuid.UUID | None,
        roots_only: bool,
        category_kind: CategoryKind | None,
    ) -> list:
        """Build SQL filters for paginated category lists."""
        filters: list = []
        if roots_only:
            filters.append(Categories.parent_id.is_(None))
        elif parent_id is not None:
            filters.append(Categories.parent_id == parent_id)
        if category_kind is not None:
            filters.append(Categories.category_kind == category_kind)
        return filters

    def list_categories(
        self,
        *,
        owner: UsersDTO,
        parent_id: uuid.UUID | None = None,
        roots_only: bool = False,
        category_kind: CategoryKind | None = None,
        skip: int = 0,
        limit: int = 100,
        **kwargs,
    ) -> tuple[pd.DataFrame, int]:
        """Return a SQL-paginated category page and matching total count.

        Args:
            owner: Tenant used for owner+global visibility.
            parent_id: When set (and ``roots_only`` is false), only direct children.
            roots_only: When true, only top-level rows (``parent_id IS NULL``).
            category_kind: Optional income/expense filter.
            skip: Offset for SQL pagination.
            limit: Page size for SQL pagination.
            **kwargs: Extra repository kwargs.

        Returns:
            Tuple of (standardized page DataFrame, total matching rows).
        """
        ensured_owner = self._ensure_owner(owner)
        filters = self._category_list_filters(
            parent_id=parent_id,
            roots_only=roots_only,
            category_kind=category_kind,
        )
        total = int(self._repository.count_records(*filters, owner=ensured_owner, dto_type=self.dto_type, **kwargs))
        records_df = self._repository.get_records(
            *filters,
            owner=ensured_owner,
            dto_type=self.dto_type,
            skip=skip,
            limit=limit,
            **kwargs,
        )
        return standardize_dataframe(self.dto_type, records_df, **kwargs), total

    def get_categories_for_parents(
        self,
        *,
        owner: UsersDTO,
        parent_ids: Sequence[uuid.UUID],
        category_kind: CategoryKind | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Load direct children for the given parent ids (for nested list responses)."""
        if not parent_ids:
            return pd.DataFrame([])
        ensured_owner = self._ensure_owner(owner)
        filters: list = [Categories.parent_id.in_(list(parent_ids))]
        if category_kind is not None:
            filters.append(Categories.category_kind == category_kind)
        records_df = self._repository.get_records(
            *filters,
            owner=ensured_owner,
            dto_type=self.dto_type,
            **kwargs,
        )
        return standardize_dataframe(self.dto_type, records_df, **kwargs)

    def _existing_category_owner_id(self, category_id: uuid.UUID, owner: UsersDTO) -> uuid.UUID | None | object:
        """Return owner_id for a visible category row, or ``_MISSING`` when not found."""
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

    def _reject_global_category_write(self, *, dto: CategoriesDTO, owner: UsersDTO) -> None:
        """Block tenant mutations against global (``owner_id IS NULL``) categories.

        New tenant rows may omit ``owner_id``; ``CategoriesRepository.upsert_record``
        assigns the authenticated owner. Existing global rows (``owner_id IS NULL``)
        are never updatable or deletable through this service.
        """
        if dto.id is None:
            return
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
        ensured_owner = self._ensure_owner(owner)
        if ensured_owner is None:
            raise ValueError("CategoriesDTO requires owner=UsersDTO for tenant-scoped operations.")
        parsed = self.parse_dto(obj)
        self._reject_global_category_write(dto=parsed, owner=ensured_owner)
        return super().create(obj=parsed, owner=ensured_owner, **kwargs)

    def delete(
        self,
        *,
        obj: CategoriesDTO | dict[str, Any],
        owner: UsersDTO | None = None,
        hard: bool = False,
        **kwargs,
    ) -> pd.DataFrame:
        """Soft/hard delete a tenant category; refuse global seed rows."""
        ensured_owner = self._ensure_owner(owner)
        if ensured_owner is None:
            raise ValueError("CategoriesDTO requires owner=UsersDTO for tenant-scoped operations.")
        parsed = self.parse_dto(obj)
        self.check_expected_dto_type(parsed)
        self._reject_global_category_write(dto=parsed, owner=ensured_owner)
        return super().delete(obj=parsed, owner=ensured_owner, hard=hard, **kwargs)
