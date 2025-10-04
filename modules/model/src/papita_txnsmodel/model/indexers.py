"""Account indexing module for the Papita Transaction Model.

This module defines the AccountsIndexer model, which serves as a central hub for
connecting various types of financial accounts within the system. It provides an
indexing mechanism that links together different account types (assets, liabilities,
banking accounts, etc.) through foreign key relationships, enabling efficient
querying and navigation across the account hierarchy.

The AccountsIndexer maintains references to all specialized account types, allowing
the system to treat accounts polymorphically while preserving the ability to access
their type-specific attributes.
"""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

from .contstants import (
    ACCOUNTS__TABLENAME,
    ACCOUNTS_INDEXER__TABLENAME,
    ASSET_ACCOUNTS__TABLENAME,
    BANK_CREDIT_LIABILITY_ACCOUNTS__TABLENAME,
    BANKING_ASSET_ACCOUNTS__TABLENAME,
    CREDIT_CARD_LIABILITY_ACCOUNTS__TABLENAME,
    LIABILITY_ACCOUNTS__TABLENAME,
    REAL_ESTATE_ASSET_ACCOUNTS__TABLENAME,
    TRADING_ASSET_ACCOUNTS__TABLENAME,
    TYPES__TABLENAME,
)

if TYPE_CHECKING:
    from .accounts import Accounts
    from .assets import AssetAccounts, BankingAssetAccounts, RealEstateAssetAccounts, TradingAssetAccounts
    from .liabilities import BankCreditLiabilityAccounts, CreditCardLiabilityAccounts, LiabilityAccounts
    from .types import Types


class AccountsIndexer(SQLModel, table=True):  # type: ignore
    """Centralized indexer that maintains relationships between different account types.

    This model serves as the main indexing table that connects base accounts to their
    specialized implementations. Each row represents a single account with references
    to its various type-specific representations across the system. The design allows
    for polymorphic account handling while maintaining strong relational integrity.

    The indexer stores foreign keys to all possible account specializations, with only
    the relevant ones being populated based on the account's type. This structure enables
    efficient querying by account type and provides a unified way to navigate the account
    hierarchy regardless of the specific account subtype.

    Attributes:
        account_id: Primary key and foreign key to the base Accounts table.
        type_id: Foreign key reference to the account's type.
        asset_account_id: Optional reference to an asset account.
        liability_account_id: Optional reference to a liability account.
        banking_asset_account_id: Optional reference to a banking asset account.
        real_estate_asset_account_id: Optional reference to a real estate asset account.
        trading_asset_account_id: Optional reference to a trading asset account.
        bank_credit_liability_account_id: Optional reference to a bank credit liability account.
        credit_card_liability_account_id: Optional reference to a credit card liability account.
        accounts: Relationship to the base Accounts model.
        types: Relationship to the Types model.
        asset_accounts: One-to-one relationship to AssetAccounts.
        liability_accounts: One-to-one relationship to LiabilityAccounts.
        banking_asset_accounts: One-to-one relationship to BankingAssetAccounts.
        trading_asset_accounts: One-to-one relationship to TradingAssetAccounts.
        real_estate_asset_accounts: One-to-one relationship to RealEstateAssetAccounts.
        bank_credit_liability_accounts: One-to-one relationship to BankCreditLiabilityAccounts.
        credit_card_liability_accounts: One-to-one relationship to CreditCardLiabilityAccounts.
    """

    __tablename__ = ACCOUNTS_INDEXER__TABLENAME

    account_id: uuid.UUID = Field(foreign_key=f"{ACCOUNTS__TABLENAME}.id", primary_key=True, nullable=False)

    type_id: uuid.UUID = Field(foreign_key=f"{TYPES__TABLENAME}.id", nullable=False)

    asset_account_id: Optional[uuid.UUID] = Field(
        foreign_key=f"{ASSET_ACCOUNTS__TABLENAME}.id", default=None, nullable=True
    )

    liability_account_id: Optional[uuid.UUID] = Field(
        foreign_key=f"{LIABILITY_ACCOUNTS__TABLENAME}.id", default=None, nullable=True
    )

    banking_asset_account_id: uuid.UUID | None = Field(
        foreign_key=f"{BANKING_ASSET_ACCOUNTS__TABLENAME}.id", default=None, nullable=True
    )

    real_estate_asset_account_id: uuid.UUID | None = Field(
        foreign_key=f"{REAL_ESTATE_ASSET_ACCOUNTS__TABLENAME}.id", default=None, nullable=True
    )

    trading_asset_account_id: uuid.UUID | None = Field(
        foreign_key=f"{TRADING_ASSET_ACCOUNTS__TABLENAME}.id", default=None, nullable=True
    )

    bank_credit_liability_account_id: uuid.UUID | None = Field(
        foreign_key=f"{BANK_CREDIT_LIABILITY_ACCOUNTS__TABLENAME}.id", default=None, nullable=True
    )

    credit_card_liability_account_id: uuid.UUID | None = Field(
        foreign_key=f"{CREDIT_CARD_LIABILITY_ACCOUNTS__TABLENAME}.id", default=None, nullable=True
    )

    accounts: "Accounts" = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME, sa_relationship_kwargs={"uselist": False}
    )

    types: "Types" = Relationship(back_populates=TYPES__TABLENAME)

    asset_accounts: Optional["AssetAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME,
        sa_relationship_kwargs={"uselist": False},
    )

    liability_accounts: Optional["LiabilityAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME, sa_relationship_kwargs={"uselist": False}
    )

    banking_asset_accounts: Optional["BankingAssetAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME, sa_relationship_kwargs={"uselist": False}
    )

    trading_asset_accounts: Optional["TradingAssetAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME, sa_relationship_kwargs={"uselist": False}
    )

    real_estate_asset_accounts: Optional["RealEstateAssetAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME, sa_relationship_kwargs={"uselist": False}
    )

    bank_credit_liability_accounts: Optional["BankCreditLiabilityAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME, sa_relationship_kwargs={"uselist": False}
    )

    credit_card_liability_accounts: Optional["CreditCardLiabilityAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME, sa_relationship_kwargs={"uselist": False}
    )
