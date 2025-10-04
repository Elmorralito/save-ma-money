"""
Unit tests for the database connector module.

This module tests the SQLDatabaseConnector class which manages database connections
using SQLAlchemy. It covers connection establishment, connection status checking,
session handling, and connection closing functionality.
"""

import os
import logging
from pathlib import Path
from unittest import mock

import pytest
import sqlalchemy as db
from sqlmodel import Session

from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.classutils import FallbackAction


@pytest.fixture
def reset_connector():
    """
    Reset SQLDatabaseConnector class state before and after each test.

    This fixture ensures tests don't affect each other by resetting the class-level
    attributes of SQLDatabaseConnector and restoring them after the test completes.
    """
    # Save original state
    original_engine = getattr(SQLDatabaseConnector, 'engine', None)
    original_sql_kwargs = getattr(SQLDatabaseConnector, 'sql_kwargs', {})

    # Reset state for test
    SQLDatabaseConnector.engine = None
    SQLDatabaseConnector.sql_kwargs = {}

    yield

    # Restore original state
    SQLDatabaseConnector.engine = original_engine
    SQLDatabaseConnector.sql_kwargs = original_sql_kwargs


@pytest.fixture
def mock_engine():
    """Create a mock SQLAlchemy engine for testing."""
    mock_engine = mock.MagicMock(spec=db.Engine)
    return mock_engine


def test_new_initializes_class_attributes():
    """Test that __new__ initializes class attributes correctly."""
    connector = SQLDatabaseConnector(sql_kwargs={"echo": True})

    assert connector.engine is None
    assert connector.sql_kwargs == {"echo": True}


@mock.patch('sqlalchemy.create_engine')
def test_establish_with_url_object(mock_create_engine, reset_connector):
    """Test establishing connection with a SQLAlchemy URL object."""
    url = db.URL.create(
        drivername="duckdb",
        database=":memory:"
    )
    mock_create_engine.return_value = mock.MagicMock(spec=db.Engine)

    connector = SQLDatabaseConnector.establish(connection=url)
    assert connector.connected()



@mock.patch('sqlalchemy.create_engine')
def test_establish_with_dict_params(mock_create_engine, reset_connector):
    """Test establishing connection with a dictionary of connection parameters."""
    connection_dict = {
        "drivername": "postgresql",
        "username": "user",
        "password": "pass",
        "host": "localhost",
        "port": 5432,
        "database": "testdb"
    }
    mock_create_engine.return_value = mock.MagicMock(spec=db.Engine)

    connector = SQLDatabaseConnector.establish(connection=connection_dict)

    mock_create_engine.assert_called_once()
    assert connector.engine is not None


@mock.patch('sqlalchemy.create_engine')
def test_establish_with_sql_kwargs(mock_create_engine, reset_connector):
    """Test establishing connection with SQL kwargs."""
    url = f"duckdb:///{os.path.join(os.path.abspath(os.getcwd()), 'test', 'path')}"
    sql_kwargs = {"echo": True}
    mock_engine = mock.MagicMock(spec=db.Engine)
    mock_create_engine.return_value = mock_engine

    connector = SQLDatabaseConnector.establish(connection=url, **sql_kwargs)

    mock_create_engine.assert_called_once()
    assert 'echo' in mock_create_engine.call_args[1]
    assert mock_create_engine.call_args[1]['echo'] is True
    assert connector.engine is mock_engine


@mock.patch('sqlalchemy.create_engine')
def test_establish_duckdb_default_kwargs(mock_create_engine, reset_connector):
    """Test establishing DuckDB connection uses default kwargs when none provided."""
    url = mock.MagicMock(spec=db.URL)
    url.drivername = "duckdb"
    mock_engine = mock.MagicMock(spec=db.Engine)
    mock_create_engine.return_value = mock_engine

    connector = SQLDatabaseConnector.establish(connection=url)

    mock_create_engine.assert_called_once()
    assert 'connect_args' in mock_create_engine.call_args[1]
    assert mock_create_engine.call_args[1]['connect_args'] == {"read_only": False}
    assert connector.engine is mock_engine


def test_close_success(reset_connector, mock_engine):
    """Test successful closing of database connection."""
    SQLDatabaseConnector.engine = mock_engine

    with mock.patch.object(SQLDatabaseConnector, 'connected', return_value=True):
        SQLDatabaseConnector.close()

        mock_engine.dispose.assert_called_once_with(close=True)


def test_connected_with_engine(reset_connector, mock_engine):
    """Test connected method when engine is available."""
    SQLDatabaseConnector.engine = mock_engine

    result = SQLDatabaseConnector.connected()

    assert result is True


def test_connected_raises_exception(reset_connector):
    """Test connected method with RAISE fallback action."""
    with pytest.raises(Exception):
        SQLDatabaseConnector.connected(on_disconnected=FallbackAction.RAISE)


def test_connect_decorator(reset_connector, mock_engine):
    """Test connect decorator wraps function with database session."""
    SQLDatabaseConnector.engine = mock_engine

    # Create a mock session
    mock_session = mock.MagicMock(spec=Session)

    # Mock Session context manager
    mock_session_cm = mock.MagicMock()
    mock_session_cm.__enter__.return_value = mock_session
    mock_session_cm.__exit__.return_value = None

    with mock.patch('sqlmodel.Session', return_value=mock_session_cm):
        with mock.patch.object(SQLDatabaseConnector, 'connected', return_value=True):
            # Define a function to decorate
            class TestClass:
                @SQLDatabaseConnector.connect
                def test_func(self, arg1, _db_session=None):
                    return f"Result: {arg1}, session: {_db_session}"

            # Test the decorated function
            test_instance = TestClass()
            result = test_instance.test_func("test_arg")
            assert "Result: test_arg, session:" in result


def test_connect_decorator_with_testing_mode(reset_connector, mock_engine):
    """Test connect decorator with _testing_ flag uses provided session."""
    SQLDatabaseConnector.engine = mock_engine

    # Create mock sessions
    real_session = mock.MagicMock(name="real_session")
    mock_session = mock.MagicMock(name="mock_session")

    # Mock Session context manager
    session_cm = mock.MagicMock()
    session_cm.__enter__.return_value = real_session
    session_cm.__exit__.return_value = None

    with mock.patch('sqlmodel.Session', return_value=session_cm):
        with mock.patch.object(SQLDatabaseConnector, 'connected', return_value=True):
            # Define a function to decorate
            class TestClass:
                @SQLDatabaseConnector.connect
                def test_func(self, arg1, _db_session=None, **kwargs):
                    return f"Result: {arg1}, session: {_db_session}"

            # Test with _testing_ flag and mock session
            test_instance = TestClass()
            result = test_instance.test_func("test_arg", _db_session=mock_session, _testing_=True)

            assert "Result: test_arg, session:" in result
            assert str(mock_session) in result
            assert str(real_session) not in result


def test_connect_decorator_disconnected(reset_connector):
    """Test connect decorator raises exception when not connected."""
    class TestClass:
        @SQLDatabaseConnector.connect
        def test_func(self, arg1, _db_session=None):
            return f"Result: {arg1}, session: {_db_session}"

    with mock.patch.object(SQLDatabaseConnector, 'connected', side_effect=Exception("Not connected")):
        test_instance = TestClass()
        with pytest.raises(Exception, match="Not connected"):
            test_instance.test_func("test_arg")
