"""Database readiness probes for health endpoints."""

from __future__ import annotations

import logging
from typing import Type

from sqlalchemy import text
from sqlmodel import Session

from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.enums import FallbackAction

logger = logging.getLogger(__name__)


def check_database_ready(connector: Type[SQLDatabaseConnector]) -> bool:
    """Run ``SELECT 1`` against the configured SQLAlchemy engine.

    Args:
        connector: Model SQLDatabaseConnector class bound to an engine.

    Returns:
        True when the engine is initialized and the probe succeeds.
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
