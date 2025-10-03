"""Liabilities service module for the Papita Transactions system.

This module provides services for managing liability accounts in the system, including
basic liability accounts and extended liability account information. It implements
the necessary functionality to handle the relationships between liabilities and other
entities like accounts.

Classes:
    LiabilityAccountsService: Service for managing basic liability accounts.
    ExtendedLiabilityAccountService: Service for managing extended liability account information.
"""

# pylint: disable=W0511

from pydantic import field_validator

from papita_txnsmodel.access.liabilities.dto import (
    ExtendedLiabilityAccountsDTO,
    LiabilityAccountsDTO,
)
from papita_txnsmodel.access.liabilities.repository import (
    ExtendedLiabilityAccountsRepository,
    LiabilityAccountsRepository,
)
from papita_txnsmodel.access.types.dto import TypesDTO
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.extends import LinkedEntitiesService, LinkedEntity, TypedLinkedEntitiesServiceMixin


class LiabilityAccountsService(TypedLinkedEntitiesServiceMixin):
    """Service for managing liability accounts in the Papita Transactions system.

    This service extends the TypedLinkedEntitiesServiceMixin to handle liability accounts
    that have both type associations and relationships with other entities like
    regular accounts.

    Attributes:
        __links__ (dict[str, LinkedEntity]): Dictionary defining the relationships
            between liability accounts and other entities.
        type_id_column_name (str): Name of the column storing the liability account type ID.
        type_id_field_name (str): Name of the field storing the liability account type.
        dto_type (type[LiabilityAccountsDTO]): DTO type for liability accounts.
        repository_type (type[LiabilityAccountsRepository]): Repository for liability account
            database operations.
        types_dto_type (type[TypesDTO]): DTO type for types.
    """

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
    types_dto_type: type[TypesDTO] = TypesDTO


class ExtendedLiabilityAccountService(LinkedEntitiesService):
    """Service for managing extended liability account information.

    This service extends the LinkedEntitiesService to handle extended liability account
    information that has relationships with basic liability accounts. It enforces
    the requirement that a concrete implementation of the abstract ExtendedLiabilityAccountsDTO
    class must be provided.

    Attributes:
        __links__ (dict[str, LinkedEntity]): Dictionary defining the relationship
            between extended liability accounts and basic liability accounts.
        repository_type (type[ExtendedLiabilityAccountsRepository]): Repository for extended
            liability account database operations.
    """

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
    def validate_dto_type(cls, value: type[ExtendedLiabilityAccountsDTO]) -> type[ExtendedLiabilityAccountsDTO]:
        """Validate that a concrete implementation of ExtendedLiabilityAccountsDTO is provided.

        This validator ensures that the dto_type is a subclass of ExtendedLiabilityAccountsDTO
        but not the abstract class itself, enforcing that a concrete implementation must be provided.

        Args:
            value: The DTO type to validate.

        Returns:
            type[ExtendedLiabilityAccountsDTO]: The validated DTO type.

        Raises:
            TypeError: If the value is the abstract ExtendedLiabilityAccountsDTO class itself.
        """
        if issubclass(value, ExtendedLiabilityAccountsDTO) and value == ExtendedLiabilityAccountsDTO:
            raise TypeError(
                "It's necessary to provide a implementation of the abstract class 'ExtendedLiabilityAccountsDTO'."
            )

        return value
