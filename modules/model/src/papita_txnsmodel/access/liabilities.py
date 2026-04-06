"""Liabilities repository module for the Papita Transactions system.

This module defines the repository classes for liability entities in the system.
It provides database access operations specific to liabilities, extending the base
repository functionality with liability-specific implementations.

The module contains two main repository classes:
    - LiabilityAccountsRepository: For standard liability account operations
    - ExtendedLiabilityAccountsRepository: For specialized liability account operations

These repositories handle the database interactions for liability accounts, providing
a clean abstraction layer between the database and the business logic.
"""

from papita_txnsmodel.model.liabilities import ExtendedLiabilityAccounts, LiabilityAccounts
from papita_txnsmodel.utils.classutils import MetaSingleton

from .base import OwnedTableRepository


class LiabilityAccountsRepository(OwnedTableRepository, metaclass=MetaSingleton):
    """Repository for general liability account database operations.

    This class extends the OwnedTableRepository to provide liability account-specific database
    operations. It uses the Singleton pattern via MetaSingleton to ensure only
    one instance exists throughout the application.

    The repository works with LiabilityAccounts objects and provides all the CRUD
    operations inherited from OwnedTableRepository, including querying, inserting,
    updating, and deleting liability account records.

    Attributes:
        __expected_dao_type__ (type[LiabilityAccounts]): The expected DAO type for this
            repository, set to LiabilityAccounts.
    """

    __expected_dao_type__ = LiabilityAccounts


class ExtendedLiabilityAccountsRepository(OwnedTableRepository, metaclass=MetaSingleton):
    """Repository for specialized liability account database operations.

    This class extends the OwnedTableRepository to provide operations for specialized
    liability account types such as bank credit liabilities and credit card liabilities.
    It uses the Singleton pattern via MetaSingleton to ensure only one instance
    exists throughout the application.

    The repository works with ExtendedLiabilityAccounts objects and their subclasses,
    providing all the CRUD operations inherited from OwnedTableRepository for these
    specialized liability types.

    Attributes:
        __expected_dao_type__ (type[ExtendedLiabilityAccounts]): The expected DAO type for this
            repository, set to ExtendedLiabilityAccounts.
    """

    __expected_dao_type__ = ExtendedLiabilityAccounts
