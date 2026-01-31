"""Types repository module for the Papita Transactions system.

This module defines repository classes for type entities in the system.
It provides database access operations specific to types, extending the base
repository functionality with type-specific implementations.

Classes:
    TypesRepository: Repository for general type entity database operations.
    TypesClassificationRepository: Repository for type classification operations.
"""

from typing import TYPE_CHECKING, Optional, Type

import pandas as pd
from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.access.base.repository import BaseRepository
from papita_txnsmodel.utils.classutils import MetaSingleton
from sqlalchemy import or_

from .dto import TypesDTO

if TYPE_CHECKING:
    from papita_txnsmodel.access.users.dto import UsersDTO


class TypesRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for type entity database operations.

    This class extends the BaseRepository to provide operations specific to type
    entities, which categorize different financial objects in the system such as
    assets, liabilities, and transactions. It uses the Singleton pattern via
    MetaSingleton to ensure only one instance exists throughout the application.

    The repository works with TypesDTO objects and provides all the CRUD operations
    inherited from BaseRepository, including querying, inserting, updating, and
    deleting type records.

    Attributes:
        __expected_dto_type__ (type[TypesDTO]): The expected DTO type for this
            repository, set to TypesDTO.
    """

    __expected_dto_type__ = TypesDTO

    def get_records(
        self, *query_filters, owner: Optional["UsersDTO"] = None, dto_type: Type[TableDTO] = TypesDTO, **kwargs
    ) -> pd.DataFrame:
        """Retrieve records from the database based on query filters.

        Overrides the base method to include global records (where owner_id is null)
        when an owner is provided.

        Args:
            *query_filters: Variable length list of query filter conditions.
            owner: The owner of the records to retrieve. If provided, includes
                records owned by this user AND global records.
            dto_type: The DTO type for the records to retrieve. Defaults to TypesDTO.
            **kwargs: Additional keyword arguments to pass to run_query.

        Returns:
            pd.DataFrame: DataFrame containing the retrieved records.
        """
        if owner:
            owner_filter = or_(dto_type.__dao_type__.owner_id == owner.id, dto_type.__dao_type__.owner_id == None)
            return super().get_records(owner_filter, *query_filters, dto_type=dto_type, **kwargs)

        return super().get_records(*query_filters, dto_type=dto_type, **kwargs)
