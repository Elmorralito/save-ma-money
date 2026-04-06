"""Accounts indexer repository module for the Papita Transactions system.

This module defines the repository class for account indexer entities in the system.
It provides database access operations specific to account indexers, extending the base
repository functionality with indexer-specific implementations.

Classes:
    AccountsIndexerRepository: Repository for account indexer operations.
"""

from papita_txnsmodel.model.indexers import AccountsIndexer
from papita_txnsmodel.utils.classutils import MetaSingleton

from .base import OwnedTableRepository


class AccountsIndexerRepository(OwnedTableRepository, metaclass=MetaSingleton):
    """Repository for account indexer database operations.

    This class extends the OwnedTableRepository to provide account indexer-specific database
    operations. It uses the Singleton pattern via MetaSingleton to ensure only
    one instance exists throughout the application.

    The repository works with AccountsIndexer objects and provides all the CRUD
    operations inherited from OwnedTableRepository, including querying, inserting,
    updating, and deleting account indexer records.

    Attributes:
        __expected_dao_type__ (type[AccountsIndexer]): The expected DAO type for this
            repository, set to AccountsIndexer.
    """

    __expected_dao_type__ = AccountsIndexer
