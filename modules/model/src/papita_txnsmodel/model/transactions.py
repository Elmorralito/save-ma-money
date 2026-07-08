"""Transaction templates and posted transactions (v3)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ARRAY, CHAR, DECIMAL, TIMESTAMP, Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, SmallInteger, String, Text
from sqlmodel import Field, Relationship

from .base import SCHEMA_NAME, BaseSQLModel
from .contstants import (
    ACCOUNTS__TABLENAME,
    CATEGORIES__TABLENAME,
    TRANSACTION_TEMPLATES__TABLENAME,
    TRANSACTIONS__TABLENAME,
    USERS__TABLENAME,
)
from .enums import TransactionKind, TransactionStatus

if TYPE_CHECKING:
    from .accounts import Accounts
    from .categories import Categories
    from .users import Users


class TransactionTemplates(BaseSQLModel, table=True):  # type: ignore
    """Recurring or planned transaction template."""

    __tablename__ = TRANSACTION_TEMPLATES__TABLENAME
    __table_args__ = (
        Index("ix_transaction_templates_owner_category", "owner_id", "category_id"),
        {"schema": SCHEMA_NAME},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key=f"{USERS__TABLENAME}.id", nullable=False, index=True)
    category_id: uuid.UUID = Field(foreign_key=f"{CATEGORIES__TABLENAME}.id", nullable=False, index=True)
    name: str = Field(nullable=False, index=True)
    description: str = Field(sa_type=Text, nullable=False, default="")
    tags: List[str] = Field(sa_column=Column(ARRAY(String), nullable=False), default_factory=list)
    planned_amount: float = Field(sa_column=Column(DECIMAL(22, 8), nullable=False), gt=0)
    planned_day: int = Field(sa_column=Column(SmallInteger, nullable=False), ge=1, le=31)
    use_month_end: bool = Field(nullable=False, default=False)

    owner: "Users" = Relationship(back_populates="owned_transaction_templates")
    category: "Categories" = Relationship(back_populates="transaction_templates")
    transactions: List["Transactions"] = Relationship(back_populates="template", cascade_delete=True)


class Transactions(BaseSQLModel, table=True):  # type: ignore
    """Posted ledger transaction."""

    __tablename__ = TRANSACTIONS__TABLENAME
    __table_args__ = (
        Index("ix_transactions_owner_active_status", "owner_id", "active", "status"),
        Index("ix_transactions_owner_transaction_ts", "owner_id", "transaction_ts"),
        Index("ix_transactions_from_account_id", "from_account_id"),
        Index("ix_transactions_to_account_id", "to_account_id"),
        Index("ix_transactions_category_id", "category_id"),
        Index("ix_transactions_id", "id"),
        {
            "schema": SCHEMA_NAME,
            "postgresql_partition_by": "RANGE (transaction_ts)",
        },
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key=f"{USERS__TABLENAME}.id", nullable=False, index=True)
    transaction_kind: TransactionKind = Field(
        sa_column=Column(
            SAEnum(TransactionKind, name="transaction_kind", schema="papita_transactions", create_type=False),
            nullable=False,
        )
    )
    amount: float = Field(sa_column=Column(DECIMAL(22, 8), nullable=False), gt=0)
    currency: str = Field(sa_column=Column(CHAR(3), nullable=False), default="USD")
    transaction_ts: datetime = Field(
        sa_column=Column(TIMESTAMP, nullable=False, index=True, primary_key=True),
        default_factory=datetime.now,
    )
    from_account_id: uuid.UUID | None = Field(foreign_key=f"{ACCOUNTS__TABLENAME}.id", default=None, nullable=True)
    to_account_id: uuid.UUID | None = Field(foreign_key=f"{ACCOUNTS__TABLENAME}.id", default=None, nullable=True)
    category_id: uuid.UUID | None = Field(foreign_key=f"{CATEGORIES__TABLENAME}.id", default=None, nullable=True)
    template_id: uuid.UUID | None = Field(
        foreign_key=f"{TRANSACTION_TEMPLATES__TABLENAME}.id", default=None, nullable=True
    )
    status: TransactionStatus = Field(
        sa_column=Column(
            SAEnum(TransactionStatus, name="transaction_status", schema="papita_transactions", create_type=False),
            nullable=False,
        ),
        default=TransactionStatus.COMPLETED,
    )
    description: str = Field(sa_type=Text, nullable=False, default="")
    reference_number: str | None = Field(sa_type=String(64), nullable=True, default=None)
    tags: List[str] = Field(sa_column=Column(ARRAY(String), nullable=False), default_factory=list)

    owner: "Users" = Relationship(back_populates="owned_transactions")
    category: Optional["Categories"] = Relationship(back_populates="transactions")
    template: Optional["TransactionTemplates"] = Relationship(back_populates="transactions")
    from_accounts: Optional["Accounts"] = Relationship(
        back_populates="transactions_from_accounts",
        sa_relationship_kwargs={"foreign_keys": "Transactions.from_account_id"},
    )
    to_accounts: Optional["Accounts"] = Relationship(
        back_populates="transactions_to_accounts",
        sa_relationship_kwargs={"foreign_keys": "Transactions.to_account_id"},
    )
