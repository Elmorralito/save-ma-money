"""Add per-user preferences JSONB and flip auth_provider default to local.

Revision ID: s6b7c8d9e0f1
Revises: r5a6b7c8d9e0
Create Date: 2026-11-24 23:05:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "s6b7c8d9e0f1"
down_revision: str | Sequence[str] | None = "r5a6b7c8d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA_NAME = "papita_transactions"
TABLE_NAME = "users"


def upgrade() -> None:
    op.add_column(
        TABLE_NAME,
        sa.Column(
            "preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Per-user domain settings and preferences (currency, locale, ledger defaults, alerts, security)",
        ),
        schema=SCHEMA_NAME,
    )
    # Self-hosted identity: new rows default to local; keep legacy supabase values readable.
    op.alter_column(
        TABLE_NAME,
        "auth_provider",
        server_default=sa.text("'local'"),
        comment="Identity authority: local | legacy supabase",
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    op.alter_column(
        TABLE_NAME,
        "auth_provider",
        server_default=sa.text("'supabase'"),
        comment="Identity authority: supabase | local",
        schema=SCHEMA_NAME,
    )
    op.drop_column(TABLE_NAME, "preferences", schema=SCHEMA_NAME)
