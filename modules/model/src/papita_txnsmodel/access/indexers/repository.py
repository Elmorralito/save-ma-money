"""Accounts indexer repository module for the Papita Transactions system.

This module defines the repository class for account indexer entities in the system.
It provides database access operations specific to account indexers, extending the base
repository functionality with indexer-specific implementations.

Classes:
    AccountsIndexerRepository: Repository for account indexer operations.
"""

from papita_txnsmodel.access.base.repository import OwnedTableRepository
from papita_txnsmodel.utils.classutils import MetaSingleton

from .dto import AccountsIndexerDTO


class AccountsIndexerRepository(OwnedTableRepository, metaclass=MetaSingleton):
    """Repository for account indexer database operations.

    This class extends the OwnedTableRepository to provide account indexer-specific database
    operations. It uses the Singleton pattern via MetaSingleton to ensure only
    one instance exists throughout the application.

    The repository works with AccountsIndexerDTO objects and provides all the CRUD
    operations inherited from OwnedTableRepository, including querying, inserting,
    updating, and deleting account indexer records.

    Attributes:
        __expected_dto__ (type[AccountsIndexerDTO]): The expected DTO type for this
            repository, set to AccountsIndexerDTO.
    """

    __expected_dto__ = AccountsIndexerDTO
