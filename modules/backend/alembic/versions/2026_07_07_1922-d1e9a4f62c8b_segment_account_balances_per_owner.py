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

revision: str = "d1e9a4f62c8b"
down_revision: Union[str, Sequence[str], None] = "c4a8e2f19b7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SEGMENTED_ACCOUNT_BALANCES = PGMaterializedView(
    schema=SCHEMA_NAME,
    signature=ACCOUNT_BALANCES_VIEW,
    definition="""
WITH per_owner_account_net AS (
    SELECT
        a.owner_id,
        a.id account_id,
        a.currency,
        SUM(
            CASE
                WHEN
                    t.to_account_id = a.id AND a_to.id IS NOT NULL
                    THEN t.amount
                WHEN
                    t.from_account_id = a.id AND a_from.id IS NOT NULL
                    THEN -t.amount
                ELSE 0
            END
        ) balance,
        MAX(t.transaction_ts) last_activity_ts
    FROM papita_transactions.accounts AS a
        LEFT JOIN papita_transactions.transactions AS t
            ON
                a.owner_id = t.owner_id
                AND t.active = TRUE
                AND t.status = 'COMPLETED'
                AND (a.id = t.from_account_id OR a.id = t.to_account_id)
        LEFT JOIN papita_transactions.accounts AS a_to
            ON
                t.to_account_id = a_to.id
                AND t.owner_id = a_to.owner_id
                AND a_to.active = TRUE
        LEFT JOIN papita_transactions.accounts AS a_from
            ON
                t.from_account_id = a_from.id
                AND t.owner_id = a_from.owner_id
                AND a_from.active = TRUE
    WHERE
        a.active = TRUE
        AND (t.id IS NULL OR a_to.id IS NOT NULL OR a_from.id IS NOT NULL)
    GROUP BY a.owner_id, a.id, a.currency
)

SELECT
    owner_id,
    account_id,
    currency,
    balance,
    last_activity_ts
FROM per_owner_account_net
""",
    with_data=True,
)

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
    op.replace_entity(_SEGMENTED_ACCOUNT_BALANCES)
    op.execute(sa.text("COMMIT"))


def downgrade() -> None:
    """Restore pre-segmentation account_balances definition."""
    op.replace_entity(_PRE_SEGMENT_ACCOUNT_BALANCES)
    op.execute(sa.text("COMMIT"))
