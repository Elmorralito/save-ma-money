"""Monthly RANGE partitioning utilities for papita_transactions.transactions."""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterator

from sqlalchemy import text
from sqlalchemy.engine import Connection

from papita_txnsmodel.model.contstants import SCHEMA_NAME, TRANSACTIONS__TABLENAME

RETENTION_YEARS = 10
FUTURE_MONTHS_BUFFER = 12
PARTITION_TABLE_PATTERN = re.compile(r"^transactions_y(\d{4})m(\d{2})$")
LEGACY_TABLE_NAME = "transactions_legacy_pre_partition"
STAGING_TABLE_NAME = "transactions_unpartitioned_staging"


@dataclass(frozen=True)
class MonthlyPartitionSpec:
    """One monthly partition bound for the transactions ledger."""

    table_name: str
    year: int
    month: int
    start: date
    end: date


def month_start(value: date) -> date:
    """Return the first day of the month for a calendar date."""
    return date(value.year, value.month, 1)


def add_months(value: date, months: int) -> date:
    """Shift a calendar date by a number of months (day clamped to month end)."""
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def partition_table_name(*, year: int, month: int) -> str:
    """Build the child partition table name for a year/month."""
    return f"transactions_y{year:04d}m{month:02d}"


def is_transactions_partition_table(name: str) -> bool:
    """Return True when ``name`` is a monthly transactions child partition."""
    return PARTITION_TABLE_PATTERN.match(name) is not None


def partition_window(*, reference: date | None = None) -> tuple[date, date]:
    """Inclusive month start and exclusive upper month start for partition coverage."""
    anchor = month_start(reference or date.today())
    start = add_months(anchor, -(RETENTION_YEARS * 12))
    end = add_months(anchor, FUTURE_MONTHS_BUFFER + 1)
    return start, end


def iter_monthly_partitions(*, start: date, end: date) -> Iterator[MonthlyPartitionSpec]:
    """Yield monthly partition specs from ``start`` through ``end`` (exclusive)."""
    cursor = month_start(start)
    exclusive_end = month_start(end)
    while cursor < exclusive_end:
        next_month = add_months(cursor, 1)
        yield MonthlyPartitionSpec(
            table_name=partition_table_name(year=cursor.year, month=cursor.month),
            year=cursor.year,
            month=cursor.month,
            start=cursor,
            end=next_month,
        )
        cursor = next_month


def create_partition_sql(spec: MonthlyPartitionSpec) -> str:
    """Return DDL to create one monthly child partition."""
    return (
        f"CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.{spec.table_name} "
        f"PARTITION OF {SCHEMA_NAME}.{TRANSACTIONS__TABLENAME} "
        f"FOR VALUES FROM ('{spec.start.isoformat()}') TO ('{spec.end.isoformat()}');"
    )


def drop_partition_sql(spec: MonthlyPartitionSpec) -> str:
    """Return DDL to drop one monthly child partition."""
    return f"DROP TABLE IF EXISTS {SCHEMA_NAME}.{spec.table_name};"


def create_parent_partitioned_table_sql() -> str:
    """Return DDL for the partitioned transactions parent table."""
    return f"""
CREATE TABLE {SCHEMA_NAME}.{TRANSACTIONS__TABLENAME} (
    active BOOLEAN NOT NULL,
    deleted_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    id UUID NOT NULL,
    owner_id UUID NOT NULL,
    transaction_kind {SCHEMA_NAME}.transaction_kind NOT NULL,
    amount NUMERIC(22, 8) NOT NULL,
    currency CHAR(3) NOT NULL,
    transaction_ts TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    from_account_id UUID,
    to_account_id UUID,
    category_id UUID,
    template_id UUID,
    status {SCHEMA_NAME}.transaction_status NOT NULL,
    description TEXT NOT NULL,
    reference_number VARCHAR(64),
    tags VARCHAR[] NOT NULL,
    PRIMARY KEY (id, transaction_ts),
    CONSTRAINT transactions_owner_id_fkey FOREIGN KEY (owner_id)
        REFERENCES {SCHEMA_NAME}.users (id),
    CONSTRAINT transactions_category_id_fkey FOREIGN KEY (category_id)
        REFERENCES {SCHEMA_NAME}.categories (id),
    CONSTRAINT transactions_from_account_id_fkey FOREIGN KEY (from_account_id)
        REFERENCES {SCHEMA_NAME}.accounts (id),
    CONSTRAINT transactions_to_account_id_fkey FOREIGN KEY (to_account_id)
        REFERENCES {SCHEMA_NAME}.accounts (id),
    CONSTRAINT transactions_template_id_fkey FOREIGN KEY (template_id)
        REFERENCES {SCHEMA_NAME}.transaction_templates (id)
) PARTITION BY RANGE (transaction_ts);
"""


def create_non_partitioned_table_sql(*, table_name: str = TRANSACTIONS__TABLENAME) -> str:
    """Return DDL for a legacy single-table transactions relation (downgrade path)."""
    return f"""
CREATE TABLE {SCHEMA_NAME}.{table_name} (
    active BOOLEAN NOT NULL,
    deleted_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    id UUID NOT NULL,
    owner_id UUID NOT NULL,
    transaction_kind {SCHEMA_NAME}.transaction_kind NOT NULL,
    amount NUMERIC(22, 8) NOT NULL,
    currency CHAR(3) NOT NULL,
    transaction_ts TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    from_account_id UUID,
    to_account_id UUID,
    category_id UUID,
    template_id UUID,
    status {SCHEMA_NAME}.transaction_status NOT NULL,
    description TEXT NOT NULL,
    reference_number VARCHAR(64),
    tags VARCHAR[] NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT transactions_owner_id_fkey FOREIGN KEY (owner_id)
        REFERENCES {SCHEMA_NAME}.users (id),
    CONSTRAINT transactions_category_id_fkey FOREIGN KEY (category_id)
        REFERENCES {SCHEMA_NAME}.categories (id),
    CONSTRAINT transactions_from_account_id_fkey FOREIGN KEY (from_account_id)
        REFERENCES {SCHEMA_NAME}.accounts (id),
    CONSTRAINT transactions_to_account_id_fkey FOREIGN KEY (to_account_id)
        REFERENCES {SCHEMA_NAME}.accounts (id),
    CONSTRAINT transactions_template_id_fkey FOREIGN KEY (template_id)
        REFERENCES {SCHEMA_NAME}.transaction_templates (id)
);
"""


def add_transactions_check_constraint_sql() -> str:
    """Return DDL for the v3 transaction kind/account check constraint."""
    return f"""
ALTER TABLE {SCHEMA_NAME}.{TRANSACTIONS__TABLENAME}
ADD CONSTRAINT chk_transaction_kind_accounts CHECK (
    (transaction_kind = 'INCOME' AND from_account_id IS NULL AND to_account_id IS NOT NULL
        AND category_id IS NOT NULL)
    OR (transaction_kind = 'EXPENSE' AND from_account_id IS NOT NULL AND to_account_id IS NULL
        AND category_id IS NOT NULL)
    OR (
        transaction_kind = 'TRANSFER'
        AND from_account_id IS NOT NULL
        AND to_account_id IS NOT NULL
        AND category_id IS NULL
        AND from_account_id <> to_account_id
    )
);
"""


def create_legacy_transactions_indexes_sql() -> list[str]:
    """Return index DDL for the pre-partition single-table transactions relation."""
    table = f"{SCHEMA_NAME}.{TRANSACTIONS__TABLENAME}"
    return [
        f"CREATE INDEX IF NOT EXISTS ix_papita_transactions_transactions_owner_id ON {table} (owner_id);",
        f"CREATE INDEX IF NOT EXISTS ix_papita_transactions_transactions_transaction_ts ON {table} (transaction_ts);",
        f"CREATE INDEX IF NOT EXISTS ix_transactions_owner_active_status ON {table} (owner_id, active, status);",
        f"CREATE INDEX IF NOT EXISTS ix_transactions_owner_transaction_ts ON {table} (owner_id, transaction_ts);",
        f"CREATE INDEX IF NOT EXISTS ix_transactions_from_account_id ON {table} (from_account_id);",
        f"CREATE INDEX IF NOT EXISTS ix_transactions_to_account_id ON {table} (to_account_id);",
        f"CREATE INDEX IF NOT EXISTS ix_transactions_category_id ON {table} (category_id);",
    ]


def create_transactions_indexes_sql() -> list[str]:
    """Return index DDL statements for the transactions parent table."""
    table = f"{SCHEMA_NAME}.{TRANSACTIONS__TABLENAME}"
    return [
        f"CREATE INDEX IF NOT EXISTS ix_papita_transactions_transactions_owner_id ON {table} (owner_id);",
        f"CREATE INDEX IF NOT EXISTS ix_papita_transactions_transactions_transaction_ts ON {table} (transaction_ts);",
        f"CREATE INDEX IF NOT EXISTS ix_transactions_owner_active_status ON {table} (owner_id, active, status);",
        f"CREATE INDEX IF NOT EXISTS ix_transactions_owner_transaction_ts ON {table} (owner_id, transaction_ts);",
        f"CREATE INDEX IF NOT EXISTS ix_transactions_from_account_id ON {table} (from_account_id);",
        f"CREATE INDEX IF NOT EXISTS ix_transactions_to_account_id ON {table} (to_account_id);",
        f"CREATE INDEX IF NOT EXISTS ix_transactions_category_id ON {table} (category_id);",
        f"CREATE INDEX IF NOT EXISTS ix_transactions_id ON {table} (id);",
    ]


def partition_exists(connection: Connection, *, table_name: str) -> bool:
    """Return True when a child partition table already exists."""
    result = connection.execute(
        text("""
            SELECT 1
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = :schema
              AND c.relname = :table_name
            """),
        {"schema": SCHEMA_NAME, "table_name": table_name},
    )
    return result.first() is not None


def ensure_monthly_partitions(
    connection: Connection,
    *,
    reference: date | None = None,
    start: date | None = None,
    end: date | None = None,
) -> list[str]:
    """Create missing monthly partitions within the requested month bounds."""
    window_start, window_end = partition_window(reference=reference)
    effective_start = start if start is not None else window_start
    effective_end = end if end is not None else window_end
    created: list[str] = []
    for spec in iter_monthly_partitions(start=effective_start, end=effective_end):
        if partition_exists(connection, table_name=spec.table_name):
            continue
        connection.execute(text(create_partition_sql(spec)))
        created.append(spec.table_name)
    return created


def migration_partition_bounds(connection: Connection, *, legacy_table: str) -> tuple[date, date]:
    """Expand the default partition window to cover all rows in a legacy table."""
    start, end = partition_window()
    result = connection.execute(
        text(f"SELECT MIN(transaction_ts), MAX(transaction_ts) FROM {SCHEMA_NAME}.{legacy_table}")
    )
    min_ts, max_ts = result.one()
    if min_ts is not None:
        start = min(start, month_start(min_ts.date() if isinstance(min_ts, datetime) else min_ts))
    if max_ts is not None:
        max_date = max_ts.date() if isinstance(max_ts, datetime) else max_ts
        end = max(end, add_months(month_start(max_date), 1))
    return start, end


def archive_expired_partitions(
    connection: Connection,
    *,
    reference: date | None = None,
    retention_years: int = RETENTION_YEARS,
) -> list[str]:
    """Detach and drop monthly partitions older than the retention window."""
    anchor = month_start(reference or date.today())
    cutoff = add_months(anchor, -(retention_years * 12))
    archived: list[str] = []

    result = connection.execute(
        text("""
            SELECT c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = :schema
              AND c.relkind = 'r'
              AND c.relname ~ '^transactions_y[0-9]{4}m[0-9]{2}$'
            ORDER BY c.relname
            """),
        {"schema": SCHEMA_NAME},
    )
    for (relname,) in result:
        match = PARTITION_TABLE_PATTERN.match(relname)
        if match is None:
            continue
        year = int(match.group(1))
        month = int(match.group(2))
        partition_start = date(year, month, 1)
        if partition_start >= cutoff:
            continue
        connection.execute(text(f"DROP TABLE IF EXISTS {SCHEMA_NAME}.{relname};"))
        archived.append(relname)
    return archived


def run_partition_maintenance(*, database_url: str, reference: datetime | None = None) -> dict[str, list[str]]:
    """Ensure future partitions exist and archive partitions beyond retention."""
    from sqlalchemy import create_engine

    ref_date = reference.date() if reference is not None else None
    engine = create_engine(database_url)
    with engine.begin() as connection:
        created = ensure_monthly_partitions(connection, reference=ref_date)
        archived = archive_expired_partitions(connection, reference=ref_date)
    return {"created_partitions": created, "archived_partitions": archived}
