# pylint: disable=C0103
"""Add cashflow_bucket to categories and cashflow_only to credit_card_account_details (PPT-091 / #184).

Revision ID: o2d3e4f5a6b7
Revises: n1c2d3e4f5a6
Create Date: 2026-11-21 14:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "o2d3e4f5a6b7"
down_revision: Union[str, None] = "n1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "papita_transactions"
_CASHFLOW_BUCKET_VALUES = (
    "INCOME_FIXED",
    "INCOME_VARIABLE",
    "LOAN_PAYMENT",
    "FIXED_EXPENSE",
    "VARIABLE_EXPENSE",
    "UNEXPECTED_EXPENSE",
    "SAVINGS",
    "CAPITAL_DEPLOYMENT",
    "NON_OPERATING_INFLOW",
)
cashflow_bucket_enum = postgresql.ENUM(
    *_CASHFLOW_BUCKET_VALUES,
    name="cashflow_bucket",
    schema=SCHEMA,
    create_type=False,
)


def upgrade() -> None:
    """Create cashflow_bucket enum/column on categories and cashflow_only on credit_card_account_details."""
    bind = op.get_bind()
    postgresql.ENUM(*_CASHFLOW_BUCKET_VALUES, name="cashflow_bucket", schema=SCHEMA).create(
        bind,
        checkfirst=True,
    )
    op.add_column(
        "categories",
        sa.Column("cashflow_bucket", cashflow_bucket_enum, nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "credit_card_account_details",
        sa.Column(
            "cashflow_only",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Drop cashflow_only, cashflow_bucket column, and cashflow_bucket enum."""
    bind = op.get_bind()
    op.drop_column("credit_card_account_details", "cashflow_only", schema=SCHEMA)
    op.drop_column("categories", "cashflow_bucket", schema=SCHEMA)
    postgresql.ENUM(*_CASHFLOW_BUCKET_VALUES, name="cashflow_bucket", schema=SCHEMA).drop(
        bind,
        checkfirst=True,
    )
