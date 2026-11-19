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
from papita_txnsmodel.model.contstants import SCHEMA_NAME, TRANSACTIONS__TABLENAME
from papita_txnsmodel.views import view_entities
from papita_txnsmodel.views.indexes import ALL_VIEW_INDEX_SPECS, create_view_index

revision: str = "g4b5c6d7e8f9"
down_revision: Union[str, Sequence[str], None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_balance_materialized_views() -> None:
    """Drop MV indexes and views that reference transactions."""
    for spec in reversed(ALL_VIEW_INDEX_SPECS):
        op.execute(sa.text(f'DROP INDEX IF EXISTS "{SCHEMA_NAME}"."{spec.name}"'))
    for entity in reversed(view_entities):
        op.execute(sa.text(f'DROP MATERIALIZED VIEW IF EXISTS "{SCHEMA_NAME}"."{entity.signature}" CASCADE'))


def _create_balance_materialized_views() -> None:
    """Recreate balance MVs and indexes against the partitioned ledger."""
    for entity in view_entities:
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
        sa.text(
            f"INSERT INTO {SCHEMA_NAME}.{TRANSACTIONS__TABLENAME} " f"SELECT * FROM {SCHEMA_NAME}.{LEGACY_TABLE_NAME}"
        )
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
        sa.text(
            f"INSERT INTO {SCHEMA_NAME}.{STAGING_TABLE_NAME} " f"SELECT * FROM {SCHEMA_NAME}.{TRANSACTIONS__TABLENAME}"
        )
    )
    op.execute(sa.text(f"DROP TABLE {SCHEMA_NAME}.{TRANSACTIONS__TABLENAME} CASCADE"))
    op.execute(sa.text(f"ALTER TABLE {SCHEMA_NAME}.{STAGING_TABLE_NAME} " f"RENAME TO {TRANSACTIONS__TABLENAME}"))
    op.execute(sa.text(add_transactions_check_constraint_sql()))
    for index_sql in create_legacy_transactions_indexes_sql():
        op.execute(sa.text(index_sql))
    _create_balance_materialized_views()
