# pylint: disable=W0511

from pydantic import field_validator

from papita_txnsmodel.access.liabilities.dto import (
    LiabilityAccountsDTO,
    _ExtendedLiabilityAccountsDTO,
)
from papita_txnsmodel.access.liabilities.repository import (
    ExtendedLiabilityAccountsRepository,
    LiabilityAccountsRepository,
)
from papita_txnsmodel.access.types.dto import LiabilityAccountTypesDTO
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.extends import LinkedEntitiesService, LinkedEntity, TypedLinkedEntitiesServiceMixin


class LiabilityAccountsService(TypedLinkedEntitiesServiceMixin):

    __links__: dict[str, LinkedEntity] = {
        "account": LinkedEntity(
            expected_other_entity_service_type=AccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="account_id",
            own_entity_link_field_name="account",
        ),
    }

    type_id_column_name: str = "account_type_id"
    type_id_field_name: str = "account_type"
    dto_type: type[LiabilityAccountsDTO] = LiabilityAccountsDTO
    repository_type: type[LiabilityAccountsRepository] = LiabilityAccountsRepository
    types_dto_type: type[LiabilityAccountTypesDTO] = LiabilityAccountTypesDTO


class ExtendedLiabilityAccountService(LinkedEntitiesService):

    __links__: dict[str, LinkedEntity] = {
        "liability_account": LinkedEntity(
            expected_other_entity_service_type=LiabilityAccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="liability_account_id",
            own_entity_link_field_name="liability_account",
        )
    }

    repository_type: type[ExtendedLiabilityAccountsRepository] = ExtendedLiabilityAccountsRepository

    @field_validator("dto_type")
    @classmethod
    def validate_dto_type(cls, value: type[_ExtendedLiabilityAccountsDTO]) -> type[_ExtendedLiabilityAccountsDTO]:
        if issubclass(value, _ExtendedLiabilityAccountsDTO) and value == _ExtendedLiabilityAccountsDTO:
            raise TypeError(
                "It's necessary to provide a implementation of the abstract class '_ExtendedLiabilityAccountsDTO'."
            )

        return value
