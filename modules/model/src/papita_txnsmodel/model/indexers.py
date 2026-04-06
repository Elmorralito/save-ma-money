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
from typing import TYPE_CHECKING, Optional, Self, get_args

from pydantic import model_validator
from sqlmodel import Field, Relationship, SQLModel

from papita_txnsmodel.model.assets import ExtendedAssetAccounts
from papita_txnsmodel.model.liabilities import ExtendedLiabilityAccounts

from .constants import (
    ACCOUNTS__TABLENAME,
    ACCOUNTS_INDEXER__TABLENAME,
    ASSET_ACCOUNTS__TABLENAME,
    BANK_CREDIT_LIABILITY_ACCOUNTS__TABLENAME,
    BANKING_ASSET_ACCOUNTS__TABLENAME,
    CREDIT_CARD_LIABILITY_ACCOUNTS__TABLENAME,
    LIABILITY_ACCOUNTS__TABLENAME,
    REAL_ESTATE_ASSET_ACCOUNTS__TABLENAME,
    SCHEMA_NAME,
    TRADING_ASSET_ACCOUNTS__TABLENAME,
    TYPES__TABLENAME,
    USERS__TABLENAME,
    fk_id,
)

if TYPE_CHECKING:
    from .accounts import Accounts
    from .assets import AssetAccounts, BankingAssetAccounts, RealEstateAssetAccounts, TradingAssetAccounts
    from .liabilities import BankCreditLiabilityAccounts, CreditCardLiabilityAccounts, LiabilityAccounts
    from .types import Types
    from .users import Users


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
    __table_args__ = {"schema": SCHEMA_NAME}

    account_id: uuid.UUID = Field(foreign_key=fk_id(ACCOUNTS__TABLENAME), primary_key=True, nullable=False)

    type_id: uuid.UUID = Field(foreign_key=fk_id(TYPES__TABLENAME), nullable=False, index=True)

    owner_id: uuid.UUID = Field(foreign_key=fk_id(USERS__TABLENAME), nullable=False, index=True)

    asset_account_id: Optional[uuid.UUID] = Field(
        foreign_key=fk_id(ASSET_ACCOUNTS__TABLENAME), default=None, nullable=True
    )

    liability_account_id: Optional[uuid.UUID] = Field(
        foreign_key=fk_id(LIABILITY_ACCOUNTS__TABLENAME), default=None, nullable=True
    )

    banking_asset_account_id: uuid.UUID | None = Field(
        foreign_key=fk_id(BANKING_ASSET_ACCOUNTS__TABLENAME), default=None, nullable=True
    )

    real_estate_asset_account_id: uuid.UUID | None = Field(
        foreign_key=fk_id(REAL_ESTATE_ASSET_ACCOUNTS__TABLENAME), default=None, nullable=True
    )

    trading_asset_account_id: uuid.UUID | None = Field(
        foreign_key=fk_id(TRADING_ASSET_ACCOUNTS__TABLENAME), default=None, nullable=True
    )

    bank_credit_liability_account_id: uuid.UUID | None = Field(
        foreign_key=fk_id(BANK_CREDIT_LIABILITY_ACCOUNTS__TABLENAME), default=None, nullable=True
    )

    credit_card_liability_account_id: uuid.UUID | None = Field(
        foreign_key=fk_id(CREDIT_CARD_LIABILITY_ACCOUNTS__TABLENAME), default=None, nullable=True
    )

    accounts: "Accounts" = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME,
        sa_relationship_kwargs={"uselist": False, "foreign_keys": "Accounts.id"},
    )

    types: "Types" = Relationship(back_populates=TYPES__TABLENAME)

    asset_accounts: Optional["AssetAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME,
        sa_relationship_kwargs={"uselist": False, "foreign_keys": "AssetAccounts.id"},
    )

    liability_accounts: Optional["LiabilityAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME,
        sa_relationship_kwargs={"uselist": False, "foreign_keys": "LiabilityAccounts.id"},
    )

    banking_asset_accounts: Optional["BankingAssetAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME,
        sa_relationship_kwargs={"uselist": False, "foreign_keys": "BankingAssetAccounts.id"},
    )

    trading_asset_accounts: Optional["TradingAssetAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME,
        sa_relationship_kwargs={"uselist": False, "foreign_keys": "TradingAssetAccounts.id"},
    )

    real_estate_asset_accounts: Optional["RealEstateAssetAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME,
        sa_relationship_kwargs={"uselist": False, "foreign_keys": "RealEstateAssetAccounts.id"},
    )

    bank_credit_liability_accounts: Optional["BankCreditLiabilityAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME,
        sa_relationship_kwargs={"uselist": False, "foreign_keys": "BankCreditLiabilityAccounts.id"},
    )

    credit_card_liability_accounts: Optional["CreditCardLiabilityAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME,
        sa_relationship_kwargs={"uselist": False, "foreign_keys": "CreditCardLiabilityAccounts.id"},
    )

    owner: "Users" = Relationship(back_populates="owned_accounts_indexer", cascade_delete=True)

    @model_validator(mode="after")
    def _normalize_model(self) -> Self:
        """Normalize the model after initialization."""
        return self.validate_accounts().validate_extended_accounts().validate_linked_accounts()

    def validate_accounts(self) -> Self:
        """Validate base account relationship integrity.

        Ensures that the account must be either an asset or a liability, but not both
        and not neither. This enforces the basic classification constraint for accounts.

        Returns:
            AccountsIndexerDTO: The instance with validated accounts

        Raises:
            ValueError: If both asset and liability are None or if both are set
        """
        match self.asset_account_id, self.liability_account_id:
            case None, None:
                raise ValueError("The index cannot contain empty asset and liability.")
            case _, _:
                raise ValueError("The index cannot contain both asset and liability.")

        return self

    def validate_extended_accounts(self) -> Self:
        """Validate that only one extended account type is specified.

        Ensures that an account cannot be of multiple extended types simultaneously,
        which would violate the account type hierarchy. The method checks all fields
        annotated with extended account types to ensure at most one is set.

        Returns:
            AccountsIndexerDTO: The instance with validated extended accounts

        Raises:
            ValueError: If more than one extended account is set
        """
        extended_account_fields = [
            field_name
            for field_name, info in self.__class__.model_fields.items()
            if ExtendedAssetAccounts in get_args(info.annotation)
            or ExtendedLiabilityAccounts in get_args(info.annotation)
        ]
        extended_accounts_count = sum(1 for field in extended_account_fields if getattr(self, field) is not None)
        if extended_accounts_count > 1:
            raise ValueError("The index cannot contain more than extended account.")

        return self

    def validate_linked_accounts(self) -> Self:
        """Validate that extended accounts match their parent type.

        Ensures that extended accounts (e.g., banking assets) are consistent with their
        base account type (e.g., asset). This prevents incorrect account type linkages
        by checking that any extended account field references an account of the
        appropriate base type.

        Returns:
            AccountsIndexerDTO: The instance with validated linked accounts

        Raises:
            ValueError: If an extended account type doesn't match its parent type
        """
        match self.asset_account, self.liability_account:
            case None, _:
                extended_account_type = ExtendedAssetAccounts
            case _, None:
                extended_account_type = ExtendedLiabilityAccounts

        extended_account_fields = [
            field_name
            for field_name, info in self.__class__.model_fields.items()
            if extended_account_type in get_args(info.annotation)
            or ExtendedLiabilityAccounts in get_args(info.annotation)
        ]
        extended_accounts_count = sum(1 for field in extended_account_fields if getattr(self, field) is not None)
        if extended_accounts_count > 0:
            raise ValueError(f"Extended account is not of type {extended_account_type.__name__}")

        return self
