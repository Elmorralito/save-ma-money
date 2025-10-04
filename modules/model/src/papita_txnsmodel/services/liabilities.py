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

from papita_txnsmodel.access.liabilities.dto import (
    BankCreditLiabilityAccountsDTO,
    CreditCardLiabilityAccountsDTO,
    LiabilityAccountsDTO,
)
from papita_txnsmodel.access.liabilities.repository import (
    ExtendedLiabilityAccountsRepository,
    LiabilityAccountsRepository,
)
from papita_txnsmodel.services.base import BaseService


class LiabilityAccountsService(BaseService):
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

    dto_type: type[LiabilityAccountsDTO] = LiabilityAccountsDTO
    repository_type: type[LiabilityAccountsRepository] = LiabilityAccountsRepository


class BankCreditLiabilityAccountsService(BaseService):

    dto_type: type[BankCreditLiabilityAccountsDTO] = BankCreditLiabilityAccountsDTO
    repository_type: type[ExtendedLiabilityAccountsRepository] = ExtendedLiabilityAccountsRepository


class CreditCardLiabilityAccountsService(BaseService):

    dto_type: type[CreditCardLiabilityAccountsDTO] = CreditCardLiabilityAccountsDTO
    repository_type: type[ExtendedLiabilityAccountsRepository] = ExtendedLiabilityAccountsRepository
