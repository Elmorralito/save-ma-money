# pylint: disable=C0103
"""Add include_in_balance to accounts (PPT-097 / #261 Guardrail A).

Revision ID: m0b1c2d3e4f5
Revises: l9a0b1c2d3e4
Create Date: 2026-11-17 20:30:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from papita_txnsmodel.model.contstants import SCHEMA_NAME

revision: str = "m0b1c2d3e4f5"
down_revision: Union[str, Sequence[str], None] = "l9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add include_in_balance boolean column to papita_transactions.accounts."""
    op.add_column(
        "accounts",
        sa.Column(
            "include_in_balance",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    """Drop include_in_balance column from papita_transactions.accounts."""
    op.drop_column("accounts", "include_in_balance", schema=SCHEMA_NAME)
