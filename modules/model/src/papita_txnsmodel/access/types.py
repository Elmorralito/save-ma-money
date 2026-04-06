"""Types repository module for the Papita Transactions system.

This module defines repository classes for type entities in the system.
It provides database access operations specific to types, extending the base
repository functionality with type-specific implementations.

Classes:
    TypesRepository: Repository for general type entity database operations.
    TypesClassificationRepository: Repository for type classification operations.
"""

from typing import Type

import pandas as pd
from sqlalchemy import or_

from papita_txnsmodel.model.base import BaseSQLModel
from papita_txnsmodel.model.types import Types
from papita_txnsmodel.model.users import Users
from papita_txnsmodel.utils.classutils import MetaSingleton

from .base import BaseRepository


class TypesRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for type entity database operations.

    This class extends the BaseRepository to provide operations specific to type
    entities, which categorize different financial objects in the system such as
    assets, liabilities, and transactions. It uses the Singleton pattern via
    MetaSingleton to ensure only one instance exists throughout the application.

    The repository works with Types objects and provides all the CRUD operations
    inherited from BaseRepository, including querying, inserting, updating, and
    deleting type records.

    Attributes:
        __expected_dao_type__ (type[Types]): The expected DAO type for this
            repository, set to Types.
    """

    __expected_dao_type__ = Types

    def get_records(
        self, *query_filters, owner: Users | None = None, dao_type: Type[BaseSQLModel] = Types, **kwargs
    ) -> pd.DataFrame:
        """Retrieve records from the database based on query filters.

        Overrides the base method to include global records (where owner_id is null)
        when an owner is provided.

        Args:
            *query_filters: Variable length list of query filter conditions.
            owner: The owner of the records to retrieve. If provided, includes
                records owned by this user AND global records.
            dao_type: The DAO type for the records to retrieve. Defaults to Types.
            **kwargs: Additional keyword arguments to pass to run_query.

        Returns:
            pd.DataFrame: DataFrame containing the retrieved records.
        """
        if owner:
            owner_filter = [or_(dao_type.owner_id == owner.id, dao_type.owner_id is None)]  # noqa: E711
            return super().get_records(*owner_filter, *query_filters, dao_type=dao_type, **kwargs)

        return super().get_records(*query_filters, dao_type=dao_type, **kwargs)
