"""Assets service module for the Papita Transactions system.

This module provides services for managing asset accounts in the system, including
general asset accounts, real estate assets, and trading assets. It implements the
necessary functionality to handle the relationships between assets and other entities
like accounts and liability accounts.

Classes:
    AssetAccountsService: Service for managing general asset accounts.
    ExtendedAssetAccountService: Service for managing extended asset account information.
    RealEstateAssetAccountsService: Service for managing real estate asset accounts.
    TradingAssetAccountsService: Service for managing trading asset accounts.
"""

# pylint: disable=W0511

from papita_txnsmodel.access.assets.dto import (
    AssetAccountsDTO,
    FinancedAssetAccountsDTO,
    RealEstateAssetAccountsDTO,
    TradingAssetAccountsDTO,
)
from papita_txnsmodel.access.assets.repository import AssetAccountsRepository, ExtendedAssetAccountsRepository
from papita_txnsmodel.services.base import BaseService

from .extends import LinkedEntitiesService, LinkedEntity
from .liabilities import BankCreditLiabilityAccountsService


class AssetAccountsService(BaseService):
    """Service for managing trading asset accounts.

    This service extends the BaseService to handle trading asset accounts
    that have relationships with basic asset accounts. It provides functionality
    specific to trading assets like securities, stocks, and other investment vehicles.

    Attributes:
        __links__ (dict[str, LinkedEntity]): Dictionary defining the relationship
            between trading asset accounts and basic asset accounts.
        dto_type (type[TradingAssetAccountsDTO]): DTO type for trading asset accounts.
        repository_type (type[ExtendedAssetAccountRepository]): Repository for extended
            asset account database operations.
    """

    dto_type: type[AssetAccountsDTO] = AssetAccountsDTO
    repository_type: type[AssetAccountsRepository] = AssetAccountsRepository


class FinancedAssetAccountsService(LinkedEntitiesService):
    """Service for managing asset accounts in the Papita Transactions system.

    This service extends the TypedLinkedEntitiesServiceMixin to handle asset accounts
    that have both type associations and relationships with other entities like
    regular accounts and bank credit liability accounts.

    Attributes:
        __links__ (dict[str, LinkedEntity]): Dictionary defining the relationships
            between asset accounts and other entities.
        type_id_column_name (str): Name of the column storing the asset account type ID.
        type_id_field_name (str): Name of the field storing the asset account type.
        dto_type (type[AssetAccountsDTO]): DTO type for asset accounts.
        repository_type (type[AssetAccountsRepository]): Repository for asset account
            database operations.
        types_dto_type (type[TypesDTO]): DTO type for types.
    """

    __links__: dict[str, LinkedEntity] = {
        "bank_credit_liability_account": LinkedEntity(
            expected_other_entity_service_type=BankCreditLiabilityAccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="bank_credit_liability_account_id",
            own_entity_link_field_name="bank_credit_liability_account",
        ),
    }

    dto_type: type[FinancedAssetAccountsDTO] = FinancedAssetAccountsDTO
    repository_type: type[ExtendedAssetAccountsRepository] = ExtendedAssetAccountsRepository


class RealEstateAssetAccountsService(BaseService):
    """Service for managing real estate asset accounts.

    This service extends the BaseService to handle real estate asset accounts
    that have relationships with basic asset accounts. It provides functionality
    specific to real estate assets like property details and ownership information.

    Attributes:
        __links__ (dict[str, LinkedEntity]): Dictionary defining the relationship
            between real estate asset accounts and basic asset accounts.
        dto_type (type[RealEstateAssetAccountsDTO]): DTO type for real estate asset accounts.
        repository_type (type[ExtendedAssetAccountRepository]): Repository for extended
            asset account database operations.
    """

    dto_type: type[RealEstateAssetAccountsDTO] = RealEstateAssetAccountsDTO
    repository_type: type[ExtendedAssetAccountsRepository] = ExtendedAssetAccountsRepository


class TradingAssetAccountsService(BaseService):
    """Service for managing trading asset accounts.

    This service extends the BaseService to handle trading asset accounts
    that have relationships with basic asset accounts. It provides functionality
    specific to trading assets like securities, stocks, and other investment vehicles.

    Attributes:
        __links__ (dict[str, LinkedEntity]): Dictionary defining the relationship
            between trading asset accounts and basic asset accounts.
        dto_type (type[TradingAssetAccountsDTO]): DTO type for trading asset accounts.
        repository_type (type[ExtendedAssetAccountRepository]): Repository for extended
            asset account database operations.
    """

    dto_type: type[TradingAssetAccountsDTO] = TradingAssetAccountsDTO
    repository_type: type[ExtendedAssetAccountsRepository] = ExtendedAssetAccountsRepository
