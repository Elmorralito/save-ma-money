import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import ARRAY, Column, String
from sqlmodel import Field, Relationship

from .base import BaseSQLModel

if TYPE_CHECKING:
    from .assets import AssetAccounts
    from .liabilities import LiabilityAccounts
    from .transactions import IdentifiedTransactions


class AssetAccountTypes(BaseSQLModel, table=True):  # type: ignore

    __tablename__ = "asset_account_types"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False, index=True, unique=True)
    tags: List[str] = Field(sa_column=Column(ARRAY(String), nullable=False), min_items=1, unique_items=True)
    description: str = Field(nullable=False)

    asset_accounts: List["AssetAccounts"] = Relationship(back_populates="asset_account_types", cascade_delete=True)


class LiabilityAccountTypes(BaseSQLModel, table=True):  # type: ignore

    __tablename__ = "liability_account_types"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False, index=True, unique=True)
    tags: List[str] = Field(sa_column=Column(ARRAY(String), nullable=False), min_items=1, unique_items=True)
    description: str = Field(nullable=False)

    liability_accounts: List["LiabilityAccounts"] = Relationship(
        back_populates="liability_account_types", cascade_delete=True
    )


class TransactionCategories(BaseSQLModel, table=True):  # type: ignore

    __tablename__ = "transaction_categories"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False, index=True, unique=True)
    tags: List[str] = Field(sa_column=Column(ARRAY(String), nullable=False), min_items=1, unique_items=True)
    description: str = Field(nullable=False)

    identified_transactions: List["IdentifiedTransactions"] = Relationship(
        back_populates="transaction_categories", cascade_delete=True
    )
