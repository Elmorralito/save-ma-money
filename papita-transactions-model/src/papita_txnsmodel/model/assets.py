import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DECIMAL, Column, SmallInteger
from sqlmodel import Field, Relationship, SQLModel

from papita_txnsmodel.model.enums import RealStateAssetAccountsAreaUnits, RealStateAssetAccountsOwnership

if TYPE_CHECKING:
    from .accounts import Accounts
    from .liabilities import BankCreditLiabilityAccounts
    from .types import AssetAccountTypes


class AssetAccounts(SQLModel, table=True):  # type: ignore

    __tablename__ = "asset_accounts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    account_id: uuid.UUID = Field(foreign_key="accounts.id", nullable=False)
    account_type_id: uuid.UUID = Field(foreign_key="asset_account_types.id", nullable=False)
    bank_credit_liability_account_id: uuid.UUID | None = Field(
        foreign_key="bank_credit_liability_accounts.liability_account_id", default=None, nullable=True
    )
    months_per_period: int = Field(sa_column=Column(SmallInteger, nullable=False), default=1, gt=0)
    initial_value: float | None = Field(sa_column=Column(DECIMAL[22, 8], nullable=True), default=None, gt=0)
    last_value: float | None = Field(sa_column=Column(DECIMAL[22, 8], nullable=True), default=None, gt=0)
    monthly_interest_rate: float | None = Field(sa_column=Column(DECIMAL[10, 4], nullable=True), default=None, gt=0)
    yearly_interest_rate: float | None = Field(sa_column=Column(DECIMAL[10, 4], nullable=True), default=None, gt=0)
    roi: float | None = Field(sa_column=Column(DECIMAL[10, 4], nullable=True), default=None, gt=0)
    periodical_earnings: float | None = Field(sa_column=Column(DECIMAL[22, 8], nullable=True), default=None, gt=0)

    accounts: "Accounts" = Relationship(
        back_populates="asset_accounts",
    )

    asset_account_types: "AssetAccountTypes" = Relationship(
        back_populates="asset_accounts",
    )

    bank_credit_liability_accounts: Optional["BankCreditLiabilityAccounts"] = Relationship(
        back_populates="asset_accounts"
    )
    banking_asset_accounts: Optional["BankingAssetAccounts"] = Relationship(
        back_populates="asset_accounts", sa_relationship_kwargs={"uselist": False}, cascade_delete=True
    )
    trading_asset_accounts: Optional["TradingAssetAccounts"] = Relationship(
        back_populates="asset_accounts", sa_relationship_kwargs={"uselist": False}, cascade_delete=True
    )
    real_state_asset_accounts: Optional["RealStateAssetAccounts"] = Relationship(
        back_populates="asset_accounts", sa_relationship_kwargs={"uselist": False}, cascade_delete=True
    )


class BankingAssetAccounts(SQLModel, table=True):  # type: ignore

    __tablename__ = "banking_asset_accounts"

    asset_account_id: uuid.UUID = Field(
        foreign_key=f"{AssetAccounts.__tablename__}.id", primary_key=True, nullable=False
    )
    entity: str = Field(nullable=False, index=True)
    account_number: str | None = Field(nullable=True, index=True)

    asset_accounts: AssetAccounts = Relationship(back_populates="banking_asset_accounts")


class RealStateAssetAccounts(SQLModel, table=True):  # type: ignore

    __tablename__ = "real_state_asset_accounts"

    asset_account_id: uuid.UUID = Field(
        foreign_key=f"{AssetAccounts.__tablename__}.id", primary_key=True, nullable=False
    )

    address: str = Field(nullable=False)
    city: str = Field(nullable=False)
    country: str = Field(nullable=False)
    total_area: float = Field(sa_column=Column(DECIMAL[12, 4], nullable=False), gt=0)
    built_area: float = Field(sa_column=Column(DECIMAL[12, 4], nullable=False), gt=0)
    area_unit: RealStateAssetAccountsAreaUnits = Field(default=RealStateAssetAccountsAreaUnits.SQ_MT)
    ownership: RealStateAssetAccountsOwnership = Field(default=RealStateAssetAccountsOwnership.FULL)
    participation: float = Field(sa_column=Column(DECIMAL[4, 4], nullable=False), gt=0, le=1, default=1.0)

    asset_accounts: AssetAccounts = Relationship(back_populates="real_state_asset_accounts")


class TradingAssetAccounts(SQLModel, table=True):  # type: ignore

    __tablename__ = "trading_asset_accounts"

    asset_account_id: uuid.UUID = Field(
        foreign_key=f"{AssetAccounts.__tablename__}.id", primary_key=True, nullable=False
    )
    buy_value: float = Field(sa_column=Column(DECIMAL[22, 8], nullable=False), gt=0)
    last_value: float | None = Field(sa_column=Column(DECIMAL[22, 8], nullable=True), default=None, gt=0)
    units: int = Field(sa_column=Column(SmallInteger, nullable=False), default=1, gt=0)

    asset_accounts: AssetAccounts = Relationship(back_populates="trading_asset_accounts")
