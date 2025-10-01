"""Accounts repository module for the Papita Transactions system.

This module defines the repository class for account entities in the system.
It provides database access operations specific to accounts, extending the base
repository functionality with account-specific implementations.

Classes:
    AccountsRepository: Repository for account entity database operations.
"""

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.base.repository import BaseRepository
from papita_txnsmodel.utils.classutils import MetaSingleton


class AccountsRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for account entity database operations.

    This class extends the BaseRepository to provide account-specific database
    operations. It uses the Singleton pattern via MetaSingleton to ensure only
    one instance exists throughout the application.

    The repository works with AccountsDTO objects and provides all the CRUD
    operations inherited from BaseRepository, including querying, inserting,
    updating, and deleting account records.

    Attributes:
        __expected_dto_type__ (type[AccountsDTO]): The expected DTO type for this
            repository, set to AccountsDTO.
    """

    __expected_dto_type__ = AccountsDTO
