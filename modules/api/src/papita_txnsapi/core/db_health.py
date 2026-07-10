"""Database readiness probes for health endpoints.

Provides lightweight connectivity checks against the model-layer SQLAlchemy engine.
Used by ``/health`` and ``/ready`` routes to report whether the API can reach PostgreSQL.

Key exports:
    check_database_ready: Execute ``SELECT 1`` and return a boolean readiness flag.
"""

from __future__ import annotations

import logging
from typing import Type

from sqlalchemy import text
from sqlmodel import Session

from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.enums import FallbackAction

logger = logging.getLogger(__name__)


def check_database_ready(connector: Type[SQLDatabaseConnector]) -> bool:
    """Probe database connectivity with a minimal ``SELECT 1`` query.

    Verifies that the connector is initialized, an engine exists, and a session can
    execute a trivial statement without raising.

    Args:
        connector: Model ``SQLDatabaseConnector`` class bound to a configured engine.

    Returns:
        ``True`` when the engine is connected and the probe succeeds; ``False`` on
        disconnect, missing engine, or any execution error (errors are logged).
    """
    if not connector.connected(on_disconnected=FallbackAction.LOG, custom_logger=logger):
        return False

    if connector.engine is None:
        return False

    try:
        with Session(connector.engine) as session:
            session.connection().execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database readiness check failed")
        return False
