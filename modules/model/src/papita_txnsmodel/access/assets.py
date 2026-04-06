"""Assets repository module for the Papita Transactions system.

This module defines the repository classes for asset entities in the system.
It provides database access operations specific to assets, extending the base
repository functionality with asset-specific implementations.

Classes:
    AssetAccountsRepository: Repository for general asset account operations.
    ExtendedAssetAccountsRepository: Repository for specialized asset account operations.
    FinancedAssetAccountsRepository: Repository for financed asset account operations.
"""

from papita_txnsmodel.model.assets import AssetAccounts, ExtendedAssetAccounts, FinancedAssetAccounts
from papita_txnsmodel.utils.classutils import MetaSingleton

from .base import OwnedTableRepository


class AssetAccountsRepository(OwnedTableRepository, metaclass=MetaSingleton):
    """Repository for general asset account database operations.

    This class extends the OwnedTableRepository to provide asset account-specific database
    operations. It uses the Singleton pattern via MetaSingleton to ensure only
    one instance exists throughout the application.

    The repository works with AssetAccounts objects and provides all the CRUD
    operations inherited from OwnedTableRepository, including querying, inserting,
    updating, and deleting asset account records.

    Attributes:
        __expected_dao_type__ (type[AssetAccounts]): The expected DAO type for this
            repository, set to AssetAccounts.
    """

    __expected_dao_type__ = AssetAccounts


class ExtendedAssetAccountsRepository(OwnedTableRepository, metaclass=MetaSingleton):
    """Repository for specialized asset account database operations.

    This class extends the OwnedTableRepository to provide operations for specialized
    asset account types such as banking assets, real estate assets, and trading assets.
    It uses the Singleton pattern via MetaSingleton to ensure only one instance
    exists throughout the application.

    The repository works with ExtendedAssetAccounts objects and their subclasses,
    providing all the CRUD operations inherited from OwnedTableRepository for these
    specialized asset types.

    Attributes:
        __expected_dao_type__ (type[ExtendedAssetAccounts]): The expected DAO type for this
            repository, set to ExtendedAssetAccounts.
    """

    __expected_dao_type__ = ExtendedAssetAccounts


class FinancedAssetAccountsRepository(OwnedTableRepository, metaclass=MetaSingleton):
    """Repository for financed asset account database operations.

    This class extends the OwnedTableRepository to provide operations specifically for
    assets that are partially or fully financed through credit or loans. It uses
    the Singleton pattern via MetaSingleton to ensure only one instance exists
    throughout the application.

    The repository works with FinancedAssetAccountsDTO objects, providing all the
    CRUD operations inherited from OwnedTableRepository for managing financing details
    of asset accounts.

    Attributes:
        __expected_dto__ (type[FinancedAssetAccountsDTO]): The expected DTO type for this
            repository, set to FinancedAssetAccountsDTO.
    """

    __expected_dao_type__ = FinancedAssetAccounts
