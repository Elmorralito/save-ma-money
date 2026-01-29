"""Accounts module for managing financial account entities in the Papita Transactions system.

This module defines the Accounts model which represents financial accounts in the system.
It provides the structure for storing account information and establishes relationships
with assets, liabilities, and transactions.

Classes:
    Accounts: Represents a financial account in the system.
"""

from datetime import datetime
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ARRAY, TIMESTAMP, Column, String, Text
from sqlmodel import Field, Relationship

from .base import BaseSQLModel
from .contstants import ACCOUNTS__TABLENAME, USERS__TABLENAME

if TYPE_CHECKING:
    from .indexers import AccountsIndexer
    from .transactions import Transactions
    from .users import Users


class Accounts(BaseSQLModel, table=True):  # type: ignore
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
        end_ts (Optional[datetime.datetime]): Timestamp when the account was closed or
            deactivated. Null if the account is still active.
        asset_accounts (AssetAccounts): Related asset account information. One-to-one
            relationship with cascade delete.
        liability_accounts (Optional[LiabilityAccounts]): Related liability account
            information. Optional one-to-one relationship with cascade delete.
        transactions_from_accounts (List[Transactions]): List of transactions where this
            account is the source. One-to-many relationship with cascade delete.
        transactions_to_accounts (List[Transactions]): List of transactions where this
            account is the destination. One-to-many relationship with cascade delete.
    """

    __tablename__ = ACCOUNTS__TABLENAME

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(sa_type=String, nullable=False, index=True)
    description: str = Field(sa_type=Text, nullable=False)
    tags: List[str] = Field(sa_column=Column(ARRAY(String)), min_items=1, unique_items=True)
    start_ts: datetime = Field(
        sa_column=Column(TIMESTAMP, nullable=False, index=True), default_factory=datetime.now
    )
    end_ts: Optional[datetime] = Field(sa_column=Column(TIMESTAMP, nullable=True, index=True), default=None)
    owner_id: uuid.UUID = Field(foreign_key=f"{USERS__TABLENAME}.uid", nullable=False, index=True)

    owner: "Users" = Relationship(back_populates="owned_accounts")

    accounts_indexer: "AccountsIndexer" = Relationship(
        back_populates=ACCOUNTS__TABLENAME,
        sa_relationship_kwargs={"uselist": False},
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
