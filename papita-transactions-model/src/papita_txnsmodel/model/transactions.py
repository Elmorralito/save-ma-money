"""Transactions module for managing financial transactions in the Papita Transactions system.

This module defines models for tracking financial transactions between accounts and
identified transaction templates. It provides the structure for recording money
movements and their categorization within the system.

Classes:
    IdentifiedTransactions: Model for transaction templates or recurring transactions.
    Transactions: Model for actual financial transactions between accounts.
"""

import datetime
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ARRAY, DECIMAL, TIMESTAMP, Column, SmallInteger, String
from sqlmodel import Field, Relationship

from .base import BaseSQLModel

if TYPE_CHECKING:
    from .accounts import Accounts
    from .types import Types


class IdentifiedTransactions(BaseSQLModel, table=True):  # type: ignore
    """Transaction template model for recurring or planned transactions.

    This class defines the structure for identified transactions, which serve as
    templates or categories for actual transactions. They can represent recurring
    payments, budgeted expenses, or other planned financial activities.

    Attributes:
        id (uuid.UUID): Unique identifier for the identified transaction. Auto-generated UUID.
        type_id (uuid.UUID): Foreign key to the associated transaction type.
        name (str): Name of the identified transaction. Indexed for faster lookups.
        tags (List[str]): List of tags associated with the transaction. Must contain at
            least one tag and all tags must be unique.
        description (str): Detailed description of the identified transaction.
        planned_value (float): Expected monetary value of the transaction. Must be positive.
        planned_transaction_day (int): Day of the month when the transaction is expected
            to occur. Must be between 1 and 28.
        types (Types): Related type information.
        transactions (List[Transactions]): List of actual transactions associated with
            this identified transaction template. One-to-many relationship with cascade delete.
    """

    __tablename__ = "identified_transactions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    type_id: uuid.UUID = Field(foreign_key="types.id", nullable=False)
    name: str = Field(nullable=False, index=True)
    tags: List[str] = Field(sa_column=Column(ARRAY(String), nullable=False), min_items=1, unique_items=True)
    description: str = Field(nullable=False)
    planned_value: float = Field(sa_column=Column(DECIMAL[22, 8], nullable=False), gt=0)
    planned_transaction_day: int = Field(sa_column=Column(SmallInteger, nullable=False), gt=0, le=28)

    types: "Types" = Relationship(back_populates="identified_transactions")
    transactions: List["Transactions"] = Relationship(back_populates="identified_transactions", cascade_delete=True)


class Transactions(BaseSQLModel, table=True):  # type: ignore
    """Financial transaction model representing money movements between accounts.

    This class defines the structure for actual financial transactions, which represent
    the movement of money between accounts or external sources/destinations. Transactions
    can be linked to identified transaction templates for categorization.

    Attributes:
        id (uuid.UUID): Unique identifier for the transaction. Auto-generated UUID.
        identified_transaction_id (uuid.UUID | None): Optional foreign key to an identified
            transaction template.
        from_account_id (uuid.UUID | None): Optional foreign key to the source account.
            Can be null for income transactions from external sources.
        to_account_id (uuid.UUID | None): Optional foreign key to the destination account.
            Can be null for expense transactions to external destinations.
        transaction_ts (datetime.datetime): Timestamp when the transaction occurred.
            Indexed for time-based queries.
        value (float): Monetary value of the transaction. Must be positive.
        identified_transactions (IdentifiedTransactions): Related identified transaction
            template information.
        from_accounts (Optional[Accounts]): Related source account information.
        to_accounts (Optional[Accounts]): Related destination account information.
    """

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
