"""Repositories for v3 account extension tables."""

from papita_txnsmodel.access.account_details.dto import (
    BankingAccountDetailsDTO,
    CreditCardAccountDetailsDTO,
    LoanAccountDetailsDTO,
    RealEstateAccountDetailsDTO,
    TradingAccountDetailsDTO,
)
from papita_txnsmodel.access.base.repository import BaseRepository
from papita_txnsmodel.utils.classutils import MetaSingleton


class BankingAccountDetailsRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for banking account details."""

    __expected_dto__ = BankingAccountDetailsDTO


class RealEstateAccountDetailsRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for real-estate account details."""

    __expected_dto__ = RealEstateAccountDetailsDTO


class TradingAccountDetailsRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for trading account details."""

    __expected_dto__ = TradingAccountDetailsDTO


class CreditCardAccountDetailsRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for credit card account details."""

    __expected_dto__ = CreditCardAccountDetailsDTO


class LoanAccountDetailsRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository for loan account details."""

    __expected_dto__ = LoanAccountDetailsDTO
