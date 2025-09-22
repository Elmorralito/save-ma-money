"""
Database connection

This module provides a `SQLDatabaseConnector` class to manage database connections using SQLAlchemy.
It includes methods for initializing the connection, parsing file system paths for database storage,
and wrapping functions to use a database session.

Classes:
    SQLDatabaseConnector
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

    def __new__(cls, *args, **kwargs) -> type["SQLDatabaseConnector"]:
        cls.engine: db.Engine | None = None
        cls.sql_kwargs: dict = kwargs.pop("sql_kwargs", {})
        cls._connected: bool = False
        return cls

    @classmethod
    def establish(
        cls,
        *,
        connection: dict | str | db.URL | None,
        **sql_kwargs,
    ) -> type["SQLDatabaseConnector"]:
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
                        )
                except Exception:
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

        url = db.make_url(url) if isinstance(url, str) else url
        if not sql_kwargs and url.drivername == "duckdb":
            sql_kwargs = {"connect_args": {"read_only": False}}

        cls.engine = db.create_engine(url, **(cls.sql_kwargs | sql_kwargs))
        return cls

    @classmethod
    def close(cls):
        """
        Closes all database connections.

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
                db_session = mock_session if kwargs.get("_testing_") else session
                return func(instance_self, *args, _db_session=db_session, **kwargs)

        return wrapper

    @classmethod
    def connected(
        cls, on_disconnected: FallbackAction | str = FallbackAction.LOG, custom_logger: logging.Logger | None = None
    ) -> bool:
        on_disconnected = (
            on_disconnected
            if isinstance(on_disconnected, FallbackAction)
            else FallbackAction(str(on_disconnected).upper())
        )
        if not isinstance(cls.engine, db.Engine):
            on_disconnected.handle("The connection hasn't been established.", logger=custom_logger or logger)
            return False

        return True
