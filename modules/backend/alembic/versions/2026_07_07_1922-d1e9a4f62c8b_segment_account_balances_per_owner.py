# pylint: disable=C0103
"""Segment account_balances per owner with explicit tenant-scoped account joins.

Revision ID: d1e9a4f62c8b
Revises: c4a8e2f19b7d
Create Date: 2026-07-07 19:22:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from alembic_utils.pg_materialized_view import PGMaterializedView

from papita_txnsmodel.model.contstants import ACCOUNT_BALANCES_VIEW, SCHEMA_NAME
from papita_txnsmodel.views import ACCOUNT_BALANCES_MATERIALIZED_VIEW

revision: str = "d1e9a4f62c8b"
down_revision: Union[str, Sequence[str], None] = "c4a8e2f19b7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PRE_SEGMENT_ACCOUNT_BALANCES = PGMaterializedView(
    schema=SCHEMA_NAME,
    signature=ACCOUNT_BALANCES_VIEW,
    definition="""
SELECT
    a.owner_id,
    a.id AS account_id,
    a.currency,
    COALESCE(SUM(CASE WHEN t.to_account_id = a.id AND t.status = 'COMPLETED' THEN t.amount END), 0)
        - COALESCE(
            SUM(CASE WHEN t.from_account_id = a.id AND t.status = 'COMPLETED' THEN t.amount END), 0
        ) AS balance,
    MAX(t.transaction_ts) AS last_activity_ts
FROM papita_transactions.accounts a
LEFT JOIN papita_transactions.transactions t
    ON t.owner_id = a.owner_id
    AND (t.from_account_id = a.id OR t.to_account_id = a.id)
    AND t.active = true
WHERE a.active = true
GROUP BY a.owner_id, a.id, a.currency
""",
    with_data=True,
)


def upgrade() -> None:
    """Replace account_balances with per-owner segmented definition."""
    op.replace_entity(ACCOUNT_BALANCES_MATERIALIZED_VIEW)
    op.execute(sa.text("COMMIT"))


def downgrade() -> None:
    """Restore pre-segmentation account_balances definition."""
    op.replace_entity(_PRE_SEGMENT_ACCOUNT_BALANCES)
    op.execute(sa.text("COMMIT"))
