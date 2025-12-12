"""Unit tests for the upsert module in the Papita Transactions system.

This test suite validates database upsert operations including conflict handling,
dialect-specific implementations, and factory pattern. All database connections
and operations are mocked to ensure test isolation and prevent actual database access.
"""

from unittest.mock import MagicMock, Mock, PropertyMock, patch

import pandas as pd
import pytest
from sqlalchemy import Table
from sqlalchemy.orm import DeclarativeMeta
from sqlmodel import Session

from papita_txnsmodel.database.upsert import (
    DuckDBUpserter,
    OnUpsertConflictDo,
    PostgreSQLUpserter,
    Upserter,
    UpserterFactory,
)


@pytest.fixture
def mock_session():
    """Provide a mocked SQLModel session for database operations testing."""
    session = MagicMock(spec=Session)
    mock_bind = MagicMock()
    mock_dialect = MagicMock()
    mock_dialect.name = "postgresql"
    mock_bind.dialect = mock_dialect
    session.bind = mock_bind
    session.commit = MagicMock()
    return session


@pytest.fixture
def mock_engine():
    """Provide a mocked SQLAlchemy engine/connection for connection testing."""
    engine = MagicMock()
    engine.execute = MagicMock()
    return engine


@pytest.fixture
def sample_dataframe():
    """Provide a sample DataFrame for upsert operations testing."""
    return pd.DataFrame({"id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"], "value": [10, 20, 30]})


@pytest.fixture
def mock_table():
    """Provide a mocked SQLAlchemy Table object for testing."""
    table = MagicMock(spec=Table)
    table.table_name = "test_table"
    table.columns = [MagicMock(key="id"), MagicMock(key="name"), MagicMock(key="value")]
    return table


@pytest.fixture
def mock_declarative_meta():
    """Provide a mocked DeclarativeMeta class for testing."""
    meta = MagicMock(spec=DeclarativeMeta)
    meta.__tablename__ = "test_table"
    mock_table_obj = MagicMock()
    mock_table_obj.c = [MagicMock(key="id"), MagicMock(key="name"), MagicMock(key="value")]
    meta.__table__ = mock_table_obj
    return meta


class TestOnUpsertConflictDo:
    """Test suite for OnUpsertConflictDo enum."""

    def test_enum_has_nothing_value(self):
        """Test that OnUpsertConflictDo enum has NOTHING value."""
        assert OnUpsertConflictDo.NOTHING.value == "NOTHING"

    def test_enum_has_update_value(self):
        """Test that OnUpsertConflictDo enum has UPDATE value."""
        assert OnUpsertConflictDo.UPDATE.value == "UPDATE"


class TestUpserter:
    """Test suite for Upserter base class."""

    def test_upsert_raises_assertion_error_for_unsupported_dialect(self, mock_session, sample_dataframe):
        """Test that upsert raises AssertionError when dialect is not supported."""
        mock_session.bind.dialect.name = "mysql"
        with pytest.raises(AssertionError, match="Dialect not supported"):
            Upserter.upsert(
                schema_name="test_schema",
                table="test_table",
                pks=["id"],
                df=sample_dataframe,
                db_session=mock_session,
            )

    def test_upsert_handles_string_table_name(self, mock_session, sample_dataframe):
        """Test that upsert correctly handles string table name."""
        Upserter.__supported_dialect__ = "postgresql"
        with patch.object(Upserter, "_upsert_fallback", return_value=3) as mock_fallback:
            result = Upserter.upsert(
                schema_name="test_schema",
                table="test_table",
                pks=["id"],
                df=sample_dataframe,
                db_session=mock_session,
            )
            assert result == 3
            mock_fallback.assert_called_once()
        Upserter.__supported_dialect__ = ""

    def test_upsert_handles_table_object(self, mock_session, sample_dataframe, mock_table):
        """Test that upsert correctly handles SQLAlchemy Table object."""
        Upserter.__supported_dialect__ = "postgresql"
        with patch.object(Upserter, "_upsert_fallback", return_value=3) as mock_fallback:
            result = Upserter.upsert(
                schema_name="test_schema",
                table=mock_table,
                pks=["id"],
                df=sample_dataframe,
                db_session=mock_session,
            )
            assert result == 3
            mock_fallback.assert_called_once()
        Upserter.__supported_dialect__ = ""

    def test_upsert_handles_declarative_meta(self, mock_session, sample_dataframe, mock_declarative_meta):
        """Test that upsert correctly handles DeclarativeMeta object."""
        Upserter.__supported_dialect__ = "postgresql"
        with patch.object(Upserter, "_upsert_fallback", return_value=3) as mock_fallback:
            result = Upserter.upsert(
                schema_name="test_schema",
                table=mock_declarative_meta,
                pks=["id"],
                df=sample_dataframe,
                db_session=mock_session,
            )
            assert result == 3
            mock_fallback.assert_called_once()
        Upserter.__supported_dialect__ = ""

    def test_upsert_raises_type_error_for_unsupported_table_type(self, mock_session, sample_dataframe):
        """Test that upsert raises TypeError for unsupported table types."""
        Upserter.__supported_dialect__ = "postgresql"
        with pytest.raises(TypeError, match="Table type not supported"):
            Upserter.upsert(
                schema_name="test_schema",
                table=12345,
                pks=["id"],
                df=sample_dataframe,
                db_session=mock_session,
            )
        Upserter.__supported_dialect__ = ""

    def test_upsert_fallback_raises_type_error_when_method_not_set(self, mock_session, sample_dataframe, mock_table):
        """Test that _upsert_fallback raises TypeError when upsert method is not set."""
        Upserter._upsert_method = None
        with patch("papita_txnsmodel.database.upsert.slice_batches", return_value=[]):
            with pytest.raises(TypeError, match="There is no method set for upserting"):
                Upserter._upsert_fallback(
                    schema_name="test_schema",
                    table_name="test_table",
                    table=mock_table,
                    columns=["id", "name", "value"],
                    df=sample_dataframe,
                    db_session=mock_session,
                )

    def test_on_conflict_do_nothing_raises_not_implemented_error(self, mock_engine):
        """Test that base _on_conflict_do_nothing raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            Upserter._on_conflict_do_nothing(Mock(), mock_engine, ["id"], iter([]))

    def test_on_conflict_do_update_raises_not_implemented_error(self, mock_engine):
        """Test that base _on_conflict_do_update raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            Upserter._on_conflict_do_update(Mock(), mock_engine, ["id"], iter([]))


class TestPostgreSQLUpserter:
    """Test suite for PostgreSQLUpserter class."""

    @patch("papita_txnsmodel.database.upsert.PostgreSQLUpserter._insert")
    def test_on_conflict_do_nothing_executes_statement(self, mock_insert, mock_engine):
        """Test that _on_conflict_do_nothing executes PostgreSQL insert statement."""
        PostgreSQLUpserter._pks = {"id"}
        mock_table = MagicMock()
        mock_table.table = mock_table
        mock_stmt = MagicMock()
        mock_insert.return_value = mock_stmt
        mock_stmt.values.return_value = mock_stmt
        mock_stmt.on_conflict_do_nothing.return_value = mock_stmt
        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_engine.execute.return_value = mock_result
        data_iter = iter([{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}])

        result = PostgreSQLUpserter._on_conflict_do_nothing(mock_table, mock_engine, ["id", "name"], data_iter)

        assert result == 2
        mock_engine.execute.assert_called_once()

    @patch("papita_txnsmodel.database.upsert.PostgreSQLUpserter._insert")
    def test_on_conflict_do_nothing_handles_row_dict_conversion(self, mock_insert, mock_engine):
        """Test that _on_conflict_do_nothing handles row dictionary conversion."""
        PostgreSQLUpserter._pks = {"id"}
        mock_table = MagicMock()
        mock_table.table = mock_table
        mock_stmt = MagicMock()
        mock_insert.return_value = mock_stmt
        mock_stmt.values.return_value = mock_stmt
        mock_stmt.on_conflict_do_nothing.return_value = mock_stmt
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_engine.execute.return_value = mock_result
        mock_row = MagicMock()
        mock_row.to_dict = MagicMock(return_value={"id": 1, "name": "Alice"})
        data_iter = iter([mock_row])

        result = PostgreSQLUpserter._on_conflict_do_nothing(mock_table, mock_engine, ["id", "name"], data_iter)

        assert result == 1

    @patch("papita_txnsmodel.database.upsert.PostgreSQLUpserter._insert")
    def test_on_conflict_do_nothing_returns_negative_one_on_error(self, mock_insert, mock_engine):
        """Test that _on_conflict_do_nothing returns -1 when accessing rowcount fails."""
        PostgreSQLUpserter._pks = {"id"}
        mock_table = MagicMock()
        mock_table.table = mock_table
        mock_stmt = MagicMock()
        mock_insert.return_value = mock_stmt
        mock_stmt.values.return_value = mock_stmt
        mock_stmt.on_conflict_do_nothing.return_value = mock_stmt
        mock_result = MagicMock()
        type(mock_result).rowcount = PropertyMock(side_effect=Exception("Database error"))
        mock_engine.execute.return_value = mock_result
        data_iter = iter([{"id": 1, "name": "Alice"}])

        result = PostgreSQLUpserter._on_conflict_do_nothing(mock_table, mock_engine, ["id", "name"], data_iter)

        assert result == -1

    @patch("papita_txnsmodel.database.upsert.PostgreSQLUpserter._insert")
    def test_on_conflict_do_update_executes_update_statement(self, mock_insert, mock_engine):
        """Test that _on_conflict_do_update executes PostgreSQL update statement."""
        PostgreSQLUpserter._pks = {"id"}
        mock_table = MagicMock()
        mock_table.table = mock_table
        mock_stmt = MagicMock()
        mock_insert.return_value = mock_stmt
        mock_stmt.values.return_value = mock_stmt
        mock_stmt.excluded = MagicMock()
        mock_stmt.excluded.keys.return_value = ["id", "name", "value"]
        mock_stmt.on_conflict_do_update.return_value = mock_stmt
        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_engine.execute.return_value = mock_result
        data_iter = iter([{"id": 1, "name": "Alice", "value": 10}, {"id": 2, "name": "Bob", "value": 20}])

        result = PostgreSQLUpserter._on_conflict_do_update(mock_table, mock_engine, ["id", "name", "value"], data_iter)

        assert result == 2
        mock_engine.execute.assert_called_once()

    @patch("papita_txnsmodel.database.upsert.PostgreSQLUpserter._insert")
    def test_on_conflict_do_update_returns_negative_one_on_error(self, mock_insert, mock_engine):
        """Test that _on_conflict_do_update returns -1 when accessing rowcount fails."""
        PostgreSQLUpserter._pks = {"id"}
        mock_table = MagicMock()
        mock_table.table = mock_table
        mock_stmt = MagicMock()
        mock_insert.return_value = mock_stmt
        mock_stmt.values.return_value = mock_stmt
        mock_stmt.excluded = MagicMock()
        mock_stmt.excluded.keys.return_value = ["id", "name"]
        mock_stmt.on_conflict_do_update.return_value = mock_stmt
        mock_result = MagicMock()
        type(mock_result).rowcount = PropertyMock(side_effect=Exception("Database error"))
        mock_engine.execute.return_value = mock_result
        data_iter = iter([{"id": 1, "name": "Alice"}])

        result = PostgreSQLUpserter._on_conflict_do_update(mock_table, mock_engine, ["id", "name"], data_iter)

        assert result == -1


class TestDuckDBUpserter:
    """Test suite for DuckDBUpserter class."""

    def test_duckdb_upserter_has_correct_dialect(self):
        """Test that DuckDBUpserter has correct supported dialect."""
        assert DuckDBUpserter.__supported_dialect__ == "duckdb"

    def test_duckdb_upserter_inherits_from_postgres_upserter(self):
        """Test that DuckDBUpserter inherits from PostgreSQLUpserter."""
        assert issubclass(DuckDBUpserter, PostgreSQLUpserter)


class TestUpserterFactory:
    """Test suite for UpserterFactory class."""

    def test_get_upserter_returns_postgres_upserter_for_postgresql(self, mock_session):
        """Test that get_upserter returns PostgreSQLUpserter for PostgreSQL dialect."""
        mock_session.bind.dialect.name = "postgresql"
        result = UpserterFactory.get_upserter(mock_session)
        assert result == PostgreSQLUpserter

    def test_get_upserter_returns_duckdb_upserter_for_duckdb(self, mock_session):
        """Test that get_upserter returns DuckDBUpserter for DuckDB dialect."""
        mock_session.bind.dialect.name = "duckdb"
        result = UpserterFactory.get_upserter(mock_session)
        assert result == DuckDBUpserter

    def test_get_upserter_handles_case_insensitive_dialect(self, mock_session):
        """Test that get_upserter handles case-insensitive dialect matching."""
        mock_session.bind.dialect.name = "POSTGRESQL"
        result = UpserterFactory.get_upserter(mock_session)
        assert result == PostgreSQLUpserter

    def test_get_upserter_raises_value_error_for_unsupported_dialect(self, mock_session):
        """Test that get_upserter raises ValueError for unsupported dialects."""
        mock_session.bind.dialect.name = "mysql"
        with pytest.raises(ValueError, match="Unsupported dialect: mysql"):
            UpserterFactory.get_upserter(mock_session)
