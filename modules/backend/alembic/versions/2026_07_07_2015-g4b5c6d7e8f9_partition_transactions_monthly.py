# pylint: disable=C0103
"""Partition transactions by monthly RANGE on transaction_ts.

Revision ID: g4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-07-07 20:15:00.000000+00:00

"""

from typing import Sequence, Union

import alembic_utils.reversible_op  # pylint: disable=unused-import # noqa: F401
import sqlalchemy as sa
from alembic import op
from alembic_utils.pg_materialized_view import PGMaterializedView

from papita_txnsmodel.config.transaction_partitions import (
    LEGACY_TABLE_NAME,
    STAGING_TABLE_NAME,
    add_transactions_check_constraint_sql,
    create_legacy_transactions_indexes_sql,
    create_non_partitioned_table_sql,
    create_parent_partitioned_table_sql,
    create_transactions_indexes_sql,
    ensure_monthly_partitions,
    migration_partition_bounds,
)
from papita_txnsmodel.model.contstants import ACCOUNT_BALANCES_VIEW, SCHEMA_NAME, TRANSACTIONS__TABLENAME
from papita_txnsmodel.views import view_entities
from papita_txnsmodel.views.indexes import ALL_VIEW_INDEX_SPECS, create_view_index

revision: str = "g4b5c6d7e8f9"
down_revision: Union[str, Sequence[str], None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PRE_SETTLED_ACCOUNT_BALANCES = PGMaterializedView(
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

_HISTORICAL_VIEW_ENTITIES = [
    _PRE_SETTLED_ACCOUNT_BALANCES if entity.signature == ACCOUNT_BALANCES_VIEW else entity for entity in view_entities
]


def _drop_balance_materialized_views() -> None:
    """Drop MV indexes and views that reference transactions."""
    for spec in reversed(ALL_VIEW_INDEX_SPECS):
        op.execute(sa.text(f'DROP INDEX IF EXISTS "{SCHEMA_NAME}"."{spec.name}"'))
    for entity in reversed(_HISTORICAL_VIEW_ENTITIES):
        op.execute(sa.text(f'DROP MATERIALIZED VIEW IF EXISTS "{SCHEMA_NAME}"."{entity.signature}" CASCADE'))


def _create_balance_materialized_views() -> None:
    """Recreate balance MVs and indexes against the partitioned ledger."""
    for entity in _HISTORICAL_VIEW_ENTITIES:
        op.create_entity(entity)
    for spec in ALL_VIEW_INDEX_SPECS:
        create_view_index(op, spec)


def upgrade() -> None:
    """Convert transactions to a monthly RANGE-partitioned parent table."""
    bind = op.get_bind()
    _drop_balance_materialized_views()
    op.execute(sa.text(f"ALTER TABLE {SCHEMA_NAME}.{TRANSACTIONS__TABLENAME} RENAME TO {LEGACY_TABLE_NAME}"))
    op.execute(sa.text(create_parent_partitioned_table_sql()))
    start, end = migration_partition_bounds(bind, legacy_table=LEGACY_TABLE_NAME)
    ensure_monthly_partitions(bind, start=start, end=end)
    op.execute(
        sa.text(f"INSERT INTO {SCHEMA_NAME}.{TRANSACTIONS__TABLENAME} SELECT * FROM {SCHEMA_NAME}.{LEGACY_TABLE_NAME}")
    )
    op.execute(sa.text(f"DROP TABLE {SCHEMA_NAME}.{LEGACY_TABLE_NAME}"))
    op.execute(sa.text(add_transactions_check_constraint_sql()))
    for index_sql in create_transactions_indexes_sql():
        op.execute(sa.text(index_sql))
    _create_balance_materialized_views()
    op.execute(sa.text("COMMIT"))


def downgrade() -> None:
    """Restore a single-table transactions relation with PK(id)."""
    _drop_balance_materialized_views()
    op.execute(sa.text(create_non_partitioned_table_sql(table_name=STAGING_TABLE_NAME)))
    op.execute(
        sa.text(f"INSERT INTO {SCHEMA_NAME}.{STAGING_TABLE_NAME} SELECT * FROM {SCHEMA_NAME}.{TRANSACTIONS__TABLENAME}")
    )
    op.execute(sa.text(f"DROP TABLE {SCHEMA_NAME}.{TRANSACTIONS__TABLENAME} CASCADE"))
    op.execute(sa.text(f"ALTER TABLE {SCHEMA_NAME}.{STAGING_TABLE_NAME} RENAME TO {TRANSACTIONS__TABLENAME}"))
    op.execute(sa.text(add_transactions_check_constraint_sql()))
    for index_sql in create_legacy_transactions_indexes_sql():
        op.execute(sa.text(index_sql))
    _create_balance_materialized_views()
