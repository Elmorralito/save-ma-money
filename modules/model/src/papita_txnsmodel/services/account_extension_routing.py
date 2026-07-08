"""Route v3 account kinds to extension detail services and DTOs."""

from __future__ import annotations

from papita_txnsmodel.access.account_details.dto import (
    AccountDetailsDTO,
    BankingAccountDetailsDTO,
    CreditCardAccountDetailsDTO,
    LoanAccountDetailsDTO,
    RealEstateAccountDetailsDTO,
    TradingAccountDetailsDTO,
)
from papita_txnsmodel.model.enums import AccountKind
from papita_txnsmodel.services.account_details import (
    BankingAccountDetailsService,
    CreditCardAccountDetailsService,
    LoanAccountDetailsService,
    RealEstateAccountDetailsService,
    TradingAccountDetailsService,
)
from papita_txnsmodel.services.base import BaseService

_EXTENSION_BY_KIND: dict[AccountKind, tuple[type[BaseService], type[AccountDetailsDTO]]] = {
    AccountKind.CHECKING: (BankingAccountDetailsService, BankingAccountDetailsDTO),
    AccountKind.SAVINGS: (BankingAccountDetailsService, BankingAccountDetailsDTO),
    AccountKind.CASH: (BankingAccountDetailsService, BankingAccountDetailsDTO),
    AccountKind.INVESTMENT_BROKERAGE: (TradingAccountDetailsService, TradingAccountDetailsDTO),
    AccountKind.REAL_ESTATE: (RealEstateAccountDetailsService, RealEstateAccountDetailsDTO),
    AccountKind.CREDIT_CARD: (CreditCardAccountDetailsService, CreditCardAccountDetailsDTO),
    AccountKind.LOAN_MORTGAGE: (LoanAccountDetailsService, LoanAccountDetailsDTO),
}


def extension_spec_for_kind(
    account_kind: AccountKind,
) -> tuple[type[BaseService], type[AccountDetailsDTO]] | None:
    """Return the extension service and DTO types for an account kind, if any.

    Args:
        account_kind: Consolidated account discriminator.

    Returns:
        Service and DTO types for the 1:1 extension table, or None for kinds
        without extension rows (``OTHER_ASSET``, ``OTHER_LIABILITY``).
    """
    return _EXTENSION_BY_KIND.get(account_kind)


def requires_extension(account_kind: AccountKind) -> bool:
    """Return True when ``account_kind`` expects a ``*_account_details`` row."""
    return account_kind in _EXTENSION_BY_KIND
