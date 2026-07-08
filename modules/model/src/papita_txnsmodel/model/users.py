"""Users model (v3)."""

import uuid
from typing import TYPE_CHECKING, List

from sqlmodel import Field, Relationship

from .base import BaseSQLModel
from .contstants import SCHEMA_NAME, USERS__TABLENAME

if TYPE_CHECKING:
    from .account_financing import AccountFinancing
    from .accounts import Accounts
    from .categories import Categories
    from .transactions import Transactions, TransactionTemplates


class Users(BaseSQLModel, table=True):  # type: ignore
    """Tenant root user."""

    __tablename__ = USERS__TABLENAME
    __table_args__ = {"schema": SCHEMA_NAME}

    id: uuid.UUID = Field(primary_key=True, index=True)
    username: str = Field(nullable=False, index=True, unique=True)
    email: str = Field(nullable=False, index=True, unique=True)
    password: str = Field(nullable=False)

    owned_accounts: List["Accounts"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}, cascade_delete=True
    )
    owned_categories: List["Categories"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}, cascade_delete=True
    )
    owned_transaction_templates: List["TransactionTemplates"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}, cascade_delete=True
    )
    owned_transactions: List["Transactions"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}, cascade_delete=True
    )
    owned_account_financing: List["AccountFinancing"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}, cascade_delete=True
    )
