"""Liabilities repository module for the Papita Transactions system.

This module defines the repository classes for liability entities in the system.
It provides database access operations specific to liabilities, extending the base
repository functionality with liability-specific implementations.

Classes:
    LiabilityAccountsRepository: Repository for general liability account operations.
    ExtendedLiabilityAccountRepository: Repository for specialized liability account operations.
"""

from papita_txnsmodel.access.base.repository import BaseRepository
from papita_txnsmodel.utils.classutils import MetaSingleton

from .dto import ExtendedLiabilityAccountsDTO, LiabilityAccountsDTO


class LiabilityAccountsRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for general liability account database operations.

    This class extends the BaseRepository to provide liability account-specific database
    operations. It uses the Singleton pattern via MetaSingleton to ensure only
    one instance exists throughout the application.

    The repository works with LiabilityAccountsDTO objects and provides all the CRUD
    operations inherited from BaseRepository, including querying, inserting,
    updating, and deleting liability account records.

    Attributes:
        __expected_dto__ (type[LiabilityAccountsDTO]): The expected DTO type for this
            repository, set to LiabilityAccountsDTO.
    """

    __expected_dto__ = LiabilityAccountsDTO


class ExtendedLiabilityAccountsRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for specialized liability account database operations.

    This class extends the BaseRepository to provide operations for specialized
    liability account types such as bank credit liabilities and credit card liabilities.
    It uses the Singleton pattern via MetaSingleton to ensure only one instance
    exists throughout the application.

    The repository works with ExtendedLiabilityAccountsDTO objects and their subclasses,
    providing all the CRUD operations inherited from BaseRepository for these
    specialized liability types.

    Attributes:
        __expected_dto__ (type[ExtendedLiabilityAccountsDTO]): The expected DTO type for this
            repository, set to ExtendedLiabilityAccountsDTO.
    """

    __expected_dto__ = ExtendedLiabilityAccountsDTO
