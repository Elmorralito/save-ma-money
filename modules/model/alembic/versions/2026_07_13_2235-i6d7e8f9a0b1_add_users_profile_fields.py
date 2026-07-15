# pylint: disable=C0103
"""Add display_name, phone, and provider_type to users.

Revision ID: i6d7e8f9a0b1
Revises: h5c6d7e8f9a0
Create Date: 2026-07-13 22:35:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from papita_txnsmodel.model.contstants import SCHEMA_NAME, USERS__TABLENAME

revision: str = "i6d7e8f9a0b1"
down_revision: Union[str, Sequence[str], None] = "h5c6d7e8f9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add profile fields for Auth registration (display name, phone, provider)."""
    op.add_column(
        USERS__TABLENAME,
        sa.Column("display_name", sa.String(length=255), nullable=True),
        schema=SCHEMA_NAME,
    )
    op.add_column(
        USERS__TABLENAME,
        sa.Column("phone", sa.String(length=32), nullable=True),
        schema=SCHEMA_NAME,
    )
    op.add_column(
        USERS__TABLENAME,
        sa.Column(
            "provider_type",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'email'"),
            comment="Signup channel: email | phone",
        ),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        op.f("ix_papita_transactions_users_phone"),
        USERS__TABLENAME,
        ["phone"],
        unique=False,
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    """Drop profile fields."""
    op.drop_index(
        op.f("ix_papita_transactions_users_phone"),
        table_name=USERS__TABLENAME,
        schema=SCHEMA_NAME,
    )
    op.drop_column(USERS__TABLENAME, "provider_type", schema=SCHEMA_NAME)
    op.drop_column(USERS__TABLENAME, "phone", schema=SCHEMA_NAME)
    op.drop_column(USERS__TABLENAME, "display_name", schema=SCHEMA_NAME)
