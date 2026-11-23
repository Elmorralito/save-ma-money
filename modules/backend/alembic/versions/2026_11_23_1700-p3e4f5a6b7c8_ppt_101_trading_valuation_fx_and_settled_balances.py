# pylint: disable=C0103
"""Add FX rate, trading position valuation columns, and settled-only account_balances (PPT-101 / #262).

Revision ID: p3e4f5a6b7c8
Revises: o2d3e4f5a6b7
Create Date: 2026-11-23 17:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from alembic_utils.pg_materialized_view import PGMaterializedView

from papita_txnsmodel.model.contstants import ACCOUNT_BALANCES_VIEW, SCHEMA_NAME
from papita_txnsmodel.views import ACCOUNT_BALANCES_MATERIALIZED_VIEW

revision: str = "p3e4f5a6b7c8"
down_revision: Union[str, None] = "o2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = SCHEMA_NAME

_PRE_SETTLED_ACCOUNT_BALANCES = PGMaterializedView(
    schema=SCHEMA,
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


def upgrade() -> None:
    """Add fx_rate/trading valuation columns and exclude IN_TRANSIT rows from account_balances."""
    op.add_column(
        "accounts",
        sa.Column(
            "fx_rate",
            sa.DECIMAL(22, 8),
            nullable=False,
            server_default=sa.text("1.0"),
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "trading_account_details",
        sa.Column("symbol", sa.String(length=32), nullable=True),
        schema=SCHEMA,
    )
    op.alter_column(
        "trading_account_details",
        "units",
        existing_type=sa.SmallInteger(),
        type_=sa.DECIMAL(22, 8),
        existing_nullable=False,
        server_default=sa.text("1.0"),
        postgresql_using="units::numeric(22,8)",
        schema=SCHEMA,
    )
    op.add_column(
        "trading_account_details",
        sa.Column("unit_price", sa.DECIMAL(22, 8), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "trading_account_details",
        sa.Column(
            "fx_rate",
            sa.DECIMAL(22, 8),
            nullable=False,
            server_default=sa.text("1.0"),
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "trading_account_details",
        sa.Column("unrealized_pnl", sa.DECIMAL(22, 8), nullable=True),
        schema=SCHEMA,
    )
    op.replace_entity(ACCOUNT_BALANCES_MATERIALIZED_VIEW)
    op.execute(sa.text("COMMIT"))


def downgrade() -> None:
    """Revert settled-only account_balances and drop PPT-101 valuation/FX columns."""
    op.replace_entity(_PRE_SETTLED_ACCOUNT_BALANCES)
    op.execute(sa.text("COMMIT"))
    op.drop_column("trading_account_details", "unrealized_pnl", schema=SCHEMA)
    op.drop_column("trading_account_details", "fx_rate", schema=SCHEMA)
    op.drop_column("trading_account_details", "unit_price", schema=SCHEMA)
    op.alter_column(
        "trading_account_details",
        "units",
        existing_type=sa.DECIMAL(22, 8),
        type_=sa.SmallInteger(),
        existing_nullable=False,
        server_default=None,
        postgresql_using="GREATEST(1, ROUND(units)::smallint)",
        schema=SCHEMA,
    )
    op.drop_column("trading_account_details", "symbol", schema=SCHEMA)
    op.drop_column("accounts", "fx_rate", schema=SCHEMA)
