"""FastAPI dependencies for database access.

Uses :class:`SQLDatabaseConnector` established via :func:`papita_txnsapi.core.settings.get_settings`
so session lifecycle matches :meth:`SQLDatabaseConnector.connect`.
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from papita_txnsapi.core.settings import APISettings, get_settings
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.helpers.enums import FallbackAction


def get_database_connector(
    settings: Annotated[APISettings, Depends(get_settings)],
) -> type[SQLDatabaseConnector]:
    """Return the connector class configured on application settings.

    Args:
        settings: Loaded API settings (connector established during ``DATABASE_URL`` validation).

    Returns:
        The :class:`SQLDatabaseConnector` subclass with a bound engine.
    """
    return settings.DATABASE_URL


def get_db_session(
    connector: Annotated[type[SQLDatabaseConnector], Depends(get_database_connector)],
) -> Generator[Session, None, None]:
    """Yield a SQLModel session for the request scope.

    Mirrors :meth:`SQLDatabaseConnector.connect` session handling (connected check, context-managed
    session).

    Args:
        connector: Connector class from settings.

    Yields:
        An open :class:`~sqlmodel.Session` closed after the response is sent.
    """
    connector.connected(on_disconnected=FallbackAction.RAISE)
    yield connector.connect(Session(connector.engine))


DatabaseConnectorDep = Annotated[type[SQLDatabaseConnector], Depends(get_database_connector)]
DatabaseSessionDep = Annotated[Session, Depends(get_db_session)]
