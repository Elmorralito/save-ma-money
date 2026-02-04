"""Unit tests for the connector module in the Papita Transactions system.

This test suite validates database connection management including connection establishment,
session management, connection status checking, and cleanup. All database connections
are mocked to ensure test isolation and prevent actual database access.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
import sqlalchemy as db
from sqlmodel import Session

from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.enums import FallbackAction


@pytest.fixture
def mock_engine():
    """Provide a mocked SQLAlchemy engine for database connection testing."""
    engine = MagicMock(spec=db.Engine)
    engine.url = MagicMock()
    engine.url.drivername = "postgresql"
    engine.dispose = MagicMock()
    return engine


@pytest.fixture
def mock_session():
    """Provide a mocked SQLModel session for database operations testing."""
    session = MagicMock(spec=Session)
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    return session


@pytest.fixture
def reset_connector():
    """Reset SQLDatabaseConnector class-level attributes before and after each test."""
    original_engine = SQLDatabaseConnector.engine
    original_sql_kwargs = SQLDatabaseConnector.sql_kwargs
    SQLDatabaseConnector.engine = None
    SQLDatabaseConnector.sql_kwargs = None
    yield
    SQLDatabaseConnector.engine = original_engine
    SQLDatabaseConnector.sql_kwargs = original_sql_kwargs


class TestEstablish:
    """Test suite for SQLDatabaseConnector.establish method."""

    @patch("papita_txnsmodel.database.connector.db.create_engine")
    @patch("papita_txnsmodel.database.connector.db.make_url")
    def test_establish_with_none_connection_uses_default_path(self, mock_make_url, mock_create_engine, reset_connector):
        """Test that establish uses default .tmp path when connection is None."""
        mock_url = MagicMock()
        mock_url.drivername = "duckdb"
        mock_make_url.return_value = mock_url
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        result = SQLDatabaseConnector.establish(connection=None)

        assert result == SQLDatabaseConnector
        assert SQLDatabaseConnector.engine == mock_engine
        mock_create_engine.assert_called_once()

    @patch("papita_txnsmodel.database.connector.db.create_engine")
    @patch("papita_txnsmodel.database.connector.db.make_url")
    def test_establish_with_sqlalchemy_url_object(self, mock_make_url, mock_create_engine, reset_connector):
        """Test that establish correctly handles SQLAlchemy URL object."""
        mock_url = MagicMock(spec=db.URL)
        mock_url.drivername = "postgresql"
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        result = SQLDatabaseConnector.establish(connection=mock_url)

        assert result == SQLDatabaseConnector
        assert SQLDatabaseConnector.engine == mock_engine
        mock_create_engine.assert_called_once()

    @patch("papita_txnsmodel.database.connector.db.create_engine")
    @patch("papita_txnsmodel.database.connector.db.URL")
    def test_establish_with_dict_connection_creates_url(self, mock_url_class, mock_create_engine, reset_connector):
        """Test that establish correctly creates URL from dictionary connection parameters."""
        connection_dict = {
            "drivername": "postgresql",
            "username": "user",
            "password": "pass",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
        }
        mock_url = MagicMock()
        mock_url.drivername = "postgresql"
        mock_url_class.return_value = mock_url
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        result = SQLDatabaseConnector.establish(connection=connection_dict.copy())

        assert result == SQLDatabaseConnector
        assert SQLDatabaseConnector.engine == mock_engine
        mock_url_class.create.assert_called_once()

    @patch("papita_txnsmodel.database.connector.db.create_engine")
    @patch("papita_txnsmodel.database.connector.db.make_url")
    def test_establish_with_dict_containing_url_key(self, mock_make_url, mock_create_engine, reset_connector):
        """Test that establish uses url key from dictionary when present."""
        connection_dict = {"url": "postgresql://user:pass@localhost:5432/testdb"}
        mock_url = MagicMock()
        mock_url.drivername = "postgresql"
        mock_make_url.return_value = mock_url
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        result = SQLDatabaseConnector.establish(connection=connection_dict.copy())

        assert result == SQLDatabaseConnector
        assert SQLDatabaseConnector.engine == mock_engine

    @patch("papita_txnsmodel.database.connector.db.create_engine")
    @patch("papita_txnsmodel.database.connector.Path")
    @patch("papita_txnsmodel.database.connector.os.path.abspath")
    def test_establish_with_string_path_creates_duckdb_url(self, mock_abspath, mock_path_class, mock_create_engine, reset_connector):
        """Test that establish creates DuckDB URL from string file path."""
        mock_abspath.return_value = "/test/path"
        mock_path = MagicMock()
        mock_path.is_dir.return_value = False
        mock_path.absolute.return_value.as_posix.return_value = "/test/path/file.duckdb"
        mock_path_class.return_value = mock_path
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        result = SQLDatabaseConnector.establish(connection="/test/path/file.duckdb")

        assert result == SQLDatabaseConnector
        assert SQLDatabaseConnector.engine == mock_engine

    @patch("papita_txnsmodel.database.connector.db.create_engine")
    @patch("papita_txnsmodel.database.connector.db.make_url")
    def test_establish_with_unknown_type_uses_memory_duckdb(self, mock_make_url, mock_create_engine, reset_connector):
        """Test that establish defaults to in-memory DuckDB for unknown connection types."""
        mock_url = MagicMock()
        mock_url.drivername = "duckdb"
        mock_make_url.return_value = mock_url
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        result = SQLDatabaseConnector.establish(connection=12345)

        assert result == SQLDatabaseConnector
        mock_make_url.assert_called_once_with("duckdb:///:memory:")

    @patch("papita_txnsmodel.database.connector.db.create_engine")
    @patch("papita_txnsmodel.database.connector.db.make_url")
    def test_establish_merges_sql_kwargs(self, mock_make_url, mock_create_engine, reset_connector):
        """Test that establish correctly merges class-level and method-level sql_kwargs."""
        SQLDatabaseConnector.sql_kwargs = {"pool_size": 5}
        mock_url = MagicMock()
        mock_url.drivername = "postgresql"
        mock_make_url.return_value = mock_url
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        result = SQLDatabaseConnector.establish(connection="postgresql://localhost/db", pool_timeout=10)

        assert result == SQLDatabaseConnector
        call_kwargs = mock_create_engine.call_args[1]
        assert "pool_size" in call_kwargs
        assert "pool_timeout" in call_kwargs

    @patch("papita_txnsmodel.database.connector.db.create_engine")
    @patch("papita_txnsmodel.database.connector.db.make_url")
    def test_establish_adds_duckdb_connect_args_when_missing(self, mock_make_url, mock_create_engine, reset_connector):
        """Test that establish adds default connect_args for DuckDB when sql_kwargs is empty."""
        mock_url = MagicMock()
        mock_url.drivername = "duckdb"
        mock_make_url.return_value = mock_url
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        result = SQLDatabaseConnector.establish(connection="duckdb:///test.db")

        assert result == SQLDatabaseConnector
        call_kwargs = mock_create_engine.call_args[1]
        assert "connect_args" in call_kwargs
        assert call_kwargs["connect_args"]["read_only"] is False


class TestClose:
    """Test suite for SQLDatabaseConnector.close method."""

    @patch("papita_txnsmodel.database.connector.SQLDatabaseConnector.connected")
    def test_close_disposes_engine_when_connected(self, mock_connected, mock_engine, reset_connector):
        """Test that close disposes engine when connection is established."""
        SQLDatabaseConnector.engine = mock_engine
        mock_connected.return_value = True

        SQLDatabaseConnector.close()

        mock_connected.assert_called_once_with(on_disconnected=FallbackAction.RAISE)
        mock_engine.dispose.assert_called_once_with(close=True)

    @patch("papita_txnsmodel.database.connector.SQLDatabaseConnector.connected")
    def test_close_handles_exception_when_not_connected(self, mock_connected, reset_connector):
        """Test that close handles exception gracefully when connection is not established."""
        SQLDatabaseConnector.engine = None
        mock_connected.side_effect = ValueError("Not connected")

        SQLDatabaseConnector.close()

        mock_connected.assert_called_once_with(on_disconnected=FallbackAction.RAISE)

    @patch("papita_txnsmodel.database.connector.SQLDatabaseConnector.connected")
    def test_close_handles_exception_during_dispose(self, mock_connected, mock_engine, reset_connector):
        """Test that close handles exception gracefully when engine disposal fails."""
        SQLDatabaseConnector.engine = mock_engine
        mock_connected.return_value = True
        mock_engine.dispose.side_effect = Exception("Dispose failed")

        SQLDatabaseConnector.close()

        mock_engine.dispose.assert_called_once()


class TestConnect:
    """Test suite for SQLDatabaseConnector.connect decorator."""

    @patch("papita_txnsmodel.database.connector.SQLDatabaseConnector.connected")
    @patch("papita_txnsmodel.database.connector.Session")
    def test_connect_decorator_provides_session(self, mock_session_class, mock_connected, mock_engine, mock_session, reset_connector):
        """Test that connect decorator provides database session to wrapped function."""
        SQLDatabaseConnector.engine = mock_engine
        mock_connected.return_value = True
        mock_session_class.return_value.__enter__.return_value = mock_session
        mock_session_class.return_value.__exit__.return_value = False

        @SQLDatabaseConnector.connect
        def test_function(self, _db_session, **kwargs):
            return _db_session

        result = test_function(Mock())

        assert result == mock_session
        mock_connected.assert_called_once_with(on_disconnected=FallbackAction.RAISE)
        mock_session_class.assert_called_once_with(mock_engine)

    @patch("papita_txnsmodel.database.connector.SQLDatabaseConnector.connected")
    @patch("papita_txnsmodel.database.connector.Session")
    def test_connect_decorator_uses_mock_session_when_testing(self, mock_session_class, mock_connected, mock_engine, mock_session, reset_connector):
        """Test that connect decorator uses provided mock session when _testing_ flag is set."""
        SQLDatabaseConnector.engine = mock_engine
        mock_connected.return_value = True
        provided_mock_session = MagicMock()
        provided_mock_session.__enter__.return_value = provided_mock_session
        provided_mock_session.__exit__.return_value = False

        @SQLDatabaseConnector.connect
        def test_function(self, _db_session, **kwargs):
            return _db_session

        result = test_function(Mock(), _db_session=provided_mock_session, _testing_=True)

        assert result == provided_mock_session

    @patch("papita_txnsmodel.database.connector.SQLDatabaseConnector.connected")
    def test_connect_decorator_raises_when_not_connected(self, mock_connected, reset_connector):
        """Test that connect decorator raises error when connection is not established."""
        SQLDatabaseConnector.engine = None
        mock_connected.side_effect = ValueError("Not connected")

        @SQLDatabaseConnector.connect
        def test_function(self, _db_session, **kwargs):
            return True

        with pytest.raises(ValueError, match="Not connected"):
            test_function(Mock())


class TestConnected:
    """Test suite for SQLDatabaseConnector.connected method."""

    def test_connected_returns_true_when_engine_exists(self, mock_engine, reset_connector):
        """Test that connected returns True when engine is established."""
        SQLDatabaseConnector.engine = mock_engine

        result = SQLDatabaseConnector.connected()

        assert result is True

    def test_connected_returns_false_when_engine_is_none(self, reset_connector):
        """Test that connected returns False when engine is not established."""
        SQLDatabaseConnector.engine = None

        result = SQLDatabaseConnector.connected()

        assert result is False

    def test_connected_returns_false_when_engine_is_not_engine_type(self, reset_connector):
        """Test that connected returns False when engine is not a db.Engine instance."""
        SQLDatabaseConnector.engine = "not_an_engine"

        result = SQLDatabaseConnector.connected()

        assert result is False

    def test_connected_handles_log_action_when_disconnected(self, reset_connector):
        """Test that connected handles LOG action when connection is not established."""
        SQLDatabaseConnector.engine = None

        result = SQLDatabaseConnector.connected(on_disconnected=FallbackAction.LOG)

        assert result is False

    def test_connected_handles_ignore_action_when_disconnected(self, reset_connector):
        """Test that connected handles IGNORE action when connection is not established."""
        SQLDatabaseConnector.engine = None

        result = SQLDatabaseConnector.connected(on_disconnected=FallbackAction.IGNORE)

        assert result is False

    def test_connected_raises_when_raise_action_and_disconnected(self, reset_connector):
        """Test that connected raises ValueError when RAISE action and connection is not established."""
        SQLDatabaseConnector.engine = None

        with pytest.raises(ValueError, match="The connection hasn't been established"):
            SQLDatabaseConnector.connected(on_disconnected=FallbackAction.RAISE)

    def test_connected_handles_string_fallback_action(self, reset_connector):
        """Test that connected correctly converts string to FallbackAction enum."""
        SQLDatabaseConnector.engine = None

        with pytest.raises(ValueError, match="The connection hasn't been established"):
            SQLDatabaseConnector.connected(on_disconnected="raise")
