import datetime
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ARRAY, DECIMAL, TIMESTAMP, Column, SmallInteger, String
from sqlmodel import Field, Relationship

from .base import BaseSQLModel

if TYPE_CHECKING:
    from .accounts import Accounts
    from .types import TransactionCategories


class IdentifiedTransactions(BaseSQLModel, table=True):  # type: ignore

    __tablename__ = "identified_transactions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    category_id: uuid.UUID = Field(foreign_key="transaction_categories.id", nullable=False)
    name: str = Field(nullable=False, index=True)
    tags: List[str] = Field(sa_column=Column(ARRAY(String), nullable=False), min_items=1, unique_items=True)
    description: str = Field(nullable=False)
    planned_value: float = Field(sa_column=Column(DECIMAL[22, 8], nullable=False), gt=0)
    planned_transaction_day: int = Field(sa_column=Column(SmallInteger, nullable=False), gt=0, le=28)

    transaction_categories: "TransactionCategories" = Relationship(back_populates="identified_transactions")
    transactions: List["Transactions"] = Relationship(back_populates="identified_transactions", cascade_delete=True)


class Transactions(BaseSQLModel, table=True):  # type: ignore

    __tablename__ = "transactions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    identified_transaction_id: uuid.UUID | None = Field(
        foreign_key=f"{IdentifiedTransactions.__tablename__}.id", nullable=True
    )
    from_account_id: uuid.UUID | None = Field(foreign_key="accounts.id", default=None, nullable=True)
    to_account_id: uuid.UUID | None = Field(foreign_key="accounts.id", default=None, nullable=True)
    transaction_ts: datetime.datetime = Field(
        sa_column=Column(TIMESTAMP, nullable=False, index=True), default_factory=datetime.datetime.now
    )
    value: float = Field(sa_column=Column(DECIMAL[22, 8], nullable=False), gt=0)

    identified_transactions: "IdentifiedTransactions" = Relationship(back_populates="transactions")
    from_accounts: Optional["Accounts"] = Relationship(
        back_populates="transactions_from_accounts",
        sa_relationship_kwargs={"foreign_keys": "Transactions.from_account_id"},
    )
    to_accounts: Optional["Accounts"] = Relationship(
        back_populates="transactions_to_accounts", sa_relationship_kwargs={"foreign_keys": "Transactions.to_account_id"}
    )
