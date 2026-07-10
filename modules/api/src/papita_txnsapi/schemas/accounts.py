"""Account request/response schemas for PPT-036."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator

from papita_txnsapi.schemas.converters import enum_to_api_slug, parse_account_kind, parse_ledger_side
from papita_txnsmodel.access.account_balances.dto import AccountBalancesDTO
from papita_txnsmodel.access.account_details.dto import (
    AccountDetailsDTO,
    BankingAccountDetailsDTO,
    CreditCardAccountDetailsDTO,
    LoanAccountDetailsDTO,
    RealEstateAccountDetailsDTO,
    TradingAccountDetailsDTO,
)
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.model.enums import AccountKind, RealEstateAreaUnit, RealEstateOwnership

# API extension field names keyed by account kind (G1).
_EXTENSION_API_FIELD: dict[AccountKind, str] = {
    AccountKind.CHECKING: "banking_details",
    AccountKind.SAVINGS: "banking_details",
    AccountKind.CASH: "banking_details",
    AccountKind.INVESTMENT_BROKERAGE: "trading_details",
    AccountKind.REAL_ESTATE: "real_estate_details",
    AccountKind.CREDIT_CARD: "credit_card_details",
    AccountKind.LOAN_MORTGAGE: "loan_details",
}


class BankingDetailsSchema(BaseModel):
    """Banking extension fields for checking/savings/cash accounts."""

    entity: str
    account_number: str | None = None


class TradingDetailsSchema(BaseModel):
    """Trading extension fields for investment brokerage accounts."""

    buy_value: float = Field(gt=0)
    units: int = Field(default=1, gt=0)


class RealEstateDetailsSchema(BaseModel):
    """Real-estate extension fields."""

    address: str
    city: str
    country: str
    total_area: float = Field(gt=0)
    built_area: float = Field(gt=0)
    area_unit: str
    ownership: str
    participation: float = Field(default=1.0, gt=0, le=1)

    @field_validator("area_unit")
    @classmethod
    def _validate_area_unit(cls, value: str) -> str:
        parse_area_unit(value)
        return value

    @field_validator("ownership")
    @classmethod
    def _validate_ownership(cls, value: str) -> str:
        parse_ownership(value)
        return value


class CreditCardDetailsSchema(BaseModel):
    """Credit card extension fields."""

    credit_limit: float = Field(gt=0)


class LoanDetailsSchema(BaseModel):
    """Loan extension fields."""

    is_paid_off: bool = False
    insurance_payment: float = Field(default=0, ge=0)
    extras_payment: float = Field(default=0, ge=0)


class AccountCreate(BaseModel):
    """Request body for ``POST /accounts``."""

    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    account_kind: str
    ledger_side: str
    currency: str = Field(default="USD", min_length=3, max_length=3)
    initial_value: float | None = Field(default=None, ge=0)
    banking_details: BankingDetailsSchema | None = None
    trading_details: TradingDetailsSchema | None = None
    real_estate_details: RealEstateDetailsSchema | None = None
    credit_card_details: CreditCardDetailsSchema | None = None
    loan_details: LoanDetailsSchema | None = None

    def to_accounts_dto(self, *, owner_id: uuid.UUID) -> AccountsDTO:
        """Build an ``AccountsDTO`` for the model service layer."""
        return AccountsDTO(
            name=self.name.strip(),
            description=self.description,
            owner_id=owner_id,
            account_kind=parse_account_kind(self.account_kind),
            ledger_side=parse_ledger_side(self.ledger_side),
            currency=self.currency.upper(),
            initial_value=self.initial_value,
        )

    def extension_payload(self) -> dict[str, Any] | None:
        """Return extension dict for ``AccountsService.create_account``."""
        kind = parse_account_kind(self.account_kind)
        field_name = _EXTENSION_API_FIELD.get(kind)
        if field_name is None:
            return None
        nested = getattr(self, field_name, None)
        if nested is None:
            return None
        payload = nested.model_dump(mode="python")
        if field_name == "real_estate_details":
            payload["area_unit"] = parse_area_unit(payload["area_unit"])
            payload["ownership"] = parse_ownership(payload["ownership"])
        return payload


class AccountUpdate(BaseModel):
    """Request body for ``PUT /accounts/{account_id}``."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    initial_value: float | None = Field(default=None, ge=0)
    is_active: bool | None = None
    banking_details: BankingDetailsSchema | None = None
    trading_details: TradingDetailsSchema | None = None
    real_estate_details: RealEstateDetailsSchema | None = None
    credit_card_details: CreditCardDetailsSchema | None = None
    loan_details: LoanDetailsSchema | None = None

    def apply_to(self, existing: AccountsDTO) -> AccountsDTO:
        """Merge partial update fields onto an existing account DTO."""
        updates = self.model_dump(
            exclude_unset=True,
            exclude={
                "banking_details",
                "trading_details",
                "real_estate_details",
                "credit_card_details",
                "loan_details",
                "is_active",
            },
        )
        if self.is_active is not None:
            updates["active"] = self.is_active
        if self.currency is not None:
            updates["currency"] = self.currency.upper()
        merged = existing.model_copy(update=updates)
        return merged

    def extension_payload(self, account_kind: AccountKind) -> dict[str, Any] | None:
        """Return extension dict when an extension block is present in the update."""
        field_name = _EXTENSION_API_FIELD.get(account_kind)
        if field_name is None:
            return None
        nested = getattr(self, field_name, None)
        if nested is None:
            return None
        payload = nested.model_dump(mode="python")
        if field_name == "real_estate_details":
            payload["area_unit"] = parse_area_unit(payload["area_unit"])
            payload["ownership"] = parse_ownership(payload["ownership"])
        return payload


class AccountResponse(BaseModel):
    """Account resource returned by list/detail/create/update endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    account_kind: str
    ledger_side: str
    currency: str
    balance: float = 0.0
    is_active: bool
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    banking_details: BankingDetailsSchema | None = None
    trading_details: TradingDetailsSchema | None = None
    real_estate_details: RealEstateDetailsSchema | None = None
    credit_card_details: CreditCardDetailsSchema | None = None
    loan_details: LoanDetailsSchema | None = None

    @classmethod
    def from_dto(
        cls,
        account: AccountsDTO,
        *,
        balance: float = 0.0,
        extension: AccountDetailsDTO | None = None,
    ) -> AccountResponse:
        """Build an API response from model DTOs."""
        response = cls(
            id=account.id,
            name=account.name,
            account_kind=enum_to_api_slug(account.account_kind),
            ledger_side=enum_to_api_slug(account.ledger_side),
            currency=account.currency,
            balance=balance,
            is_active=bool(account.active),
            opened_at=account.opened_at,
            closed_at=account.closed_at,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )
        if extension is not None:
            _attach_extension(response, account.account_kind, extension)
        return response


class BalanceResponse(BaseModel):
    """Response for ``GET /accounts/{account_id}/balance``."""

    account_id: uuid.UUID
    balance: float
    currency: str
    as_of: datetime | None = None

    @classmethod
    def from_balance_dto(cls, row: AccountBalancesDTO) -> BalanceResponse:
        """Build from ``AccountBalancesDTO``."""
        return cls(
            account_id=row.account_id,
            balance=row.balance,
            currency=row.currency,
            as_of=row.last_activity_ts,
        )


def parse_area_unit(slug: str) -> RealEstateAreaUnit:
    """Convert API slug to ``RealEstateAreaUnit`` (supports ``sq_mt`` style)."""
    normalized = slug.strip().upper().replace("-", "_")
    return RealEstateAreaUnit(normalized)


def parse_ownership(slug: str) -> RealEstateOwnership:
    """Convert API slug to ``RealEstateOwnership``."""
    return RealEstateOwnership(slug.strip().upper())


def extension_api_field(account_kind: AccountKind) -> str | None:
    """Return the JSON field name for an account kind's extension block."""
    return _EXTENSION_API_FIELD.get(account_kind)


def balances_by_account_id(balances_df: pd.DataFrame) -> dict[uuid.UUID, float]:
    """Index balance rows by ``account_id``."""
    if getattr(balances_df, "empty", True):
        return {}
    result: dict[uuid.UUID, float] = {}
    for _, row in balances_df.iterrows():
        account_id = row.get("account_id")
        if account_id is None:
            continue
        result[uuid.UUID(str(account_id))] = float(row.get("balance", 0.0))
    return result


def effective_account_balance(
    account: AccountsDTO,
    *,
    balance_map: dict[uuid.UUID, float] | None = None,
    mv_balance: float | None = None,
) -> float:
    """Resolve display balance: MV row when present, else ``initial_value`` (G8 API semantics).

    Ledger truth lives in ``account_balances``; until an opening transaction is posted
    (#47), accounts with ``initial_value`` and no MV row expose that value in API responses
    per ``modules/api/README.md`` POST /accounts examples.
    """
    if balance_map is not None and account.id in balance_map:
        return balance_map[account.id]
    if mv_balance is not None:
        return float(mv_balance)
    if account.initial_value is not None:
        return float(account.initial_value)
    return 0.0


def paginate_dataframe(df: pd.DataFrame, skip: int, limit: int) -> tuple[pd.DataFrame, int]:
    """Slice a DataFrame for skip/limit pagination."""
    total = len(df)
    if total == 0:
        return df, 0
    return df.iloc[skip : skip + limit], total


def accounts_from_dataframe(df: pd.DataFrame) -> list[AccountsDTO]:
    """Convert an accounts query DataFrame to DTO instances."""
    if getattr(df, "empty", True):
        return []
    dao_type = AccountsDTO.__dao_type__
    accounts: list[AccountsDTO] = []
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        if "Accounts" in row_dict and isinstance(row_dict["Accounts"], dao_type):
            accounts.append(AccountsDTO.from_dao(row_dict["Accounts"]))
            continue
        if len(row_dict) == 1:
            only_value = next(iter(row_dict.values()))
            if isinstance(only_value, dao_type):
                accounts.append(AccountsDTO.from_dao(only_value))
                continue
        accounts.append(AccountsDTO.model_validate(row_dict))
    return accounts


def _attach_extension(response: AccountResponse, account_kind: AccountKind, extension: AccountDetailsDTO) -> None:
    """Set the typed extension field on an ``AccountResponse``."""
    field_name = extension_api_field(account_kind)
    if field_name is None:
        return
    if isinstance(extension, BankingAccountDetailsDTO):
        setattr(
            response, field_name, BankingDetailsSchema(entity=extension.entity, account_number=extension.account_number)
        )
    elif isinstance(extension, TradingAccountDetailsDTO):
        setattr(response, field_name, TradingDetailsSchema(buy_value=extension.buy_value, units=extension.units))
    elif isinstance(extension, RealEstateAccountDetailsDTO):
        setattr(
            response,
            field_name,
            RealEstateDetailsSchema(
                address=extension.address,
                city=extension.city,
                country=extension.country,
                total_area=extension.total_area,
                built_area=extension.built_area,
                area_unit=enum_to_api_slug(extension.area_unit),
                ownership=enum_to_api_slug(extension.ownership),
                participation=extension.participation,
            ),
        )
    elif isinstance(extension, CreditCardAccountDetailsDTO):
        setattr(response, field_name, CreditCardDetailsSchema(credit_limit=extension.credit_limit))
    elif isinstance(extension, LoanAccountDetailsDTO):
        setattr(
            response,
            field_name,
            LoanDetailsSchema(
                is_paid_off=extension.is_paid_off,
                insurance_payment=extension.insurance_payment,
                extras_payment=extension.extras_payment,
            ),
        )
