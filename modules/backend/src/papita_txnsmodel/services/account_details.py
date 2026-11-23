"""Services for v3 account extension tables."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from papita_txnsmodel.access.account_details.dto import (
    AccountDetailsDTO,
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


class _AccountDetailsServiceBase(BaseService):
    """Shared batch-lookup helper for 1:1 account extension services."""

    def get_map_by_account_ids(
        self,
        account_ids: Sequence[uuid.UUID],
        **kwargs,
    ) -> dict[uuid.UUID, AccountDetailsDTO]:
        """Return a mapping of ``account_id`` -> extension DTO for owner-validated IDs."""
        if not account_ids or self._repository is None:
            return {}
        rows = self._repository.get_by_account_ids(list(account_ids), **kwargs)
        return {row.account_id: row for row in rows}


class BankingAccountDetailsService(_AccountDetailsServiceBase):
    """Service for banking account extension rows."""

    dto_type: type[BankingAccountDetailsDTO] = BankingAccountDetailsDTO
    repository_type: type[BankingAccountDetailsRepository] = BankingAccountDetailsRepository


class RealEstateAccountDetailsService(_AccountDetailsServiceBase):
    """Service for real-estate account extension rows."""

    dto_type: type[RealEstateAccountDetailsDTO] = RealEstateAccountDetailsDTO
    repository_type: type[RealEstateAccountDetailsRepository] = RealEstateAccountDetailsRepository


class TradingAccountDetailsService(_AccountDetailsServiceBase):
    """Service for trading account extension rows."""

    dto_type: type[TradingAccountDetailsDTO] = TradingAccountDetailsDTO
    repository_type: type[TradingAccountDetailsRepository] = TradingAccountDetailsRepository


class CreditCardAccountDetailsService(_AccountDetailsServiceBase):
    """Service for credit card account extension rows."""

    dto_type: type[CreditCardAccountDetailsDTO] = CreditCardAccountDetailsDTO
    repository_type: type[CreditCardAccountDetailsRepository] = CreditCardAccountDetailsRepository


class LoanAccountDetailsService(_AccountDetailsServiceBase):
    """Service for loan account extension rows."""

    dto_type: type[LoanAccountDetailsDTO] = LoanAccountDetailsDTO
    repository_type: type[LoanAccountDetailsRepository] = LoanAccountDetailsRepository
