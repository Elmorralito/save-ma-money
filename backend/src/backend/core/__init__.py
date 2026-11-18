"""Core infrastructure: Settings, SQLAlchemy Session DI, and Authentication (PPT-097)."""

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.dependencies.auth import get_current_owner
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

__all__ = [
    "AuthSecurityManager",
    "DatabaseSessionManager",
    "Settings",
    "close_database",
    "configure_database",
    "get_active_session",
    "get_current_owner",
    "get_db",
    "get_engine",
    "get_session_manager",
    "get_settings",
    "session_scope",
    "with_session",
]
