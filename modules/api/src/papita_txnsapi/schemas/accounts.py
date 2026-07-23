"""Account request/response schemas for PPT-036 accounts CRUD.

Maps REST account payloads to ``AccountsDTO`` and kind-specific extension DTOs
from ``papita_txnsmodel``. Extension blocks (banking, trading, real estate,
credit card, loan) are keyed by ``AccountKind`` per the G1 API contract.

Includes helpers for balance resolution, DataFrame pagination, and repository-row
conversion used by ``routers/v1/accounts.py``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator

from papita_txnsapi.config.settings import MAX_DESCRIPTION_LENGTH, MAX_EXTENSION_STRING_LENGTH
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
    """Banking extension fields for checking, savings, and cash accounts.

    Attributes:
        entity: Financial institution or custodian name.
        account_number: Optional masked or full account number.
    """

    model_config = ConfigDict(extra="forbid")

    entity: str = Field(min_length=1, max_length=MAX_EXTENSION_STRING_LENGTH)
    account_number: str | None = Field(default=None, max_length=MAX_EXTENSION_STRING_LENGTH)


class TradingDetailsSchema(BaseModel):
    """Trading extension fields for investment brokerage accounts.

    Attributes:
        buy_value: Positive purchase or cost basis per position unit.
        units: Number of position units held (default 1, must be positive).
    """

    model_config = ConfigDict(extra="forbid")

    buy_value: float = Field(gt=0)
    units: int = Field(default=1, gt=0)


class RealEstateDetailsSchema(BaseModel):
    """Real-estate extension fields.

    Attributes:
        address: Street address of the property.
        city: City or locality.
        country: ISO-style country name or code.
        total_area: Total land area; must be positive.
        built_area: Built or usable area; must be positive.
        area_unit: API slug for area unit (e.g. ``sq_mt``); validated against
            ``RealEstateAreaUnit``.
        ownership: API slug for ownership type; validated against
            ``RealEstateOwnership``.
        participation: Fractional ownership share in (0, 1]; default 1.0.
    """

    model_config = ConfigDict(extra="forbid")

    address: str = Field(min_length=1, max_length=MAX_EXTENSION_STRING_LENGTH)
    city: str = Field(min_length=1, max_length=MAX_EXTENSION_STRING_LENGTH)
    country: str = Field(min_length=1, max_length=MAX_EXTENSION_STRING_LENGTH)
    total_area: float = Field(gt=0)
    built_area: float = Field(gt=0)
    area_unit: str = Field(min_length=1, max_length=64)
    ownership: str = Field(min_length=1, max_length=64)
    participation: float = Field(default=1.0, gt=0, le=1)

    @field_validator("area_unit")
    @classmethod
    def _validate_area_unit(cls, value: str) -> str:
        """Validate and normalize ``area_unit`` against ``RealEstateAreaUnit``.

        Args:
            value: Raw area-unit slug from request JSON.

        Returns:
            The unchanged slug when it maps to a valid enum member.

        Raises:
            ValueError: When the slug is not a recognized area unit.
        """
        parse_area_unit(value)
        return value

    @field_validator("ownership")
    @classmethod
    def _validate_ownership(cls, value: str) -> str:
        """Validate ``ownership`` against ``RealEstateOwnership``.

        Args:
            value: Raw ownership slug from request JSON.

        Returns:
            The unchanged slug when it maps to a valid enum member.

        Raises:
            ValueError: When the slug is not a recognized ownership type.
        """
        parse_ownership(value)
        return value


class CreditCardDetailsSchema(BaseModel):
    """Credit card extension fields.

    Attributes:
        credit_limit: Maximum revolving credit; must be positive.
    """

    model_config = ConfigDict(extra="forbid")

    credit_limit: float = Field(gt=0)


class LoanDetailsSchema(BaseModel):
    """Loan extension fields.

    Attributes:
        is_paid_off: Whether the loan balance has been fully settled.
        insurance_payment: Recurring insurance component of the payment (>= 0).
        extras_payment: Additional recurring fees beyond principal/interest (>= 0).
    """

    model_config = ConfigDict(extra="forbid")

    is_paid_off: bool = False
    insurance_payment: float = Field(default=0, ge=0)
    extras_payment: float = Field(default=0, ge=0)


class AccountCreate(BaseModel):
    """Request body for ``POST /accounts``.

    Exactly one extension block should match ``account_kind``; others are ignored
    by ``extension_payload`` when absent.

    Attributes:
        name: Display name; 1–255 characters after trimming.
        description: Optional free-text description.
        account_kind: Lowercase slug parsed to ``AccountKind``.
        ledger_side: Lowercase slug parsed to ``LedgerSide``.
        currency: ISO 4217 code; defaults to ``USD``.
        initial_value: Optional opening balance before ledger postings (>= 0).
        banking_details: Required shape for checking/savings/cash kinds.
        trading_details: Required shape for investment brokerage kind.
        real_estate_details: Required shape for real-estate kind.
        credit_card_details: Required shape for credit-card kind.
        loan_details: Required shape for loan/mortgage kind.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=MAX_DESCRIPTION_LENGTH)
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
        """Build an ``AccountsDTO`` for the model service layer.

        Args:
            owner_id: Tenant owner UUID from the authenticated session.

        Returns:
            DTO ready for ``AccountsService.create_account``; enums and currency
            are normalized (trimmed name, uppercased currency).

        Raises:
            ValueError: When ``account_kind`` or ``ledger_side`` slugs are invalid.
        """
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
        """Return extension dict for ``AccountsService.create_account``.

        Selects the nested extension block that matches ``account_kind`` and
        converts real-estate slugs to model enums.

        Returns:
            Plain dict for the service ``extension`` argument, or ``None`` when
            the kind has no extension or the matching block was not provided.
        """
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
    """Request body for ``PUT /accounts/{account_id}``.

    All fields are optional; only set fields are merged onto the existing DTO.
    Extension blocks follow the same kind-to-field mapping as ``AccountCreate``.

    Attributes:
        name: New display name; 1–255 characters when provided.
        description: Replacement description text.
        currency: New ISO 4217 code (uppercased on apply).
        initial_value: Updated opening balance hint (>= 0).
        is_active: Soft-active flag; maps to DTO ``active``.
        banking_details: Partial or full banking extension update.
        trading_details: Partial or full trading extension update.
        real_estate_details: Partial or full real-estate extension update.
        credit_card_details: Partial or full credit-card extension update.
        loan_details: Partial or full loan extension update.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    initial_value: float | None = Field(default=None, ge=0)
    is_active: bool | None = None
    banking_details: BankingDetailsSchema | None = None
    trading_details: TradingDetailsSchema | None = None
    real_estate_details: RealEstateDetailsSchema | None = None
    credit_card_details: CreditCardDetailsSchema | None = None
    loan_details: LoanDetailsSchema | None = None

    def apply_to(self, existing: AccountsDTO) -> AccountsDTO:
        """Merge partial update fields onto an existing account DTO.

        Extension blocks and ``is_active`` are excluded from the generic dump;
        ``is_active`` is mapped to ``active`` and currency is uppercased.

        Args:
            existing: Current account row from the repository.

        Returns:
            New ``AccountsDTO`` instance with only supplied fields overwritten.
        """
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
        """Return extension dict when an extension block is present in the update.

        Args:
            account_kind: Resolved kind of the account being updated (not from
                the request body, since kind is immutable on update).

        Returns:
            Plain dict for the service extension upsert, or ``None`` when no
            matching extension block was sent.
        """
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
    """Account resource returned by list, detail, create, and update endpoints.

    Attributes:
        id: Account UUID.
        name: Display name.
        account_kind: Lowercase API slug for ``AccountKind``.
        ledger_side: Lowercase API slug for ``LedgerSide``.
        currency: ISO 4217 code.
        balance: Resolved display balance (MV row or ``initial_value`` per G8).
        is_active: Whether the account is soft-active.
        opened_at: When the account was opened, if recorded.
        closed_at: When the account was closed, if applicable.
        created_at: Row creation timestamp.
        updated_at: Last modification timestamp.
        banking_details: Present for banking-backed kinds when loaded.
        trading_details: Present for brokerage kinds when loaded.
        real_estate_details: Present for real-estate kinds when loaded.
        credit_card_details: Present for credit-card kinds when loaded.
        loan_details: Present for loan kinds when loaded.
    """

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
        """Build an API response from model DTOs.

        Args:
            account: Core account row from the repository.
            balance: Pre-resolved display balance for the response.
            extension: Optional kind-specific details DTO to attach.

        Returns:
            Serialized account with enum slugs and optional extension nested object.
        """
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
    """Response for ``GET /accounts/{account_id}/balance``.

    Attributes:
        account_id: UUID of the queried account.
        balance: Ledger or materialized balance amount.
        currency: Balance currency code.
        as_of: Timestamp of the last balance activity, when available.
    """

    account_id: uuid.UUID
    balance: float
    currency: str
    as_of: datetime | None = None

    @classmethod
    def from_balance_dto(cls, row: AccountBalancesDTO) -> BalanceResponse:
        """Build from ``AccountBalancesDTO``.

        Args:
            row: Balance snapshot row from the model layer.

        Returns:
            API balance payload with ``as_of`` mapped from ``last_activity_ts``.
        """
        return cls(
            account_id=row.account_id,
            balance=row.balance,
            currency=row.currency,
            as_of=row.last_activity_ts,
        )


def parse_area_unit(slug: str) -> RealEstateAreaUnit:
    """Convert API slug to ``RealEstateAreaUnit`` (supports ``sq_mt`` style).

    Args:
        slug: Area-unit slug from JSON; hyphens are normalized to underscores.

    Returns:
        Matching ``RealEstateAreaUnit`` member.

    Raises:
        ValueError: When the normalized slug is not a valid enum value.
    """
    normalized = slug.strip().upper().replace("-", "_")
    return RealEstateAreaUnit(normalized)


def parse_ownership(slug: str) -> RealEstateOwnership:
    """Convert API slug to ``RealEstateOwnership``.

    Args:
        slug: Ownership slug from JSON.

    Returns:
        Matching ``RealEstateOwnership`` member.

    Raises:
        ValueError: When the slug is not a valid enum value.
    """
    return RealEstateOwnership(slug.strip().upper())


def extension_api_field(account_kind: AccountKind) -> str | None:
    """Return the JSON field name for an account kind's extension block.

    Args:
        account_kind: Resolved account kind enum member.

    Returns:
        Request/response attribute name (e.g. ``banking_details``), or ``None``
        when the kind has no extension table.
    """
    return _EXTENSION_API_FIELD.get(account_kind)


def balances_by_account_id(balances_df: pd.DataFrame) -> dict[uuid.UUID, float]:
    """Index balance rows by ``account_id``.

    Args:
        balances_df: DataFrame from a balances query; may be empty.

    Returns:
        Mapping of account UUID to numeric balance; empty dict when input is empty
        or rows lack ``account_id``.
    """
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
    """Resolve display balance: MV row when present, else ``initial_value`` (G8).

    Ledger truth lives in ``account_balances``; until an opening transaction is
    posted (#47), accounts with ``initial_value`` and no MV row expose that value
    in API responses per ``modules/api/README.md`` POST /accounts examples.

    Args:
        account: Account DTO whose balance is being resolved.
        balance_map: Optional pre-indexed balances from ``balances_by_account_id``.
        mv_balance: Optional single MV balance when already fetched for this account.

    Returns:
        Numeric balance for API serialization; ``0.0`` when no source is available.
    """
    if balance_map is not None and account.id in balance_map:
        return balance_map[account.id]
    if mv_balance is not None:
        return float(mv_balance)
    if account.initial_value is not None:
        return float(account.initial_value)
    return 0.0


def paginate_dataframe(df: pd.DataFrame, skip: int, limit: int) -> tuple[pd.DataFrame, int]:
    """Slice a DataFrame for skip/limit pagination.

    Args:
        df: Full result set before pagination.
        skip: Number of leading rows to omit.
        limit: Maximum rows to include in the page.

    Returns:
        Tuple of (page slice, total row count). When empty, returns the original
        frame and total ``0``.
    """
    total = len(df)
    if total == 0:
        return df, 0
    return df.iloc[skip : skip + limit], total


def accounts_from_dataframe(df: pd.DataFrame) -> list[AccountsDTO]:
    """Convert an accounts query DataFrame to DTO instances.

    Handles repository row shapes: nested ``Accounts`` DAO column, single DAO
    column, or flat dict rows validated by Pydantic.

    Args:
        df: DataFrame from ``AccountRepository`` query methods.

    Returns:
        List of ``AccountsDTO`` instances; empty list when the frame is empty.
    """
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
    """Set the typed extension field on an ``AccountResponse``.

    Mutates ``response`` in place by selecting the correct nested schema for
    ``account_kind`` and mapping enum fields to API slugs for real estate.

    Args:
        response: Partially built response awaiting extension attachment.
        account_kind: Kind used to choose the JSON field name.
        extension: Kind-specific details DTO from the repository.

    Returns:
        None. The matching ``*_details`` attribute on ``response`` is populated.
    """
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
