"""Accounts module for managing financial account entities in the Papita Transactions system.

This module defines the Accounts model which represents financial accounts in the system.
It provides the structure for storing account information and establishes relationships
with assets, liabilities, and transactions.

Classes:
    Accounts: Represents a financial account in the system.
"""

import uuid
from datetime import datetime as builtin_datetime
from typing import TYPE_CHECKING, List, Self

from pydantic import model_validator
from sqlalchemy import TIMESTAMP, Text
from sqlmodel import Column, Field, Relationship

from papita_txnsmodel.utils import modelutils
from papita_txnsmodel.utils.modelutils import URLStr

from .base import CoreTableSQLModel
from .constants import ACCOUNTS__TABLENAME, SCHEMA_NAME, USERS__TABLENAME, fk_id

if TYPE_CHECKING:
    from .indexers import AccountsIndexer
    from .transactions import Transactions
    from .users import Users


class Accounts(CoreTableSQLModel, table=True):  # type: ignore
    """Financial account model representing accounts in the Papita Transactions system.

    This class defines the structure for financial accounts, which can be linked to
    assets, liabilities, and transactions. Accounts serve as the fundamental entities
    for tracking financial activities within the system.

    Attributes:
        id (uuid.UUID): Unique identifier for the account. Auto-generated UUID.
        name (str): Name of the account. Indexed for faster lookups.
        description (str): Detailed description of the account.
        tags (List[str]): List of tags associated with the account. Must contain at least
            one tag and all tags must be unique.
        start_ts (datetime.datetime): Timestamp when the account became active.
            Indexed for time-based queries.
        end_ts (datetime | None): Timestamp when the account was closed or
            deactivated. Null if the account is still active.
        owner (Users): The owner of the account. One-to-one relationship with cascade delete.
        accounts_indexer (AccountsIndexer): The indexer of the account. One-to-one relationship with cascade delete.
        transactions_from_accounts (List[Transactions]): List of transactions where this
            account is the source. One-to-many relationship with cascade delete.
        transactions_to_accounts (List[Transactions]): List of transactions where this
            account is the destination. One-to-many relationship with cascade delete.
    """

    __tablename__ = ACCOUNTS__TABLENAME
    __table_args__ = {"schema": SCHEMA_NAME}

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    start_ts: builtin_datetime = Field(
        sa_column=Column(TIMESTAMP, nullable=False, index=True), default_factory=modelutils.current_timestamp
    )
    end_ts: builtin_datetime | None = Field(sa_column=Column(TIMESTAMP, nullable=True, index=True), default=None)
    icon: URLStr | None = Field(sa_column=Column(Text, nullable=True, index=False, unique=False), default=None)
    owner_id: uuid.UUID = Field(foreign_key=fk_id(USERS__TABLENAME), nullable=False, index=True)

    owner: "Users" = Relationship(back_populates="owned_accounts", sa_relationship_kwargs={"foreign_keys": "Users.id"})

    accounts_indexer: "AccountsIndexer" = Relationship(
        back_populates=ACCOUNTS__TABLENAME,
        sa_relationship_kwargs={"uselist": False, "foreign_keys": "AccountsIndexer.account_id"},
        cascade_delete=True,
    )

    transactions_from_accounts: List["Transactions"] = Relationship(
        back_populates="from_accounts",
        sa_relationship_kwargs={"foreign_keys": "Transactions.from_account_id"},
        cascade_delete=True,
    )

    transactions_to_accounts: List["Transactions"] = Relationship(
        back_populates="to_accounts",
        sa_relationship_kwargs={"foreign_keys": "Transactions.to_account_id"},
        cascade_delete=True,
    )

    @model_validator(mode="after")
    def _normalize_model(self) -> Self:
        """Normalize the model after initialization."""
        super()._normalize_model()
        if self.end_ts and self.start_ts > self.end_ts:
            raise ValueError("The end_ts must be after the start_ts")

        if self.end_ts and self.end_ts < self.created_at:
            raise ValueError("The end_ts must be after the created_at")

        if self.end_ts and self.end_ts < self.updated_at:
            raise ValueError("The end_ts must be before the updated_at")

        return self
