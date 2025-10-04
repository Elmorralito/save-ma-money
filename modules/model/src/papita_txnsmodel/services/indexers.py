"""Accounts indexer service module for the Papita Transactions system.

This module defines services for managing account indexing in the system. Account indexers
provide a consolidated view across different types of accounts (standard accounts, assets,
liabilities) by establishing links between related entities. This enables efficient
cross-account querying and operations.

Classes:
    AccountsIndexerService: Service for managing account indexer entities with typed links
                           to various account types.
"""

from papita_txnsmodel.access.indexers.dto import AccountsIndexerDTO
from papita_txnsmodel.access.indexers.repository import AccountsIndexerRepository
from papita_txnsmodel.access.types.dto import TypesDTO

from .accounts import AccountsService
from .assets import AssetAccountsService, RealEstateAssetAccountsService, TradingAssetAccountsService
from .extends import LinkedEntity, TypedLinkedEntitiesServiceMixin
from .liabilities import (
    BankCreditLiabilityAccountsService,
    CreditCardLiabilityAccountsService,
    LiabilityAccountsService,
)


class AccountsIndexerService(TypedLinkedEntitiesServiceMixin):
    """Service for managing account indexer entities with links to various account types.

    This service extends TypedLinkedEntitiesServiceMixin to provide account indexing
    functionality. It creates and manages links between different account entities in the
    system, including standard accounts, various asset accounts, and liability accounts.
    Each link is defined as a LinkedEntity that specifies how the indexer relates to the
    corresponding account service.

    The service allows for consolidated operations across different account types by
    providing a unified interface through the account indexer.

    Attributes:
        __links__ (dict[str, LinkedEntity]): Dictionary mapping link names to LinkedEntity
            configurations. Each LinkedEntity defines how this indexer service links to a
            specific account service.
        type_id_column_name (str): The column name used for type identification in the database.
        type_id_field_name (str): The field name used for type identification in the DTO.
        dto_type (type[AccountsIndexerDTO]): Data Transfer Object type for account indexers.
        repository_type (type[AccountsIndexerRepository]): Repository class for account
            indexer database operations.
        types_dto_type (type[TypesDTO]): Data Transfer Object type for types.
    """

    __links__: dict[str, LinkedEntity] = {
        "account": LinkedEntity(
            expected_other_entity_service_type=AccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="account_id",
            own_entity_link_field_name="account",
        ),
        "asset_account": LinkedEntity(
            expected_other_entity_service_type=AssetAccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="asset_account_id",
            own_entity_link_field_name="asset_account",
        ),
        "real_estate_asset_account": LinkedEntity(
            expected_other_entity_service_type=RealEstateAssetAccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="real_estate_asset_account_id",
            own_entity_link_field_name="real_estate_asset_account",
        ),
        "trading_asset_account": LinkedEntity(
            expected_other_entity_service_type=TradingAssetAccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="trading_asset_account_id",
            own_entity_link_field_name="trading_asset_account",
        ),
        "liability_account": LinkedEntity(
            expected_other_entity_service_type=LiabilityAccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="liability_account_id",
            own_entity_link_field_name="liability_account",
        ),
        "bank_credit_liability_account": LinkedEntity(
            expected_other_entity_service_type=BankCreditLiabilityAccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="bank_credit_liability_account_id",
            own_entity_link_field_name="bank_credit_liability_account",
        ),
        "credit_card_liability_account": LinkedEntity(
            expected_other_entity_service_type=CreditCardLiabilityAccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="credit_card_liability_account_id",
            own_entity_link_field_name="credit_card_liability_account",
        ),
    }

    type_id_column_name: str = "type_id"
    type_id_field_name: str = "type"
    dto_type: type[AccountsIndexerDTO] = AccountsIndexerDTO
    repository_type: type[AccountsIndexerRepository] = AccountsIndexerRepository
    types_dto_type: type[TypesDTO] = TypesDTO
