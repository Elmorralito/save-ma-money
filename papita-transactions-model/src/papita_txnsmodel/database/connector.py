"""
Database connection

This module provides a `SQLDatabaseConnector` class to manage database connections using SQLAlchemy.
It includes methods for initializing the connection, parsing file system paths for database storage,
and wrapping functions to use a database session.

Classes:
    SQLDatabaseConnector: A class to handle SQL database connections and session management.
"""

import functools
import logging
import os
from pathlib import Path

import sqlalchemy as db
from sqlmodel import Session

from papita_txnsmodel.utils.classutils import FallbackAction

logger = logging.getLogger(__name__)


class SQLDatabaseConnector:
    """
    A class to manage SQL database connections and sessions.

    This class is designed to be used as a singleton with class-level attributes
    rather than instance attributes. It provides methods to establish database
    connections, check connection status, close connections, and decorate functions
    to use database sessions.

    Attributes:
        engine (db.Engine | None): SQLAlchemy engine instance.
        sql_kwargs (dict): Keyword arguments for SQLAlchemy engine creation.
    """

    def __new__(cls, *args, **kwargs) -> type["SQLDatabaseConnector"]:
        cls.engine: db.Engine | None = None
        cls.sql_kwargs: dict = kwargs.pop("sql_kwargs", {})
        return cls

    @classmethod
    def establish(
        cls,
        *,
        connection: dict | str | db.URL | None,
        **sql_kwargs,
    ) -> type["SQLDatabaseConnector"]:
        """
        Establish a connection to the database.

        Args:
            connection: Connection information, can be a dictionary with connection details,
                        a string representing a file path or database URL, or a SQLAlchemy URL object.
            **sql_kwargs: Additional keyword arguments for SQLAlchemy engine creation.

        Returns:
            type["SQLDatabaseConnector"]: The class with established connection.
        """
        sql_kwargs = sql_kwargs.pop("sql_kwargs", sql_kwargs)
        logger.info("Loading/Connecting DB using '%s'", type(connection))
        if not connection:
            connection = Path(os.getcwd()).joinpath(".tmp").as_posix()

        match connection:
            case db.URL():
                url = connection
            case dict():
                try:
                    url = connection.pop("url", connection.pop("dburl", connection.pop("credentials", None)))
                    if not url:
                        url = db.URL(
                            drivername=connection["drivername"],
                            username=connection["username"],
                            password=connection["password"],
                            host=connection["host"],
                            database=connection.get("database"),
                            port=connection["port"],
                            query="",
                        )
                    elif isinstance(url, str):
                        url = db.make_url(connection)
                    elif isinstance(url, dict):
                        url = db.URL(
                            drivername=url["drivername"],
                            username=url["username"],
                            password=url["password"],
                            host=url["host"],
                            database=url.get("database"),
                            port=url["port"],
                            query="",
                        )
                except Exception:
                    logger.exception("Someting happened while parsing dict params.")
                    url = db.URL(**connection)

            case str():
                try:
                    url = Path(os.path.abspath(connection))
                    url = url.joinpath("store.duckdb") if url.is_dir() else url
                    os.makedirs(url.parent.absolute().as_posix(), mode=os.R_OK | os.W_OK, exist_ok=True)
                    url = f"duckdb://{url.absolute().as_posix()}"
                except OSError:
                    logger.exception("Cannot load duckdb storage due to:")
                    url = connection
            case _:
                url = "duckdb:///:memory:"

        url = db.make_url(url) if isinstance(url, str) else url
        if not sql_kwargs and url.drivername == "duckdb":
            sql_kwargs = {"connect_args": {"read_only": False}}

        cls.engine = db.create_engine(url, **(cls.sql_kwargs | sql_kwargs))
        print(cls.engine)
        return cls

    @classmethod
    def close(cls):
        """
        Close all database connections.

        This method attempts to close the database connection by disposing
        of the engine. If an exception occurs during closing, it will be logged.
        Returns:
            None
        """
        try:
            cls.connected(on_disconnected=FallbackAction.RAISE)
            cls.engine.dispose(close=True)
            logger.debug("Connection to the database closed.")
        except Exception:
            logger.exception("There was an error while closing the connection. Exception:")

    @classmethod
    def connect(cls, func):
        """
        Decorator to wrap a function with a database session.

        This decorator ensures that the function is executed with an active
        database session provided as the '_db_session' parameter.

        Args:
            func: The function to wrap.

        Returns:
            function: The wrapped function.
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
        """
        Check if the database connection is established.

        Args:
            on_disconnected: Action to take if not connected. Can be a FallbackAction enum
                            or a string representing a FallbackAction value.
            custom_logger: Optional logger to use instead of the default one.

        Returns:
            bool: True if connected, False otherwise.

        Raises:
            Exception: If on_disconnected is set to RAISE and not connected.
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
