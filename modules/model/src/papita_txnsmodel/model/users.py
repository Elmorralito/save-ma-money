import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from pydantic import EmailStr, SecretStr
from sqlalchemy import JSON, Column, String, Text
from sqlmodel import Field, Relationship

from papita_txnsmodel.utils.modelutils import URLStr

from .base import BaseSQLModel
from .constants import USERS__TABLENAME

if TYPE_CHECKING:
    from .accounts import Accounts
    from .assets import (
        AssetAccounts,
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

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    username: SecretStr = Field(sa_column=Column(String, nullable=False, index=True, unique=True))
    email: EmailStr = Field(nullable=False, index=True, unique=True)
    password: SecretStr = Field(sa_column=Column(String, nullable=False))
    admin: bool = Field(nullable=False, default=False)
    avatar: URLStr | None = Field(sa_column=Column(Text, nullable=True, index=False, unique=False), default=None)

    # Password algorithm and parameters
    hashing_algorithm: str = Field(nullable=False, default="argon2")
    hashing_algorithm_parameters: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    hashing_algorithm_salt: str = Field(nullable=False, default_factory=lambda: uuid.uuid4().hex)
    hashing_algorithm_module: str | None = Field(nullable=True, default=None)
    password_locked_until: datetime | None = Field(nullable=True, default=None)

    owned_accounts: List["Accounts"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"foreign_keys": "Accounts.owner_id"}, cascade_delete=True
    )
    owned_assets: List["AssetAccounts"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"foreign_keys": "AssetAccounts.owner_id"}, cascade_delete=True
    )
    owned_financed_asset_accounts: List["FinancedAssetAccounts"] = Relationship(
        back_populates="owner",
        sa_relationship_kwargs={"foreign_keys": "FinancedAssetAccounts.owner_id"},
        cascade_delete=True,
    )
    owned_banking_asset_accounts: List["BankingAssetAccounts"] = Relationship(
        back_populates="owner",
        sa_relationship_kwargs={"foreign_keys": "BankingAssetAccounts.owner_id"},
        cascade_delete=True,
    )
    owned_real_estate_asset_accounts: List["RealEstateAssetAccounts"] = Relationship(
        back_populates="owner",
        sa_relationship_kwargs={"foreign_keys": "RealEstateAssetAccounts.owner_id"},
        cascade_delete=True,
    )
    owned_trading_asset_accounts: List["TradingAssetAccounts"] = Relationship(
        back_populates="owner",
        sa_relationship_kwargs={"foreign_keys": "TradingAssetAccounts.owner_id"},
        cascade_delete=True,
    )
    owned_accounts_indexer: List["AccountsIndexer"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"foreign_keys": "AccountsIndexer.owner_id"}, cascade_delete=True
    )
    owned_liabilities: List["LiabilityAccounts"] = Relationship(
        back_populates="owner",
        sa_relationship_kwargs={"foreign_keys": "LiabilityAccounts.owner_id"},
        cascade_delete=True,
    )
    owned_bank_credit_liability_accounts: List["BankCreditLiabilityAccounts"] = Relationship(
        back_populates="owner",
        sa_relationship_kwargs={"foreign_keys": "BankCreditLiabilityAccounts.owner_id"},
        cascade_delete=True,
    )
    owned_credit_card_liability_accounts: List["CreditCardLiabilityAccounts"] = Relationship(
        back_populates="owner",
        sa_relationship_kwargs={"foreign_keys": "CreditCardLiabilityAccounts.owner_id"},
        cascade_delete=True,
    )
    owned_types: List["Types"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"foreign_keys": "Types.owner_id"}, cascade_delete=True
    )
    owned_identified_transactions: List["IdentifiedTransactions"] = Relationship(
        back_populates="owner",
        sa_relationship_kwargs={"foreign_keys": "IdentifiedTransactions.owner_id"},
        cascade_delete=True,
    )
    owned_transactions: List["Transactions"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"foreign_keys": "Transactions.owner_id"}, cascade_delete=True
    )
