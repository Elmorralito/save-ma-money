"""Accounts indexer service module for the Papita Transactions system.

This module defines services for managing account indexing in the system. Account indexers
provide a consolidated view across different types of accounts (standard accounts, assets,
liabilities) by establishing links between related entities. This enables efficient
cross-account querying and operations.

Classes:
    AccountsIndexerService: Service for managing account indexer entities with typed links
                            to various account types.
"""

from typing import Any

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.access.indexers.dto import AccountsIndexerDTO
from papita_txnsmodel.access.indexers.repository import AccountsIndexerRepository
from papita_txnsmodel.access.types.dto import TypesDTO
from papita_txnsmodel.model.enums import TypesClassifications

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
        __type_classication_relations__ (dict): Maps TypesClassifications enums to their
            corresponding field names in the account indexer, used for classification validation.
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

    __type_classication_relations__ = {
        TypesClassifications.ASSETS: "asset_account",
        TypesClassifications.LIABILITIES: "liability_account",
    }

    type_id_column_name: str = "type_id"
    type_id_field_name: str = "type"
    dto_type: type[AccountsIndexerDTO] = AccountsIndexerDTO
    repository_type: type[AccountsIndexerRepository] = AccountsIndexerRepository
    types_dto_type: type[TypesDTO] = TypesDTO

    def get_extended_account_classification(self, *, obj: TableDTO | dict[str, Any], **kwargs) -> TypesClassifications:
        """Determine the account classification type based on the object's linked entities.

        This method examines the provided object to identify its classification by checking
        which linked entity fields are populated. It uses the __type_classication_relations__
        mapping to associate populated fields with TypesClassifications enum values.
        Args:
            obj: The object to analyze, either as a TableDTO or a dictionary of attributes.
            **kwargs: Additional keyword arguments for future extensibility.

        Returns:
            TypesClassifications: The classification enum value for the account.

        Raises:
            TypeError: If the object is not a TableDTO or dictionary.
            ValueError: If the account classification cannot be determined from the object.
        """
        for enum, field_name in self.__type_classication_relations__.items():
            if isinstance(obj, dict):
                if obj.get(field_name):
                    return enum
            elif isinstance(obj, TableDTO):
                if getattr(obj, field_name, None):
                    return enum
            else:
                raise TypeError(f"Expected TableDTO | dict[str, Any], got {type(obj)}")

        raise ValueError("obj or field_name not supported.")

    def create(self, *, obj: TableDTO | dict[str, Any], **kwargs) -> TableDTO:
        """Create a new typed and linked entity record in the database.

        This method combines the create methods of TypedEntitiesService and
        LinkedEntitiesService to handle both type associations and entity relationships.
        It also validates that the type's classification matches the expected classification
        based on the account type being created.

        Args:
            obj: The object to create, either as a TableDTO or a dictionary of attributes.
            **kwargs: Additional keyword arguments to pass to the repository method.

        Returns:
            TableDTO: The created object as a DTO with type and linked entity information.

        Raises:
            TypeError: If the object is not a TableDTO or dictionary.
            ValueError: If the selected type does not match the expected classification.
        """
        if isinstance(obj, dict):
            type_obj = obj[self.type_id_field_name]
        elif isinstance(obj, TableDTO):
            type_obj = getattr(obj, self.type_id_field_name)
        else:
            raise TypeError(f"Expected TableDTO | dict[str, Any], got {type(obj)}")

        type_dto = self.types_service.get_or_create(obj=type_obj, **kwargs)
        if type_dto.classification != self.get_extended_account_classification(obj=obj, **kwargs):
            raise ValueError("The selectedtype does not correspond to the expected classification.")

        if isinstance(obj, dict):
            obj[self.type_id_field_name] = type_dto
        elif isinstance(obj, TableDTO):
            setattr(obj, self.type_id_field_name, type_dto)

        return super().create(obj=obj, **kwargs)
