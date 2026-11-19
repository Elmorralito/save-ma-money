# pylint: disable=C0103
"""Add owner monthly, quarterly, and biannual balance materialized views.

Combined per-owner period totals across all accounts (by currency).

Revision ID: c4a8e2f19b7d
Revises: b8f2c1d04e3a
Create Date: 2026-07-07 19:19:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from papita_txnsmodel.views import (
    OWNER_BIANNUAL_BALANCES_MATERIALIZED_VIEW,
    OWNER_MONTHLY_BALANCES_MATERIALIZED_VIEW,
    OWNER_QUARTERLY_BALANCES_MATERIALIZED_VIEW,
)

revision: str = "c4a8e2f19b7d"
down_revision: Union[str, Sequence[str], None] = "b8f2c1d04e3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create owner period balance materialized views."""
    op.create_entity(OWNER_MONTHLY_BALANCES_MATERIALIZED_VIEW)
    op.create_index(
        "owner_monthly_balances_owner_year_month_currency_idx",
        "owner_monthly_balances",
        ["owner_id", "balance_year", "balance_month", "currency"],
        unique=True,
        schema="papita_transactions",
    )

    op.create_entity(OWNER_QUARTERLY_BALANCES_MATERIALIZED_VIEW)
    op.create_index(
        "owner_quarterly_balances_owner_year_quarter_currency_idx",
        "owner_quarterly_balances",
        ["owner_id", "balance_year", "balance_quarter", "currency"],
        unique=True,
        schema="papita_transactions",
    )

    op.create_entity(OWNER_BIANNUAL_BALANCES_MATERIALIZED_VIEW)
    op.create_index(
        "owner_biannual_balances_owner_year_half_currency_idx",
        "owner_biannual_balances",
        ["owner_id", "balance_year", "balance_half", "currency"],
        unique=True,
        schema="papita_transactions",
    )
    op.execute(sa.text("COMMIT"))


def downgrade() -> None:
    """Drop owner period balance materialized views."""
    op.drop_index(
        "owner_biannual_balances_owner_year_half_currency_idx",
        table_name="owner_biannual_balances",
        schema="papita_transactions",
    )
    op.drop_entity(OWNER_BIANNUAL_BALANCES_MATERIALIZED_VIEW, cascade=True)

    op.drop_index(
        "owner_quarterly_balances_owner_year_quarter_currency_idx",
        table_name="owner_quarterly_balances",
        schema="papita_transactions",
    )
    op.drop_entity(OWNER_QUARTERLY_BALANCES_MATERIALIZED_VIEW, cascade=True)

    op.drop_index(
        "owner_monthly_balances_owner_year_month_currency_idx",
        table_name="owner_monthly_balances",
        schema="papita_transactions",
    )
    op.drop_entity(OWNER_MONTHLY_BALANCES_MATERIALIZED_VIEW, cascade=True)
