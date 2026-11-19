"""Services for v3 account extension tables."""

from papita_txnsmodel.access.account_details.dto import (
    BankingAccountDetailsDTO,
    CreditCardAccountDetailsDTO,
    LoanAccountDetailsDTO,
    RealEstateAccountDetailsDTO,
    TradingAccountDetailsDTO,
)
from papita_txnsmodel.access.account_details.repository import (
    BankingAccountDetailsRepository,
    CreditCardAccountDetailsRepository,
    LoanAccountDetailsRepository,
    RealEstateAccountDetailsRepository,
    TradingAccountDetailsRepository,
)
from papita_txnsmodel.services.base import BaseService


class BankingAccountDetailsService(BaseService):
    """Service for banking account extension rows."""

    dto_type: type[BankingAccountDetailsDTO] = BankingAccountDetailsDTO
    repository_type: type[BankingAccountDetailsRepository] = BankingAccountDetailsRepository


class RealEstateAccountDetailsService(BaseService):
    """Service for real-estate account extension rows."""

    dto_type: type[RealEstateAccountDetailsDTO] = RealEstateAccountDetailsDTO
    repository_type: type[RealEstateAccountDetailsRepository] = RealEstateAccountDetailsRepository


class TradingAccountDetailsService(BaseService):
    """Service for trading account extension rows."""

    dto_type: type[TradingAccountDetailsDTO] = TradingAccountDetailsDTO
    repository_type: type[TradingAccountDetailsRepository] = TradingAccountDetailsRepository


class CreditCardAccountDetailsService(BaseService):
    """Service for credit card account extension rows."""

    dto_type: type[CreditCardAccountDetailsDTO] = CreditCardAccountDetailsDTO
    repository_type: type[CreditCardAccountDetailsRepository] = CreditCardAccountDetailsRepository


class LoanAccountDetailsService(BaseService):
    """Service for loan account extension rows."""

    dto_type: type[LoanAccountDetailsDTO] = LoanAccountDetailsDTO
    repository_type: type[LoanAccountDetailsRepository] = LoanAccountDetailsRepository
