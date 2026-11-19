"""Database package for Papita Transactions (Session DI & PostgreSQL upserts)."""

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
from papita_txnsmodel.database.upsert import OnUpsertConflictDo, PostgreSQLUpserter, Upserter, UpserterFactory

__all__ = [
    "DatabaseSessionManager",
    "OnUpsertConflictDo",
    "PostgreSQLUpserter",
    "Upserter",
    "UpserterFactory",
    "close_database",
    "configure_database",
    "get_active_session",
    "get_db",
    "get_engine",
    "get_session_manager",
    "session_scope",
    "with_session",
]
