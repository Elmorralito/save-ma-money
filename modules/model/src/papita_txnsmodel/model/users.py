import uuid
from typing import TYPE_CHECKING, List

from sqlmodel import Field, Relationship

from .base import BaseSQLModel
from .contstants import SCHEMA_NAME, USERS__TABLENAME

if TYPE_CHECKING:
    from .accounts import Accounts
    from .assets import (
        Assets,
        BankingAssetAccounts,
        FinancedAssetAccounts,
        RealEstateAssetAccounts,
        TradingAssetAccounts,
    )
    from .indexers import AccountsIndexer
    from .liabilities import BankCreditLiabilityAccounts, CreditCardLiabilityAccounts, LiabilityAccounts
    from .transactions import IdentifiedTransactions, Transactions
    from .types import Types


class Users(BaseSQLModel, table=True):  # type: ignore
    """Users model."""

    __tablename__ = USERS__TABLENAME

    __table_args__ = {"schema": SCHEMA_NAME}

    id: uuid.UUID = Field(primary_key=True, index=True)
    username: str = Field(nullable=False, index=True, unique=True)
    email: str = Field(nullable=False, index=True, unique=True)
    password: str = Field(nullable=False)

    owned_accounts: List["Accounts"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}, cascade_delete=True
    )
    owned_assets: List["Assets"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}, cascade_delete=True
    )
    owned_financed_asset_accounts: List["FinancedAssetAccounts"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}, cascade_delete=True
    )
    owned_banking_asset_accounts: List["BankingAssetAccounts"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}, cascade_delete=True
    )
    owned_real_estate_asset_accounts: List["RealEstateAssetAccounts"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}, cascade_delete=True
    )
    owned_trading_asset_accounts: List["TradingAssetAccounts"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}, cascade_delete=True
    )
    owned_accounts_indexer: List["AccountsIndexer"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}, cascade_delete=True
    )
    owned_liabilities: List["LiabilityAccounts"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}, cascade_delete=True
    )
    owned_bank_credit_liability_accounts: List["BankCreditLiabilityAccounts"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}, cascade_delete=True
    )
    owned_credit_card_liability_accounts: List["CreditCardLiabilityAccounts"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}, cascade_delete=True
    )
    owned_types: List["Types"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}, cascade_delete=True
    )
    owned_identified_transactions: List["IdentifiedTransactions"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}, cascade_delete=True
    )
    owned_transactions: List["Transactions"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}, cascade_delete=True
    )
