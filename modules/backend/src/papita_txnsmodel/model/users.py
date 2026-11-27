"""Users model (v3) — self-hosted tenant profile identity.

``users.id`` is the JWT ``sub`` (uuid5 of username for email signup, or a stable
OIDC-derived UUID for Google PKCE). Credentials are local Argon2 hashes and/or
passwordless OAuth profiles under ``auth_provider='local'``.
"""

import uuid
from typing import TYPE_CHECKING, Any, List

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship

from .base import BaseSQLModel
from .contstants import SCHEMA_NAME, USERS__TABLENAME

if TYPE_CHECKING:
    from .account_financing import AccountFinancing
    from .accounts import Accounts
    from .categories import Categories
    from .transactions import Transactions, TransactionTemplates


class Users(BaseSQLModel, table=True):  # type: ignore
    """Tenant root user row for self-hosted local / Google OAuth identity.

    Attributes:
        id: Primary key — JWT ``sub`` for the tenant owner.
        username: Display / login handle for the app profile.
        email: Canonical login email (unique).
        password: Argon2 hash for email/password signup; ``None`` for OAuth-only.
        auth_provider: ``local`` (self-hosted); legacy rows may still say ``supabase``.
        display_name: Optional human-readable name from registration / IdP.
        phone: Optional phone number for profile lookup.
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
        default="local",
        max_length=32,
        nullable=False,
        sa_column_kwargs={
            "server_default": text("'local'"),
            "comment": "Identity authority: local | legacy supabase",
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
    preferences: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(
            JSONB,
            nullable=False,
            server_default=text("'{}'::jsonb"),
            comment="Per-user domain settings and preferences (currency, locale, ledger defaults, alerts, security)",
        ),
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
