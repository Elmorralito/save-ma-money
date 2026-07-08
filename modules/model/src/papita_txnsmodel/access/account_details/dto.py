"""DTOs for v3 account extension tables (1:1 account details)."""

import uuid

from pydantic import Field

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.model.account_details import (
    BankingAccountDetails,
    CreditCardAccountDetails,
    LoanAccountDetails,
    RealEstateAccountDetails,
    TradingAccountDetails,
)
from papita_txnsmodel.model.enums import RealEstateAreaUnit, RealEstateOwnership


class AccountDetailsDTO(TableDTO):
    """Base DTO for account extension tables keyed by account_id."""

    def to_dao(self):
        """Convert to DAO, excluding the generic TableDTO id field."""
        data = self.model_dump(mode="python", exclude_unset=True, exclude_none=True, exclude={"id"})
        return self.__dao_type__.model_validate(data)


class BankingAccountDetailsDTO(AccountDetailsDTO):
    """DTO for banking account extension rows."""

    __dao_type__ = BankingAccountDetails

    account_id: uuid.UUID
    entity: str
    account_number: str | None = None


class RealEstateAccountDetailsDTO(AccountDetailsDTO):
    """DTO for real-estate account extension rows."""

    __dao_type__ = RealEstateAccountDetails

    account_id: uuid.UUID
    address: str
    city: str
    country: str
    total_area: float = Field(gt=0)
    built_area: float = Field(gt=0)
    area_unit: RealEstateAreaUnit
    ownership: RealEstateOwnership
    participation: float = Field(default=1.0, gt=0, le=1)


class TradingAccountDetailsDTO(AccountDetailsDTO):
    """DTO for trading account extension rows."""

    __dao_type__ = TradingAccountDetails

    account_id: uuid.UUID
    buy_value: float = Field(gt=0)
    units: int = Field(default=1, gt=0)


class CreditCardAccountDetailsDTO(AccountDetailsDTO):
    """DTO for credit card account extension rows."""

    __dao_type__ = CreditCardAccountDetails

    account_id: uuid.UUID
    credit_limit: float = Field(gt=0)


class LoanAccountDetailsDTO(AccountDetailsDTO):
    """DTO for loan account extension rows."""

    __dao_type__ = LoanAccountDetails

    account_id: uuid.UUID
    is_paid_off: bool = False
    insurance_payment: float = Field(default=0, ge=0)
    extras_payment: float = Field(default=0, ge=0)
