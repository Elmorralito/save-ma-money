"""v3 consolidated accounts model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ARRAY, CHAR, DECIMAL, TIMESTAMP, Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, SmallInteger, String, Text
from sqlmodel import Field, Relationship

from .base import SCHEMA_NAME, BaseSQLModel
from .contstants import ACCOUNTS__TABLENAME, USERS__TABLENAME
from .enums import AccountKind, InterestRateBasis, LedgerSide

if TYPE_CHECKING:
    from .account_details import (
        BankingAccountDetails,
        CreditCardAccountDetails,
        LoanAccountDetails,
        RealEstateAccountDetails,
        TradingAccountDetails,
    )
    from .account_financing import AccountFinancing
    from .transactions import Transactions
    from .users import Users


class Accounts(BaseSQLModel, table=True):  # type: ignore
    """Consolidated financial account (v3)."""

    __tablename__ = ACCOUNTS__TABLENAME
    __table_args__ = (
        Index("ix_accounts_owner_active", "owner_id", "active"),
        {"schema": SCHEMA_NAME},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key=f"{USERS__TABLENAME}.id", nullable=False, index=True)
    name: str = Field(sa_type=String(255), nullable=False, index=True)
    description: str = Field(sa_type=Text, nullable=False, default="")
    tags: List[str] = Field(sa_column=Column(ARRAY(String), nullable=False), default_factory=list)
    account_kind: AccountKind = Field(
        sa_column=Column(
            SAEnum(AccountKind, name="account_kind", schema="papita_transactions", create_type=False),
            nullable=False,
        )
    )
    ledger_side: LedgerSide = Field(
        sa_column=Column(
            SAEnum(LedgerSide, name="ledger_side", schema="papita_transactions", create_type=False),
            nullable=False,
        )
    )
    currency: str = Field(sa_column=Column(CHAR(3), nullable=False), default="USD")
    opened_at: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False, index=True), default_factory=datetime.now)
    closed_at: Optional[datetime] = Field(sa_column=Column(TIMESTAMP, nullable=True, index=True), default=None)
    initial_value: float | None = Field(sa_column=Column(DECIMAL(22, 8), nullable=True), default=None, ge=0)
    current_value: float | None = Field(sa_column=Column(DECIMAL(22, 8), nullable=True), default=None, ge=0)
    current_value_as_of: Optional[datetime] = Field(sa_column=Column(TIMESTAMP, nullable=True), default=None)
    months_per_period: int | None = Field(sa_column=Column(SmallInteger, nullable=True), default=1, gt=0)
    interest_rate: float | None = Field(sa_column=Column(DECIMAL(10, 6), nullable=True), default=None)
    interest_rate_basis: InterestRateBasis | None = Field(
        sa_column=Column(
            SAEnum(InterestRateBasis, name="interest_rate_basis", schema="papita_transactions", create_type=False),
            nullable=True,
        ),
        default=None,
    )
    periodic_payment: float | None = Field(sa_column=Column(DECIMAL(22, 8), nullable=True), default=None)
    total_paid: float | None = Field(sa_column=Column(DECIMAL(22, 8), nullable=True), default=0, ge=0)
    overall_periods: int | None = Field(sa_column=Column(SmallInteger, nullable=True), default=None)
    periods_paid: int | None = Field(sa_column=Column(SmallInteger, nullable=True), default=None)
    closing_day: int | None = Field(sa_column=Column(SmallInteger, nullable=True), default=None, ge=1, le=31)
    roi: float | None = Field(sa_column=Column(DECIMAL(10, 4), nullable=True), default=None)
    periodic_earnings: float | None = Field(sa_column=Column(DECIMAL(22, 8), nullable=True), default=None)

    owner: "Users" = Relationship(back_populates="owned_accounts")
    banking_details: Optional["BankingAccountDetails"] = Relationship(
        back_populates="account", sa_relationship_kwargs={"uselist": False}, cascade_delete=True
    )
    real_estate_details: Optional["RealEstateAccountDetails"] = Relationship(
        back_populates="account", sa_relationship_kwargs={"uselist": False}, cascade_delete=True
    )
    trading_details: Optional["TradingAccountDetails"] = Relationship(
        back_populates="account", sa_relationship_kwargs={"uselist": False}, cascade_delete=True
    )
    credit_card_details: Optional["CreditCardAccountDetails"] = Relationship(
        back_populates="account", sa_relationship_kwargs={"uselist": False}, cascade_delete=True
    )
    loan_details: Optional["LoanAccountDetails"] = Relationship(
        back_populates="account", sa_relationship_kwargs={"uselist": False}, cascade_delete=True
    )
    financing_as_asset: List["AccountFinancing"] = Relationship(
        back_populates="asset_account",
        sa_relationship_kwargs={"foreign_keys": "AccountFinancing.asset_account_id"},
        cascade_delete=True,
    )
    financing_as_loan: List["AccountFinancing"] = Relationship(
        back_populates="loan_account",
        sa_relationship_kwargs={"foreign_keys": "AccountFinancing.loan_account_id"},
        cascade_delete=True,
    )
    transactions_from_accounts: List["Transactions"] = Relationship(
        back_populates="from_accounts",
        sa_relationship_kwargs={"foreign_keys": "Transactions.from_account_id"},
        cascade_delete=True,
    )
    transactions_to_accounts: List["Transactions"] = Relationship(
        back_populates="to_accounts",
        sa_relationship_kwargs={"foreign_keys": "Transactions.to_account_id"},
        cascade_delete=True,
    )
