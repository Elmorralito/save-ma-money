"""Liabilities service module for the Papita Transactions system.

This module provides services for managing liability accounts in the system, including
basic liability accounts and extended liability account information. It implements
the necessary functionality to handle the relationships between liabilities and other
entities like accounts.

Classes:
    LiabilityAccountsService: Service for managing basic liability accounts.
    BankCreditLiabilityAccountsService: Service for managing bank credit liability accounts.
    CreditCardLiabilityAccountsService: Service for managing credit card liability accounts.
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

    This service provides functionality for creating, retrieving, updating, and deleting
    liability accounts. It leverages the LiabilityAccountsRepository for database operations
    and uses LiabilityAccountsDTO for data transfer.

    The service manages the core attributes of liability accounts including identifiers,
    names, descriptions, balances, and any relationships to other financial entities.

    Attributes:
        dto_type (type[LiabilityAccountsDTO]): DTO class used for liability account data transfer.
        repository_type (type[LiabilityAccountsRepository]): Repository class used for
            liability account database operations.
    """

    dto_type: type[LiabilityAccountsDTO] = LiabilityAccountsDTO
    repository_type: type[LiabilityAccountsRepository] = LiabilityAccountsRepository


class BankCreditLiabilityAccountsService(BaseService):
    """Service for managing bank credit liability accounts.

    This service specializes in handling bank credit liability accounts which may include
    lines of credit, overdraft facilities, and other bank-provided credit products. It extends
    the base service functionality with bank credit-specific operations.

    The service uses an extended liability accounts repository to handle additional fields
    and relationships specific to bank credit accounts such as credit limits, interest rates,
    and payment terms.

    Attributes:
        dto_type (type[BankCreditLiabilityAccountsDTO]): DTO class used for bank credit
            liability account data transfer.
        repository_type (type[ExtendedLiabilityAccountsRepository]): Repository class used for
            extended liability account database operations.
    """

    dto_type: type[BankCreditLiabilityAccountsDTO] = BankCreditLiabilityAccountsDTO
    repository_type: type[ExtendedLiabilityAccountsRepository] = ExtendedLiabilityAccountsRepository


class CreditCardLiabilityAccountsService(BaseService):
    """Service for managing credit card liability accounts.

    This service specializes in handling credit card liability accounts, providing functionality
    specific to credit card management such as tracking credit limits, statement periods,
    minimum payments, and interest calculations.

    The service uses an extended liability accounts repository to accommodate the additional
    attributes and relationships specific to credit card accounts.

    Attributes:
        dto_type (type[CreditCardLiabilityAccountsDTO]): DTO class used for credit card
            liability account data transfer.
        repository_type (type[ExtendedLiabilityAccountsRepository]): Repository class used for
            extended liability account database operations.
    """

    dto_type: type[CreditCardLiabilityAccountsDTO] = CreditCardLiabilityAccountsDTO
    repository_type: type[ExtendedLiabilityAccountsRepository] = ExtendedLiabilityAccountsRepository
