"""Add settlement_status to papita_transactions.transactions (PPT-099 / #261).

Revision ID: n1c2d3e4f5a6
Revises: m0b1c2d3e4f5
Create Date: 2026-11-17 21:45:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "n1c2d3e4f5a6"
down_revision: Union[str, None] = "m0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "papita_transactions"
settlement_status_enum = postgresql.ENUM(
    "SETTLED",
    "IN_TRANSIT",
    name="settlement_status",
    schema=SCHEMA,
    create_type=False,
)


def upgrade() -> None:
    """Create settlement_status enum and add column to transactions."""
    bind = op.get_bind()
    postgresql.ENUM("SETTLED", "IN_TRANSIT", name="settlement_status", schema=SCHEMA).create(
        bind,
        checkfirst=True,
    )
    op.add_column(
        "transactions",
        sa.Column(
            "settlement_status",
            settlement_status_enum,
            nullable=False,
            server_default=sa.text("'SETTLED'::papita_transactions.settlement_status"),
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Drop settlement_status column and enum."""
    bind = op.get_bind()
    op.drop_column("transactions", "settlement_status", schema=SCHEMA)
    postgresql.ENUM("SETTLED", "IN_TRANSIT", name="settlement_status", schema=SCHEMA).drop(
        bind,
        checkfirst=True,
    )
