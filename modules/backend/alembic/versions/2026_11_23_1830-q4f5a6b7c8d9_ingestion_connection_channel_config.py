# pylint: disable=C0103
"""Add per-user email channel filter columns to ingestion_connections.

Revision ID: q4f5a6b7c8d9
Revises: p3e4f5a6b7c8
Create Date: 2026-11-23 18:30:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from papita_txnsmodel.model.contstants import INGESTION_CONNECTIONS__TABLENAME, SCHEMA_NAME

revision: str = "q4f5a6b7c8d9"
down_revision: Union[str, None] = "p3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = SCHEMA_NAME
TABLE = INGESTION_CONNECTIONS__TABLENAME


def upgrade() -> None:
    """Add non-secret per-owner email channel filter columns to ingestion_connections."""
    op.add_column(
        TABLE,
        sa.Column(
            "email_senders",
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'::varchar[]"),
        ),
        schema=SCHEMA,
    )
    op.add_column(
        TABLE,
        sa.Column(
            "email_subjects",
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'::varchar[]"),
        ),
        schema=SCHEMA,
    )
    op.add_column(
        TABLE,
        sa.Column("email_source_label", sa.String(length=255), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        TABLE,
        sa.Column("email_query", sa.Text(), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Drop email channel filter columns from ingestion_connections."""
    op.drop_column(TABLE, "email_query", schema=SCHEMA)
    op.drop_column(TABLE, "email_source_label", schema=SCHEMA)
    op.drop_column(TABLE, "email_subjects", schema=SCHEMA)
    op.drop_column(TABLE, "email_senders", schema=SCHEMA)
