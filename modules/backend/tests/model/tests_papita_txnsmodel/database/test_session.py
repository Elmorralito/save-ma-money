"""Unit tests for explicit SQLAlchemy Engine + Session DI (PPT-097)."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest
import sqlalchemy as db
from sqlmodel import Session

from papita_txnsmodel.database.session import (
    DatabaseSessionManager,
    close_database,
    configure_database,
    get_active_session,
    get_db,
    get_engine,
    get_session_manager,
    session_scope,
    with_session,
)
from papita_txnsmodel.utils.enums import FallbackAction


@pytest.fixture
def reset_manager():
    """Reset the default session manager before and after each test."""
    manager = get_session_manager()
    orig_engine = manager.engine
    orig_kwargs = manager.sql_kwargs
    orig_factory = manager.session_factory
    manager.engine = None
    manager.sql_kwargs = None
    manager.session_factory = None
    yield manager
    manager.engine = orig_engine
    manager.sql_kwargs = orig_kwargs
    manager.session_factory = orig_factory


class TestConfigureDatabase:
    """Test suite for DatabaseSessionManager.configure and configure_database."""

    @patch("papita_txnsmodel.database.session.db.create_engine")
    @patch("papita_txnsmodel.database.session.db.make_url")
    def test_configure_with_none_uses_in_memory_sqlite(
        self, mock_make_url: MagicMock, mock_create_engine: MagicMock, reset_manager: DatabaseSessionManager
    ) -> None:
        mock_url = MagicMock()
        mock_url.drivername = "sqlite"
        mock_make_url.return_value = mock_url
        mock_engine = MagicMock(spec=db.Engine)
        mock_create_engine.return_value = mock_engine

        result = configure_database(connection=None)

        assert result is reset_manager
        assert get_engine() is mock_engine
        mock_make_url.assert_called_once_with("sqlite:///:memory:")

    @patch("papita_txnsmodel.database.session.db.create_engine")
    def test_configure_with_url_object(
        self, mock_create_engine: MagicMock, reset_manager: DatabaseSessionManager
    ) -> None:
        mock_url = MagicMock(spec=db.URL)
        mock_url.drivername = "postgresql"
        mock_engine = MagicMock(spec=db.Engine)
        mock_create_engine.return_value = mock_engine

        result = configure_database(connection=mock_url)

        assert result is reset_manager
        assert reset_manager.engine is mock_engine

    def test_configure_with_invalid_string_raises(self, reset_manager: DatabaseSessionManager) -> None:
        del reset_manager
        with pytest.raises(ValueError, match="Unsupported database connection configuration"):
            configure_database(connection="/tmp/not_a_url.db")


class TestSessionScopeAndDI:
    """Test suite for session_scope, get_db, and @with_session."""

    def test_session_scope_binds_active_session_and_reuses_in_with_session(
        self, reset_manager: DatabaseSessionManager
    ) -> None:
        configure_database(connection="sqlite:///:memory:")

        @with_session
        def repo_op(_self: Any, *, _db_session: Session) -> Session:
            return _db_session

        with session_scope() as scoped:
            assert get_active_session() is scoped
            observed_1 = repo_op(Mock())
            observed_2 = repo_op(Mock())
            assert observed_1 is scoped
            assert observed_2 is scoped

        assert get_active_session() is None

    def test_get_db_generator_yields_request_scoped_session(
        self, reset_manager: DatabaseSessionManager
    ) -> None:
        configure_database(connection="sqlite:///:memory:")
        gen = get_db()
        session = next(gen)
        assert isinstance(session, Session)
        assert get_active_session() is session
        with pytest.raises(StopIteration):
            next(gen)
        assert get_active_session() is None

    def test_close_disposes_engine(self, reset_manager: DatabaseSessionManager) -> None:
        mock_engine = MagicMock(spec=db.Engine)
        reset_manager.engine = mock_engine
        close_database()
        mock_engine.dispose.assert_called_once_with(close=True)

    def test_connected_raises_when_engine_missing(self, reset_manager: DatabaseSessionManager) -> None:
        with pytest.raises(ValueError, match="The connection hasn't been established"):
            reset_manager.connected(on_disconnected=FallbackAction.RAISE)
