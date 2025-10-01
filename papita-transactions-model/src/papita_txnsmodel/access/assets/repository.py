"""Assets repository module for the Papita Transactions system.

This module defines the repository classes for asset entities in the system.
It provides database access operations specific to assets, extending the base
repository functionality with asset-specific implementations.

Classes:
    AssetAccountsRepository: Repository for general asset account operations.
    ExtendedAssetAccountRepository: Repository for specialized asset account operations.
"""

from papita_txnsmodel.access.base.repository import BaseRepository
from papita_txnsmodel.utils.classutils import MetaSingleton

from .dto import AssetAccountsDTO, ExtendedAssetAccountDTO


class AssetAccountsRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for general asset account database operations.

    This class extends the BaseRepository to provide asset account-specific database
    operations. It uses the Singleton pattern via MetaSingleton to ensure only
    one instance exists throughout the application.

    The repository works with AssetAccountsDTO objects and provides all the CRUD
    operations inherited from BaseRepository, including querying, inserting,
    updating, and deleting asset account records.

    Attributes:
        __expected_dto__ (type[AssetAccountsDTO]): The expected DTO type for this
            repository, set to AssetAccountsDTO.
    """

    __expected_dto__ = AssetAccountsDTO


class ExtendedAssetAccountRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for specialized asset account database operations.

    This class extends the BaseRepository to provide operations for specialized
    asset account types such as banking assets, real estate assets, and trading assets.
    It uses the Singleton pattern via MetaSingleton to ensure only one instance
    exists throughout the application.

    The repository works with ExtendedAssetAccountDTO objects and their subclasses,
    providing all the CRUD operations inherited from BaseRepository for these
    specialized asset types.

    Attributes:
        __expected_dto__ (type[ExtendedAssetAccountDTO]): The expected DTO type for this
            repository, set to ExtendedAssetAccountDTO.
    """

    __expected_dto__ = ExtendedAssetAccountDTO
