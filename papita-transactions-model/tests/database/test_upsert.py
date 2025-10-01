"""
Unit tests for the upsert operations module.

This module tests the functionality of the upsert operations classes and methods
in the papita_txnsmodel.database.upsert module, focusing on:
1. UpserterFactory functionality
2. Basic upserting operations for different dialects
3. Error handling for unsupported dialects
"""

from unittest import mock
import pandas as pd
import pytest
from sqlalchemy import Column, MetaData, Table, create_engine, text
import sqlalchemy
from sqlalchemy.orm import declarative_base
from sqlmodel import Session

from papita_txnsmodel.database.upsert import (
    DuckDBUpserter,
    OnUpsertConflictDo,
    PostgreSQLUpserter,
    Upserter,
    UpserterFactory,
)


# Make sure pytest-mock is installed: pip install pytest-mock
# No need to import it directly, pytest will handle that

@pytest.fixture
def sample_dataframe():
    """Create a sample DataFrame for testing."""
    return pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["Alice", "Bob", "Charlie"],
        "age": [25, 30, 35],
    })


@pytest.fixture
def mock_table():
    """Create a mock SQLAlchemy table for testing."""
    Base = declarative_base()

    class Person(Base):
        __tablename__ = "person"
        id = Column(primary_key=True)
        name = Column()
        age = Column()

    return Person


@pytest.fixture
def mock_postgresql_session(monkeypatch):
    """Create a mock PostgreSQL session."""
    # Create a mock engine with PostgreSQL dialect
    engine = create_engine("postgresql://user:pass@localhost/dbname", echo=False)

    # Create a mock session
    mock_session = pytest.MockFixture.MagicMock()
    mock_session.bind = engine
    mock_session.commit = pytest.MockFixture.MagicMock()

    # Create a mock result with rowcount
    mock_result = pytest.MockFixture.MagicMock()
    mock_result.rowcount = 3
    mock_session.execute = pytest.MockFixture.MagicMock(return_value=mock_result)

    return mock_session


@pytest.fixture
def mock_duckdb_session(monkeypatch):
    """Create a mock DuckDB session."""
    # Create a mock engine with DuckDB dialect
    engine = create_engine("duckdb:///:memory:", echo=False)

    # Create a mock session
    mock_session = pytest.MockFixture.MagicMock()
    mock_session.bind = engine
    mock_session.commit = pytest.MockFixture.MagicMock()

    # Create a mock result with rowcount
    mock_result = pytest.MockFixture.MagicMock()
    mock_result.rowcount = 3
    mock_session.execute = pytest.MockFixture.MagicMock(return_value=mock_result)

    return mock_session


class TestUpserterFactory:
    """Tests for the UpserterFactory class."""

    def test_get_postgresql_upserter(self):
        """Test that the factory returns PostgreSQLUpserter for postgresql dialect."""
        engine = create_engine("postgresql://user:pass@localhost/dbname", echo=False)
        session = Session(engine)

        upserter = UpserterFactory.get_upserter(session)

        assert upserter == PostgreSQLUpserter
        assert upserter.__supported_dialect__ == "postgresql"

    def test_get_duckdb_upserter(self):
        """Test that the factory returns DuckDBUpserter for duckdb dialect."""
        engine = create_engine("duckdb:///:memory:", echo=False)
        session = Session(engine)

        upserter = UpserterFactory.get_upserter(session)

        assert upserter == DuckDBUpserter
        assert upserter.__supported_dialect__ == "duckdb"

    def test_unsupported_dialect(self):
        """Test that the factory raises an error for unsupported dialects."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        session = Session(engine)

        with pytest.raises(ValueError, match="Unsupported dialect: sqlite"):
            UpserterFactory.get_upserter(session)


class TestPostgreSQLUpserter:
    """Tests for the PostgreSQLUpserter class."""

    def test_postgresql_upsert_nothing(self, monkeypatch, sample_dataframe, mock_table):
        """Test PostgreSQL upsert with ON CONFLICT DO NOTHING."""
        # Mock the database connection
        mock_engine = mock.MagicMock()
        mock_engine.dialect.name = "postgresql"

        # Create a mock session
        mock_session = mock.MagicMock()
        mock_session.bind = mock_engine
        mock_session.commit = mock.MagicMock()

        # Mock the on_conflict_do_nothing method to avoid actual database operations
        original_method = PostgreSQLUpserter._on_conflict_do_nothing

        def mock_on_conflict_do_nothing(cls, table, conn, keys, data_iter):
            return 3

        monkeypatch.setattr(PostgreSQLUpserter, '_on_conflict_do_nothing', classmethod(mock_on_conflict_do_nothing))

        # Use _testing_ flag to utilize the mock session
        result = PostgreSQLUpserter.upsert(
            schema_name="public",
            table=mock_table,
            pks=["id"],
            df=sample_dataframe,
            db_session=mock_session,
            on_conflict_do=OnUpsertConflictDo.NOTHING,
            _testing_=True
        )

        assert result == 3
        mock_session.commit.assert_called_once()

        # Restore original method
        monkeypatch.setattr(PostgreSQLUpserter, '_on_conflict_do_nothing', original_method)



class TestDuckDBUpserter:
    """Tests for the DuckDBUpserter class."""

    def test_duckdb_upsert_update(self, monkeypatch, sample_dataframe, mock_table):
        """Test DuckDB upsert with ON CONFLICT DO UPDATE."""
        # Mock the database connection
        mock_engine = mock.MagicMock()
        mock_engine.dialect.name = "duckdb"

        # Create a mock session
        mock_session = mock.MagicMock()
        mock_session.bind = mock_engine
        mock_session.commit = mock.MagicMock()

        # Mock the on_conflict_do_update method to avoid actual database operations
        original_method = DuckDBUpserter._on_conflict_do_update

        def mock_on_conflict_do_update(cls, table, conn, keys, data_iter):
            return 3

        monkeypatch.setattr(DuckDBUpserter, '_on_conflict_do_update', classmethod(mock_on_conflict_do_update))

        # Use _testing_ flag to utilize the mock session
        result = DuckDBUpserter.upsert(
            schema_name="main",
            table=mock_table,
            pks=["id"],
            df=sample_dataframe,
            db_session=mock_session,
            on_conflict_do=OnUpsertConflictDo.UPDATE,
            _testing_=True
        )

        assert result == 3
        mock_session.commit.assert_called_once()

        # Restore original method
        monkeypatch.setattr(DuckDBUpserter, '_on_conflict_do_update', original_method)
