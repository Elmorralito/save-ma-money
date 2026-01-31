"""Database connection management for the Papita Transactions system.

This module provides the `SQLDatabaseConnector` class, which manages database
connections using SQLAlchemy and SQLModel. It handles connection establishment
for various database types (including DuckDB), session lifecycle management
through decorators, and graceful connection shutdown.

Classes:
    AbstractConnector: Abstract base class defining the connector interface.
    SQLDatabaseConnector: Concrete implementation for SQL database management.
"""

import abc
import functools
import logging
import os
from pathlib import Path
from typing import Any, Callable, ClassVar, Self, Type

import sqlalchemy as db
from sqlmodel import Session

from papita_txnsmodel.utils.enums import FallbackAction

logger = logging.getLogger(__name__)


class AbstractConnector(abc.ABC):
    """Abstract base class defining the interface for database connectors.

    This class establishes the required methods for establishing connections,
    managing sessions via decorators, and closing connections.
    """

    @classmethod
    @abc.abstractmethod
    def establish(cls, *, connection: dict | str | db.URL | None, **sql_kwargs) -> Type[Self]:
        """Establish a connection to the database.

        Args:
            connection: Connection information. Can be a dictionary with credentials,
                a string (file path or URL), or a SQLAlchemy URL object.
            **sql_kwargs: Additional arguments for SQLAlchemy engine creation.

        Returns:
            Type[Self]: The connector class with an established engine.
        """

    @classmethod
    @abc.abstractmethod
    def connect(cls, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator to wrap a function with a database session.

        Injects a `Session` object into the decorated function as `_db_session`.

        Args:
            func: The function to be wrapped with a session.

        Returns:
            Callable[..., Any]: The decorated function.
        """

    @classmethod
    @abc.abstractmethod
    def close(cls):
        """Close the database connection and dispose of the engine."""

    @classmethod
    @abc.abstractmethod
    def connected(
        cls, on_disconnected: FallbackAction | str = FallbackAction.LOG, custom_logger: logging.Logger | None = None
    ) -> bool:
        """Check if the database connection is currently established.

        Args:
            on_disconnected: Action to take if disconnected.
            custom_logger: Optional logger for reporting status.

        Returns:
            bool: True if the engine is initialized, False otherwise.
        """


class SQLDatabaseConnector(AbstractConnector):
    """Manager for SQL database connections and sessions.

    Implemented as a singleton-like class with class-level attributes. It
    provides a unified interface for connection lifecycle management and
    dependency injection of database sessions.

    Attributes:
        engine: The SQLAlchemy engine instance used for sessions.
        sql_kwargs: Default keyword arguments for engine initialization.
    """

    engine: ClassVar[db.Engine | None] = None
    sql_kwargs: ClassVar[dict | None] = None

    @classmethod
    def establish(
        cls,
        *,
        connection: dict | str | db.URL | None,
        **sql_kwargs,
    ) -> type["SQLDatabaseConnector"]:
        """Establish a connection to the database based on provided parameters.

        Parses the connection input to determine if it's a direct URL, a dictionary
        of credentials, or a file path (defaulting to DuckDB).

        Args:
            connection: Connection info. Can be a dict (credentials or URL),
                a str (file path or URL), or an `sqlalchemy.engine.url.URL`.
            **sql_kwargs: Overrides for SQLAlchemy engine configuration.

        Returns:
            Type[SQLDatabaseConnector]: The class with the configured engine.
        """
        sql_kwargs = sql_kwargs.pop("sql_kwargs", sql_kwargs)
        logger.info("Loading/Connecting DB using '%s'", type(connection))
        if not connection:
            connection = Path(os.getcwd()).joinpath(".tmp").as_posix()

        if isinstance(connection, dict):
            try:
                url = connection.pop("url", connection.pop("dburl", connection.pop("credentials", None)))
                if not url:
                    url = db.URL.create(
                        drivername=connection["drivername"],
                        username=connection.get("username"),
                        password=connection.get("password"),
                        host=connection.get("host"),
                        database=connection.get("database"),
                        port=connection.get("port"),
                    )
                elif isinstance(url, str):
                    url = db.make_url(url)
                elif isinstance(url, dict):
                    url = db.URL.create(
                        drivername=url["drivername"],
                        username=url.get("username"),
                        password=url.get("password"),
                        host=url.get("host"),
                        database=url.get("database"),
                        port=url.get("port"),
                    )
            except Exception:
                logger.exception("Something happened while parsing dict params.")
                url = db.URL.create(**connection)

        elif isinstance(connection, str):
            try:
                url_path = Path(os.path.abspath(connection))
                url_path = url_path.joinpath("store.duckdb") if url_path.is_dir() else url_path
                url = f"duckdb:///{url_path.absolute().as_posix()}"
            except OSError:
                logger.exception("Cannot load duckdb storage due to:")
                url = connection
        elif hasattr(connection, "drivername"):
            url = connection
        else:
            url = "duckdb:///:memory:"

        url = db.make_url(url) if isinstance(url, str) else url
        sql_kwargs_ = (cls.sql_kwargs or {}) | sql_kwargs
        if not sql_kwargs_ and url.drivername == "duckdb":
            sql_kwargs_ = {"connect_args": {"read_only": False}}

        cls.engine = db.create_engine(url, **sql_kwargs_)
        logger.debug("Connection to the database established.")
        return cls

    @classmethod
    def close(cls):
        """Close all active database connections by disposing of the engine."""
        try:
            cls.connected(on_disconnected=FallbackAction.RAISE)
            cls.engine.dispose(close=True)
            logger.debug("Connection to the database closed.")
        except Exception:
            logger.exception("There was an error while closing the connection. Exception:")

    @classmethod
    def connect(cls, func):
        """Decorator that provides a database session to the wrapped function.

        Automatically opens a SQLModel `Session`, handles testing mocks if
        provided, and ensures the engine is connected before execution.

        Args:
            func: The function to decorate.

        Returns:
            Callable: The wrapped function with session management.
        """

        @functools.wraps(func)
        def wrapper(instance_self, *args, **kwargs):
            cls.connected(on_disconnected=FallbackAction.RAISE)
            with Session(cls.engine) as session:
                mock_session = kwargs.pop("_db_session", None)
                db_session = mock_session if kwargs.pop("_testing_", False) else session
                return func(instance_self, *args, _db_session=db_session, **kwargs)

        return wrapper

    @classmethod
    def connected(
        cls, on_disconnected: FallbackAction | str = FallbackAction.LOG, custom_logger: logging.Logger | None = None
    ) -> bool:
        """Verify the health of the database connection.

        Args:
            on_disconnected: Fallback action (LOG, RAISE, etc.) to take if
                the connection is missing.
            custom_logger: Optional logger for reporting connection errors.

        Returns:
            bool: True if a valid SQLAlchemy engine is found.

        Raises:
            Exception: If `on_disconnected` is RAISE and the engine is missing.
        """
        on_disconnected = (
            on_disconnected
            if isinstance(on_disconnected, FallbackAction)
            else FallbackAction(str(on_disconnected).upper())
        )
        if not isinstance(cls.engine, db.Engine):
            on_disconnected.handle("The connection hasn't been established.", logger=custom_logger or logger)
            return False

        return True
