"""Tests for monthly transactions partition helpers."""

from datetime import date

from papita_txnsmodel.config.transaction_partitions import (
    RETENTION_YEARS,
    add_months,
    is_transactions_partition_table,
    iter_monthly_partitions,
    month_start,
    partition_table_name,
    partition_window,
)
from papita_txnsmodel.model.transactions import Transactions


class TestTransactionPartitionHelpers:
    """Partition naming and calendar helpers behave predictably."""

    def test_month_start_normalizes_to_first_day(self):
        """Month start always returns day 1."""
        assert month_start(date(2026, 7, 15)) == date(2026, 7, 1)

    def test_add_months_clamps_day_to_month_end(self):
        """Month arithmetic respects shorter months."""
        assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)

    def test_partition_table_name_pattern(self):
        """Child partitions use a stable yYYYYmMM suffix."""
        assert partition_table_name(year=2026, month=7) == "transactions_y2026m07"

    def test_is_transactions_partition_table(self):
        """Only monthly child tables match the partition regex."""
        assert is_transactions_partition_table("transactions_y2026m07") is True
        assert is_transactions_partition_table("transactions") is False

    def test_iter_monthly_partitions_covers_single_month(self):
        """Partition iteration yields one spec per month in the range."""
        specs = list(iter_monthly_partitions(start=date(2026, 7, 1), end=date(2026, 8, 1)))
        assert len(specs) == 1
        assert specs[0].table_name == "transactions_y2026m07"
        assert specs[0].start == date(2026, 7, 1)
        assert specs[0].end == date(2026, 8, 1)

    def test_partition_window_covers_retention_and_future_buffer(self):
        """Default window spans retention years plus future buffer months."""
        start, end = partition_window(reference=date(2026, 7, 15))
        assert start == add_months(date(2026, 7, 1), -(RETENTION_YEARS * 12))
        assert end > date(2026, 7, 1)


class TestTransactionsPartitionModel:
    """SQLModel metadata reflects PostgreSQL RANGE partitioning."""

    def test_transactions_uses_composite_primary_key(self):
        """Partitioned tables require the partition key in the primary key."""
        pk_columns = {column.name for column in Transactions.__table__.primary_key.columns}
        assert pk_columns == {"id", "transaction_ts"}

    def test_transactions_declares_range_partition(self):
        """Parent table metadata declares RANGE(transaction_ts)."""
        table_kwargs = Transactions.__table__.kwargs
        assert table_kwargs.get("postgresql_partition_by") == "RANGE (transaction_ts)"

    def test_transactions_has_id_lookup_index(self):
        """Non-unique id index supports repository lookups by id alone."""
        index_names = {index.name for index in Transactions.__table__.indexes}
        assert "ix_transactions_id" in index_names
