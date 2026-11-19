"""Users model (v3) — tenant profile linked to Supabase Auth identity.

``users.id`` **is** the Supabase Auth user id (``auth.users.id`` / JWT ``sub``).
Credentials live in the Supabase Auth project; ``password`` is only used for the
legacy/local HS256 test path (``auth_provider='local'``).
"""

import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import text
from sqlmodel import Field, Relationship

from .base import BaseSQLModel
from .contstants import SCHEMA_NAME, USERS__TABLENAME

if TYPE_CHECKING:
    from .account_financing import AccountFinancing
    from .accounts import Accounts
    from .categories import Categories
    from .transactions import Transactions, TransactionTemplates


class Users(BaseSQLModel, table=True):  # type: ignore
    """Tenant root user row pointing at a Supabase Auth subject.

    Attributes:
        id: Primary key — equal to Supabase Auth ``users.id`` (JWT ``sub``).
        username: Display / login handle for the app profile.
        email: Email mirrored from Auth claims (unique).
        password: Argon2 hash for ``auth_provider=local`` only; ``None`` when Auth-managed.
        auth_provider: ``supabase`` (MVP) or ``local`` (unit tests / transitional).
        display_name: Optional human-readable name from Auth / registration.
        phone: Optional phone number mirrored for Auth profile lookup.
        provider_type: Signup channel — ``email``, ``google``, or ``github``.
    """

    __tablename__ = USERS__TABLENAME
    __table_args__ = {"schema": SCHEMA_NAME}

    id: uuid.UUID = Field(
        primary_key=True,
        index=True,
        description="Supabase Auth user id (auth.users.id / JWT sub)",
        sa_column_kwargs={"comment": "Supabase Auth user id (auth.users.id / JWT sub)"},
    )
    username: str = Field(nullable=False, index=True, unique=True)
    email: str = Field(nullable=False, index=True, unique=True)
    password: str | None = Field(default=None, nullable=True)
    auth_provider: str = Field(
        default="supabase",
        max_length=32,
        nullable=False,
        sa_column_kwargs={
            "server_default": text("'supabase'"),
            "comment": "Identity authority: supabase | local",
        },
    )
    display_name: str | None = Field(default=None, max_length=255, nullable=True)
    phone: str | None = Field(default=None, max_length=32, nullable=True, index=True)
    provider_type: str = Field(
        default="email",
        max_length=32,
        nullable=False,
        sa_column_kwargs={
            "server_default": text("'email'"),
            "comment": "Signup channel: email | google | github",
        },
    )

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
