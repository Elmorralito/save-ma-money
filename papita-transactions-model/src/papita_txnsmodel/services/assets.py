# pylint: disable=W0511

from papita_txnsmodel.access.assets.dto import (
    AssetAccountsDTO,
    ExtendedAssetAccountDTO,
    RealStateAssetAccountsDTO,
    TradingAssetAccountsDTO,
)
from papita_txnsmodel.access.assets.repository import AssetAccountsRepository, ExtendedAssetAccountRepository
from papita_txnsmodel.access.types.dto import TypesDTO

from .accounts import AccountsService
from .extends import LinkedEntitiesService, LinkedEntity, TypedLinkedEntitiesServiceMixin
from .liabilities import ExtendedLiabilityAccountService


class AssetAccountsService(TypedLinkedEntitiesServiceMixin):

    __links__: dict[str, LinkedEntity] = {
        "account": LinkedEntity(
            expected_other_entity_service_type=AccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="account_id",
            own_entity_link_field_name="account",
        ),
        "bank_credit_liability_account": LinkedEntity(
            expected_other_entity_service_type=ExtendedLiabilityAccountService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="bank_credit_liability_account_id",
            own_entity_link_field_name="bank_credit_liability_account",
        ),
    }

    type_id_column_name: str = "account_type_id"
    type_id_field_name: str = "account_type"
    dto_type: type[AssetAccountsDTO] = AssetAccountsDTO
    repository_type: type[AssetAccountsRepository] = AssetAccountsRepository
    types_dto_type: type[TypesDTO] = TypesDTO


class ExtendedAssetAccountService(LinkedEntitiesService):

    __links__: dict[str, LinkedEntity] = {
        "asset_account": LinkedEntity(
            expected_other_entity_service_type=AssetAccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="asset_account_id",
            own_entity_link_field_name="asset_account",
        )
    }

    dto_type: type[ExtendedAssetAccountDTO] = ExtendedAssetAccountDTO
    repository_type: type[ExtendedAssetAccountRepository] = ExtendedAssetAccountRepository


class RealStateAssetAccountsService(LinkedEntitiesService):

    __links__: dict[str, LinkedEntity] = {
        "asset_account": LinkedEntity(
            expected_other_entity_service_type=AssetAccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="asset_account_id",
            own_entity_link_field_name="asset_account",
        ),
    }

    dto_type: type[RealStateAssetAccountsDTO] = RealStateAssetAccountsDTO
    repository_type: type[ExtendedAssetAccountRepository] = ExtendedAssetAccountRepository


class TradingAssetAccountsService(LinkedEntitiesService):

    __links__: dict[str, LinkedEntity] = {
        "asset_account": LinkedEntity(
            expected_other_entity_service_type=AssetAccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="asset_account_id",
            own_entity_link_field_name="asset_account",
        ),
    }

    dto_type: type[TradingAssetAccountsDTO] = TradingAssetAccountsDTO
    repository_type: type[ExtendedAssetAccountRepository] = ExtendedAssetAccountRepository
