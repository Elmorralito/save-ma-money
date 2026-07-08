"""Category taxonomy model (v3)."""

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ARRAY, Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, String, Text
from sqlmodel import Field, Relationship

from .base import SCHEMA_NAME, BaseSQLModel
from .contstants import CATEGORIES__TABLENAME, USERS__TABLENAME
from .enums import CategoryKind

if TYPE_CHECKING:
    from .transactions import Transactions, TransactionTemplates
    from .users import Users


class Categories(BaseSQLModel, table=True):  # type: ignore
    """Income/expense category with optional hierarchy."""

    __tablename__ = CATEGORIES__TABLENAME
    __table_args__ = (
        Index(
            "uq_categories_owner_name_kind",
            "owner_id",
            "name",
            "category_kind",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
        {"schema": SCHEMA_NAME},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID | None = Field(foreign_key=f"{USERS__TABLENAME}.id", nullable=True, index=True)
    parent_id: uuid.UUID | None = Field(foreign_key=f"{CATEGORIES__TABLENAME}.id", nullable=True, index=True)
    name: str = Field(sa_type=String(255), nullable=False)
    category_kind: CategoryKind = Field(
        sa_column=Column(
            SAEnum(CategoryKind, name="category_kind", schema="papita_transactions", create_type=False),
            nullable=False,
        )
    )
    description: str = Field(sa_type=Text, nullable=False, default="")
    tags: List[str] = Field(sa_column=Column(ARRAY(String), nullable=False), default_factory=list)
    icon: str | None = Field(sa_type=String(64), nullable=True, default=None)
    color: str | None = Field(sa_type=String(7), nullable=True, default=None)

    owner: Optional["Users"] = Relationship(back_populates="owned_categories")
    parent: Optional["Categories"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Categories.id"},
    )
    children: List["Categories"] = Relationship(back_populates="parent")
    transaction_templates: List["TransactionTemplates"] = Relationship(back_populates="category", cascade_delete=True)
    transactions: List["Transactions"] = Relationship(back_populates="category", cascade_delete=True)
