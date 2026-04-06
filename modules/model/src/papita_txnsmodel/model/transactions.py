"""Transactions module for managing financial transactions in the Papita Transactions system.

This module defines models for tracking financial transactions between accounts and
identified transaction templates. It provides the structure for recording money
movements and their categorization within the system.

Classes:
    IdentifiedTransactions: Model for transaction templates or recurring transactions.
    Transactions: Model for actual financial transactions between accounts.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional, Self

from pydantic import model_validator
from sqlalchemy import DECIMAL, TIMESTAMP, Column, SmallInteger, Text
from sqlmodel import Field, Relationship

from papita_txnsmodel.utils.modelutils import URLStr

from .base import BaseSQLModel, CoreTableSQLModel
from .constants import (
    ACCOUNTS__TABLENAME,
    IDENTIFIED_TRANSACTIONS__TABLENAME,
    TRANSACTIONS__TABLENAME,
    TYPES__TABLENAME,
    USERS__TABLENAME,
    fk_id,
)

if TYPE_CHECKING:
    from .accounts import Accounts
    from .types import Types
    from .users import Users


class IdentifiedTransactions(CoreTableSQLModel, table=True):  # type: ignore
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

    __tablename__ = IDENTIFIED_TRANSACTIONS__TABLENAME

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    type_id: uuid.UUID = Field(foreign_key=fk_id(TYPES__TABLENAME), nullable=False)
    icon: URLStr | None = Field(sa_column=Column(Text, nullable=True, index=False, unique=False), default=None)
    planned_value: float = Field(sa_column=Column(DECIMAL[22, 8], nullable=False), gt=0)
    planned_transaction_day: int = Field(sa_column=Column(SmallInteger, nullable=False), gt=0, le=28)
    owner_id: uuid.UUID = Field(foreign_key=fk_id(USERS__TABLENAME), nullable=False)

    owner: "Users" = Relationship(back_populates="owned_identified_transactions")

    types: "Types" = Relationship(back_populates=IDENTIFIED_TRANSACTIONS__TABLENAME)
    transactions: List["Transactions"] = Relationship(
        back_populates=IDENTIFIED_TRANSACTIONS__TABLENAME, cascade_delete=True
    )


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
        transaction_ts (datetime): Timestamp when the transaction occurred.
            Indexed for time-based queries.
        value (float): Monetary value of the transaction. Must be positive.
        identified_transactions (IdentifiedTransactions): Related identified transaction
            template information.
        from_accounts (Optional[Accounts]): Related source account information.
        to_accounts (Optional[Accounts]): Related destination account information.
    """

    __tablename__ = TRANSACTIONS__TABLENAME

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False, index=True)
    icon: URLStr | None = Field(sa_column=Column(Text, nullable=True, index=False, unique=False), default=None)
    identified_transaction_id: uuid.UUID | None = Field(
        foreign_key=fk_id(IDENTIFIED_TRANSACTIONS__TABLENAME), nullable=True
    )
    from_account_id: uuid.UUID | None = Field(foreign_key=fk_id(ACCOUNTS__TABLENAME), default=None, nullable=True)
    to_account_id: uuid.UUID | None = Field(foreign_key=fk_id(ACCOUNTS__TABLENAME), default=None, nullable=True)
    transaction_ts: datetime = Field(
        sa_column=Column(TIMESTAMP, nullable=False, index=True), default_factory=datetime.now
    )
    value: float = Field(sa_column=Column(DECIMAL[22, 8], nullable=False), gt=0)
    owner_id: uuid.UUID = Field(foreign_key=fk_id(USERS__TABLENAME), nullable=False, index=True)

    owner: "Users" = Relationship(back_populates="owned_transactions")

    identified_transactions: "IdentifiedTransactions" = Relationship(back_populates=TRANSACTIONS__TABLENAME)
    from_accounts: Optional["Accounts"] = Relationship(
        back_populates="transactions_from_accounts",
        sa_relationship_kwargs={"foreign_keys": "Transactions.from_account_id"},
    )
    to_accounts: Optional["Accounts"] = Relationship(
        back_populates="transactions_to_accounts", sa_relationship_kwargs={"foreign_keys": "Transactions.to_account_id"}
    )

    @model_validator(mode="after")
    def _normalize_model(self) -> Self:
        """Normalize the model after initialization."""
        super()._normalize_model()
        if self.transaction_ts and self.transaction_ts.tzinfo != timezone.utc:
            self.transaction_ts = self.transaction_ts.astimezone(timezone.utc)

        if not self.from_account_id and not self.to_account_id:
            raise ValueError("The transaction must have at least one account")

        if self.from_account_id == self.to_account_id:
            raise ValueError("The transaction must have different accounts")

        return self
