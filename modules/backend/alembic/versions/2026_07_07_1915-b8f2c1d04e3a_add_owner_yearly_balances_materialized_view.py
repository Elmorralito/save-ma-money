# pylint: disable=C0103
"""Add owner_yearly_balances materialized view.

Combined per-owner, per-year ledger totals across all accounts (by currency).
Transfers between a user's own accounts net to zero at the owner level.

Revision ID: b8f2c1d04e3a
Revises: a75354933e79
Create Date: 2026-07-07 19:15:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from papita_txnsmodel.views import OWNER_YEARLY_BALANCES_MATERIALIZED_VIEW

revision: str = "b8f2c1d04e3a"
down_revision: Union[str, Sequence[str], None] = "a75354933e79"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create owner_yearly_balances materialized view."""
    op.create_entity(OWNER_YEARLY_BALANCES_MATERIALIZED_VIEW)
    op.create_index(
        "owner_yearly_balances_owner_year_currency_idx",
        "owner_yearly_balances",
        ["owner_id", "balance_year", "currency"],
        unique=True,
        schema="papita_transactions",
    )
    op.execute(sa.text("COMMIT"))


def downgrade() -> None:
    """Drop owner_yearly_balances materialized view."""
    op.drop_index(
        "owner_yearly_balances_owner_year_currency_idx",
        table_name="owner_yearly_balances",
        schema="papita_transactions",
    )
    op.drop_entity(OWNER_YEARLY_BALANCES_MATERIALIZED_VIEW, cascade=True)
