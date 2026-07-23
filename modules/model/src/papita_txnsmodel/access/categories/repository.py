"""Categories repository module for the Papita Transactions system.

This module defines the repository class for category entities in the system.
It provides database access operations specific to categories, including global
and owner-scoped record retrieval.

Classes:
    CategoriesRepository: Repository for category entity database operations.
"""

from typing import Type

import pandas as pd
from sqlalchemy import or_
from sqlmodel import Session

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.access.base.repository import BaseRepository
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.classutils import MetaSingleton

from .dto import CategoriesDTO


class CategoriesRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for category entity database operations.

    This class extends BaseRepository to provide operations specific to categories.
    When an owner is provided, queries include both that user's categories and
    global categories (owner_id IS NULL).

    Attributes:
        __expected_dto_type__ (type[CategoriesDTO]): The expected DTO type for this
            repository, set to CategoriesDTO.
    """

    __expected_dto__ = CategoriesDTO

    def get_records(
        self, *query_filters, owner: UsersDTO | None = None, dto_type: Type[TableDTO] = CategoriesDTO, **kwargs
    ) -> pd.DataFrame:
        """Retrieve records from the database based on query filters.

        Overrides the base method to include global records (where owner_id is null)
        when an owner is provided.

        Args:
            *query_filters: Variable length list of query filter conditions.
            owner: The owner of the records to retrieve. If provided, includes
                records owned by this user AND global records.
            dto_type: The DTO type for the records to retrieve. Defaults to CategoriesDTO.
            **kwargs: Additional keyword arguments to pass to run_query.

        Returns:
            pd.DataFrame: DataFrame containing the retrieved records.
        """
        if owner:
            owner_filter = [or_(dto_type.__dao_type__.owner_id == owner.id, dto_type.__dao_type__.owner_id.is_(None))]
            return super().get_records(*owner_filter, *query_filters, dto_type=dto_type, **kwargs)

        return super().get_records(*query_filters, dto_type=dto_type, **kwargs)

    def count_records(
        self, *query_filters, owner: UsersDTO | None = None, dto_type: Type[TableDTO] = CategoriesDTO, **kwargs
    ) -> int:
        """Count category rows with the same owner+global visibility as ``get_records``."""
        if owner:
            owner_filter = or_(dto_type.__dao_type__.owner_id == owner.id, dto_type.__dao_type__.owner_id.is_(None))
            return super().count_records(owner_filter, *query_filters, dto_type=dto_type, **kwargs)
        return super().count_records(*query_filters, dto_type=dto_type, **kwargs)

    @SQLDatabaseConnector.connect
    def upsert_record(self, dto: CategoriesDTO, *, _db_session: Session, **kwargs) -> CategoriesDTO | None:
        """Upsert a category row with optional owner scoping for tenant-owned rows."""
        owner = kwargs.pop("owner", None)
        if isinstance(owner, UsersDTO):
            if dto.owner_id is not None and dto.owner_id != owner.id:
                raise ValueError("DTO owner_id does not match the provided owner.")
            if dto.owner_id is None and kwargs.get("assign_owner", True):
                dto.owner_id = owner.id

        return super().upsert_record(dto, _db_session=_db_session, **kwargs)
