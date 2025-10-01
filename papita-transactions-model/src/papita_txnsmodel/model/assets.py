"""Assets module for managing asset accounts in the Papita Transactions system.

This module defines various asset account models including general asset accounts,
banking assets, real estate assets, and trading assets. It provides the structure
for storing different types of assets with their specific attributes and relationships.

Classes:
    AssetAccounts: Base model for all asset accounts in the system.
    BankingAssetAccounts: Model for banking-related asset accounts.
    RealEstateAssetAccounts: Model for real estate asset accounts.
    TradingAssetAccounts: Model for trading and investment asset accounts.
"""

import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import DECIMAL, Column, SmallInteger
from sqlmodel import Field, Relationship

from .base import BaseSQLModel
from .contstants import (
    ASSET_ACCOUNTS__TABLENAME,
    BANK_CREDIT_LIABILITY_ACCOUNTS__TABLENAME,
    BANKING_ASSET_ACCOUNTS__TABLENAME,
    FINANCED_ASSET_ACCOUNTS__TABLENAME,
    REAL_ESTATE_ASSET_ACCOUNTS__TABLENAME,
    TRADING_ASSET_ACCOUNTS__TABLENAME,
)
from .enums import RealEstateAssetAccountsAreaUnits, RealEstateAssetAccountsOwnership

if TYPE_CHECKING:
    from .indexers import AccountsIndexer
    from .liabilities import BankCreditLiabilityAccounts


class AssetAccounts(BaseSQLModel, table=True):  # type: ignore
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
        real_state_asset_accounts (Optional[RealEstateAssetAccounts]): Optional related real estate
            asset account details with one-to-one relationship.
    """

    __tablename__ = ASSET_ACCOUNTS__TABLENAME

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    months_per_period: int = Field(sa_column=Column(SmallInteger, nullable=False), default=1, gt=0)
    initial_value: float | None = Field(sa_column=Column(DECIMAL[22, 8], nullable=True), default=None, gt=0)
    last_value: float | None = Field(sa_column=Column(DECIMAL[22, 8], nullable=True), default=None, gt=0)
    monthly_interest_rate: float | None = Field(sa_column=Column(DECIMAL[10, 4], nullable=True), default=None, gt=0)
    yearly_interest_rate: float | None = Field(sa_column=Column(DECIMAL[10, 4], nullable=True), default=None, gt=0)
    roi: float | None = Field(sa_column=Column(DECIMAL[10, 4], nullable=True), default=None, gt=0)
    periodical_earnings: float | None = Field(sa_column=Column(DECIMAL[22, 8], nullable=True), default=None, gt=0)

    accounts_indexer: "AccountsIndexer" = Relationship(
        back_populates=ASSET_ACCOUNTS__TABLENAME, sa_relationship_kwargs={"uselist": False}, cascade_delete=True
    )

    financed_asset_accounts: List["FinancedAssetAccounts"] = Relationship(
        back_populates=ASSET_ACCOUNTS__TABLENAME, cascade_delete=True
    )


class ExtendedAssetAccounts(BaseSQLModel):

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


class FinancedAssetAccounts(BaseSQLModel, table=True):  # type: ignore

    __tablename__ = FINANCED_ASSET_ACCOUNTS__TABLENAME

    bank_credit_liability_account_id: uuid.UUID = Field(
        foreign_key=f"{BANK_CREDIT_LIABILITY_ACCOUNTS__TABLENAME}.id", primary_key=True
    )

    asset_account_id: uuid.UUID = Field(foreign_key=f"{ASSET_ACCOUNTS__TABLENAME}.id", nullable=False)

    financing_share: float = Field(sa_column=Column(DECIMAL[4, 4], nullable=False), default=1.0, le=1, gt=0)

    bank_credit_liability_accounts: "BankCreditLiabilityAccounts" = Relationship(
        back_populates=FINANCED_ASSET_ACCOUNTS__TABLENAME, sa_relationship_kwargs={"uselist": False}
    )

    asset_accounts: AssetAccounts = Relationship(back_populates=FINANCED_ASSET_ACCOUNTS__TABLENAME)


class BankingAssetAccounts(ExtendedAssetAccounts, table=True):  # type: ignore
    """Banking asset accounts model for bank-specific asset information.

    This class defines the structure for banking-specific asset accounts, such as
    checking accounts, savings accounts, and certificates of deposit. It extends
    the base asset account with banking-specific attributes.

    Attributes:
        asset_account_id (uuid.UUID): Foreign key to the associated asset account.
            Serves as the primary key.
        entity (str): Name of the banking entity or institution. Indexed for faster lookups.
        account_number (str | None): Optional bank account number. Indexed for faster lookups.
    """

    __tablename__ = BANKING_ASSET_ACCOUNTS__TABLENAME

    entity: str = Field(nullable=False, index=True)
    account_number: str | None = Field(nullable=True, index=True)

    accounts_indexer: "AccountsIndexer" = Relationship(
        back_populates=BANKING_ASSET_ACCOUNTS__TABLENAME,
        sa_relationship_kwargs={"uselist": False},
        cascade_delete=False,
    )


class RealEstateAssetAccounts(ExtendedAssetAccounts, table=True):  # type: ignore
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
        area_unit (RealEstateAssetAccountsAreaUnits): Unit of measurement for the property area.
        ownership (RealEstateAssetAccountsOwnership): Type of ownership for the real estate property.
        participation (float): Percentage of ownership in the real estate property. Must be between 0 and 1.
    """

    __tablename__ = REAL_ESTATE_ASSET_ACCOUNTS__TABLENAME

    address: str = Field(nullable=False)
    city: str = Field(nullable=False)
    country: str = Field(nullable=False)
    total_area: float = Field(sa_column=Column(DECIMAL[12, 4], nullable=False), gt=0)
    built_area: float = Field(sa_column=Column(DECIMAL[12, 4], nullable=False), gt=0)
    area_unit: RealEstateAssetAccountsAreaUnits = Field(default=RealEstateAssetAccountsAreaUnits.SQ_MT)
    ownership: RealEstateAssetAccountsOwnership = Field(default=RealEstateAssetAccountsOwnership.FULL)
    participation: float = Field(sa_column=Column(DECIMAL[4, 4], nullable=False), gt=0, le=1, default=1.0)

    accounts_indexer: "AccountsIndexer" = Relationship(
        back_populates=REAL_ESTATE_ASSET_ACCOUNTS__TABLENAME,
        sa_relationship_kwargs={"uselist": False},
        cascade_delete=False,
    )


class TradingAssetAccounts(ExtendedAssetAccounts, table=True):  # type: ignore
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
    """

    __tablename__ = TRADING_ASSET_ACCOUNTS__TABLENAME

    buy_value: float = Field(sa_column=Column(DECIMAL[22, 8], nullable=False), gt=0)
    last_value: float | None = Field(sa_column=Column(DECIMAL[22, 8], nullable=True), default=None, gt=0)
    units: int = Field(sa_column=Column(SmallInteger, nullable=False), default=1, gt=0)

    accounts_indexer: "AccountsIndexer" = Relationship(
        back_populates=TRADING_ASSET_ACCOUNTS__TABLENAME,
        sa_relationship_kwargs={"uselist": False},
        cascade_delete=False,
    )
