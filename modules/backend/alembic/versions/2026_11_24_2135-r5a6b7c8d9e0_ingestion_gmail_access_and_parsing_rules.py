# pylint: disable=C0103
"""Add per-user Gmail access and email parsing rules to ingestion_connections.

Revision ID: r5a6b7c8d9e0
Revises: q4f5a6b7c8d9
Create Date: 2026-11-24 21:35:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from papita_txnsmodel.model.contstants import INGESTION_CONNECTIONS__TABLENAME, SCHEMA_NAME

revision: str = "r5a6b7c8d9e0"
down_revision: Union[str, None] = "q4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = SCHEMA_NAME
TABLE = INGESTION_CONNECTIONS__TABLENAME


def upgrade() -> None:
    """Add per-user Gmail access flags, encrypted token slot, and JSONB parsing rules."""
    op.add_column(
        TABLE,
        sa.Column(
            "gmail_access_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        schema=SCHEMA,
    )
    op.add_column(
        TABLE,
        sa.Column("gmail_connected_email", sa.String(length=255), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        TABLE,
        sa.Column("gmail_refresh_token_enc", sa.Text(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        TABLE,
        sa.Column(
            "parsing_rules",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Drop per-user Gmail access and parsing_rules columns."""
    op.drop_column(TABLE, "parsing_rules", schema=SCHEMA)
    op.drop_column(TABLE, "gmail_refresh_token_enc", schema=SCHEMA)
    op.drop_column(TABLE, "gmail_connected_email", schema=SCHEMA)
    op.drop_column(TABLE, "gmail_access_enabled", schema=SCHEMA)
