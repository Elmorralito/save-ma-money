"""Assets module for managing asset accounts in the Papita Transactions system.

This module defines various asset account models including general asset accounts,
banking assets, real estate assets, and trading assets. It provides the structure
for storing different types of assets with their specific attributes and relationships.

Classes:
    AssetAccounts: Base model for all asset accounts in the system.
    BankingAssetAccounts: Model for banking-related asset accounts.
    RealStateAssetAccounts: Model for real estate asset accounts.
    TradingAssetAccounts: Model for trading and investment asset accounts.
"""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DECIMAL, Column, SmallInteger
from sqlmodel import Field, Relationship, SQLModel

from papita_txnsmodel.model.enums import RealStateAssetAccountsAreaUnits, RealStateAssetAccountsOwnership

if TYPE_CHECKING:
    from .accounts import Accounts
    from .liabilities import BankCreditLiabilityAccounts
    from .types import Types


class AssetAccounts(SQLModel, table=True):  # type: ignore
    """Asset accounts model representing financial assets in the system.

    This class defines the structure for asset accounts, which can be linked to
    regular accounts, types, and liability accounts. It serves as the base model
    for more specific asset types like banking, real estate, and trading assets.

    Attributes:
        id (uuid.UUID): Unique identifier for the asset account. Auto-generated UUID.
        account_id (uuid.UUID): Foreign key to the associated account.
        type_id (uuid.UUID): Foreign key to the asset type.
        bank_credit_liability_account_id (uuid.UUID | None): Optional foreign key to a
            bank credit liability account.
        months_per_period (int): Number of months per accounting period. Must be positive.
        initial_value (float | None): Initial monetary value of the asset. Must be positive.
        last_value (float | None): Most recent monetary value of the asset. Must be positive.
        monthly_interest_rate (float | None): Monthly interest rate as a decimal. Must be positive.
        yearly_interest_rate (float | None): Yearly interest rate as a decimal. Must be positive.
        roi (float | None): Return on investment as a decimal. Must be positive.
        periodical_earnings (float | None): Earnings per period. Must be positive.
        accounts (Accounts): Related account information.
        types (Types): Related type information.
        bank_credit_liability_accounts (Optional[BankCreditLiabilityAccounts]): Optional related
            bank credit liability account.
        banking_asset_accounts (Optional[BankingAssetAccounts]): Optional related banking asset
            account details with one-to-one relationship.
        trading_asset_accounts (Optional[TradingAssetAccounts]): Optional related trading asset
            account details with one-to-one relationship.
        real_state_asset_accounts (Optional[RealStateAssetAccounts]): Optional related real estate
            asset account details with one-to-one relationship.
    """

    __tablename__ = "asset_accounts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    account_id: uuid.UUID = Field(foreign_key="accounts.id", nullable=False)
    type_id: uuid.UUID = Field(foreign_key="types.id", nullable=False)
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

    types: "Types" = Relationship(
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
    """Banking asset accounts model for bank-specific asset information.

    This class defines the structure for banking-specific asset accounts, such as
    checking accounts, savings accounts, and certificates of deposit. It extends
    the base asset account with banking-specific attributes.

    Attributes:
        asset_account_id (uuid.UUID): Foreign key to the associated asset account.
            Serves as the primary key.
        entity (str): Name of the banking entity or institution. Indexed for faster lookups.
        account_number (str | None): Optional bank account number. Indexed for faster lookups.
        asset_accounts (AssetAccounts): Related asset account information.
    """

    __tablename__ = "banking_asset_accounts"

    asset_account_id: uuid.UUID = Field(
        foreign_key=f"{AssetAccounts.__tablename__}.id", primary_key=True, nullable=False
    )
    entity: str = Field(nullable=False, index=True)
    account_number: str | None = Field(nullable=True, index=True)

    asset_accounts: AssetAccounts = Relationship(back_populates="banking_asset_accounts")


class RealStateAssetAccounts(SQLModel, table=True):  # type: ignore
    """Real estate asset accounts model for managing real estate-related assets.

    This class defines the structure for real estate asset accounts, including
    properties, land, and other real estate investments. It extends the base
    asset account with real estate-specific attributes.

    Attributes:
        asset_account_id (uuid.UUID): Foreign key to the associated asset account.
            Serves as the primary key.
        address (str): Address of the real estate property.
        city (str): City where the real estate property is located.
        country (str): Country where the real estate property is located.
        total_area (float): Total area of the real estate property. Must be positive.
        built_area (float): Built-up area of the real estate property. Must be positive.
        area_unit (RealStateAssetAccountsAreaUnits): Unit of measurement for the property area.
        ownership (RealStateAssetAccountsOwnership): Type of ownership for the real estate property.
        participation (float): Percentage of ownership in the real estate property. Must be between 0 and 1.
        asset_accounts (AssetAccounts): Related asset account information.
    """

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
    """Trading asset accounts model for managing investment and trading assets.

    This class defines the structure for trading asset accounts, such as stocks,
    bonds, and other investment instruments. It extends the base asset account
    with trading-specific attributes.

    Attributes:
        asset_account_id (uuid.UUID): Foreign key to the associated asset account.
            Serves as the primary key.
        buy_value (float): Purchase value of the trading asset. Must be positive.
        last_value (float | None): Most recent market value of the trading asset. Must be positive.
        units (int): Number of units or shares of the trading asset. Must be positive.
        asset_accounts (AssetAccounts): Related asset account information.
    """

    __tablename__ = "trading_asset_accounts"

    asset_account_id: uuid.UUID = Field(
        foreign_key=f"{AssetAccounts.__tablename__}.id", primary_key=True, nullable=False
    )
    buy_value: float = Field(sa_column=Column(DECIMAL[22, 8], nullable=False), gt=0)
    last_value: float | None = Field(sa_column=Column(DECIMAL[22, 8], nullable=True), default=None, gt=0)
    units: int = Field(sa_column=Column(SmallInteger, nullable=False), default=1, gt=0)

    asset_accounts: AssetAccounts = Relationship(back_populates="trading_asset_accounts")
