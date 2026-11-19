"""SQLAlchemy Engine and request/worker-scoped Session dependency injection (PPT-097).

Provides explicit SQLAlchemy ``Engine`` + ``sessionmaker`` management:
- ``Depends(get_db)`` for FastAPI request-scoped sessions
- ``session_scope()`` context manager for CLI, background workers, and tests
- ``@with_session`` decorator for repository methods to reuse the active request/batch
  ``Session`` (or open a scoped session when called standalone)
"""

from __future__ import annotations

import contextlib
import contextvars
import functools
import logging
from collections.abc import Callable, Iterator
from typing import Any

import sqlalchemy as db
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from papita_txnsmodel.utils.enums import FallbackAction

logger = logging.getLogger(__name__)

_active_session: contextvars.ContextVar[Session | None] = contextvars.ContextVar(
    "papita_active_db_session",
    default=None,
)


def _dict_connection_to_url(connection: dict[str, Any]) -> str | db.URL:
    """Build a SQLAlchemy URL from a credentials or nested-url dictionary."""
    data = dict(connection)
    try:
        url = data.pop("url", data.pop("dburl", data.pop("credentials", None)))
        if not url:
            return db.URL.create(
                drivername=data["drivername"],
                username=data.get("username"),
                password=data.get("password"),
                host=data.get("host"),
                database=data.get("database"),
                port=data.get("port"),
            )
        if isinstance(url, str):
            return db.make_url(url)
        if isinstance(url, dict):
            return db.URL.create(
                drivername=url["drivername"],
                username=url.get("username"),
                password=url.get("password"),
                host=url.get("host"),
                database=url.get("database"),
                port=url.get("port"),
            )
    except Exception:
        logger.exception("Something happened while parsing dict params.")
    return db.URL.create(**data)


def _coerce_connection_url(connection: dict[str, Any] | str | db.URL) -> str | db.URL:
    """Normalize connection input to a SQLAlchemy URL or URL string."""
    if isinstance(connection, dict):
        return _dict_connection_to_url(connection)
    if isinstance(connection, str) and "://" in connection:
        return connection
    if hasattr(connection, "drivername"):
        return connection
    raise ValueError(f"Unsupported database connection configuration: {connection!r}")


class DatabaseSessionManager:
    """Explicit SQLAlchemy Engine and ``sessionmaker`` manager (no class-global state)."""

    def __init__(
        self,
        engine: db.Engine | None = None,
        sql_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self.engine: db.Engine | None = engine
        self.sql_kwargs: dict[str, Any] | None = sql_kwargs
        self.session_factory: sessionmaker[Session] | None = (
            sessionmaker(bind=engine, class_=Session, expire_on_commit=False) if isinstance(engine, db.Engine) else None
        )

    def configure(
        self,
        *,
        connection: dict[str, Any] | str | db.URL | db.Engine | None,
        **sql_kwargs: Any,
    ) -> DatabaseSessionManager:
        """Configure the SQLAlchemy Engine and ``SessionLocal`` factory."""
        sql_kwargs = sql_kwargs.pop("sql_kwargs", sql_kwargs)
        if isinstance(connection, db.Engine):
            self.engine = connection
        else:
            logger.info("Configuring DB engine using '%s'", type(connection))
            raw_url = "sqlite:///:memory:" if connection is None else _coerce_connection_url(connection)
            url = db.make_url(raw_url) if isinstance(raw_url, str) else raw_url
            merged_kwargs = (self.sql_kwargs or {}) | sql_kwargs
            if connection is None and "connect_args" not in merged_kwargs:
                merged_kwargs["connect_args"] = {"check_same_thread": False}
            self.engine = db.create_engine(url, **merged_kwargs)

        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )
        return self

    def connected(
        self,
        on_disconnected: FallbackAction | str = FallbackAction.LOG,
        custom_logger: logging.Logger | None = None,
    ) -> bool:
        """Return True when a valid SQLAlchemy Engine is configured."""
        action = (
            on_disconnected
            if isinstance(on_disconnected, FallbackAction)
            else FallbackAction(str(on_disconnected).upper())
        )
        if not isinstance(self.engine, db.Engine):
            action.handle("The connection hasn't been established.", logger=custom_logger or logger)
            return False
        return True

    def close(self) -> None:
        """Dispose of the active SQLAlchemy Engine."""
        try:
            self.connected(on_disconnected=FallbackAction.RAISE)
            assert self.engine is not None
            self.engine.dispose(close=True)
            logger.debug("Database engine disposed.")
        except Exception:
            logger.exception("There was an error while closing the connection. Exception:")

    @contextlib.contextmanager
    def session_scope(self) -> Iterator[Session]:
        """Provide a scoped SQLModel ``Session`` and bind it to the active context."""
        self.connected(on_disconnected=FallbackAction.RAISE)
        factory = self.session_factory or sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )
        with factory() as session:
            token = _active_session.set(session)
            try:
                yield session
            finally:
                try:
                    _active_session.reset(token)
                except ValueError:
                    _active_session.set(None)


_default_manager = DatabaseSessionManager()


def get_session_manager() -> DatabaseSessionManager:
    """Return the active ``DatabaseSessionManager`` instance."""
    return _default_manager


def configure_database(
    *,
    connection: dict[str, Any] | str | db.URL | db.Engine | None,
    **sql_kwargs: Any,
) -> DatabaseSessionManager:
    """Configure the active ``DatabaseSessionManager`` and return it."""
    return _default_manager.configure(connection=connection, **sql_kwargs)


def get_engine() -> db.Engine | None:
    """Return the configured SQLAlchemy ``Engine`` if present."""
    return _default_manager.engine


def close_database() -> None:
    """Dispose of the configured SQLAlchemy ``Engine``."""
    _default_manager.close()


@contextlib.contextmanager
def session_scope(manager: DatabaseSessionManager | None = None) -> Iterator[Session]:
    """Context manager yielding a SQLModel ``Session`` for workers, CLI, and tests."""
    target = manager or _default_manager
    with target.session_scope() as session:
        yield session


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding one request-scoped SQLModel ``Session``."""
    with _default_manager.session_scope() as session:
        yield session


def get_active_session() -> Session | None:
    """Return the current request/worker-scoped ``Session``, if any."""
    return _active_session.get()


def with_session(func: Callable[..., Any]) -> Callable[..., Any]:
    """Inject ``_db_session`` from explicit kwargs, active request/worker scope, or a new scope."""

    @functools.wraps(func)
    def wrapper(instance_self: Any, *args: Any, **kwargs: Any) -> Any:
        testing = kwargs.pop("_testing_", False)
        explicit_session = kwargs.pop("_db_session", None)
        if testing and explicit_session is not None:
            _default_manager.connected(on_disconnected=FallbackAction.RAISE)
            return func(instance_self, *args, _db_session=explicit_session, **kwargs)
        if isinstance(explicit_session, Session):
            return func(instance_self, *args, _db_session=explicit_session, **kwargs)

        active = _active_session.get()
        if isinstance(active, Session):
            return func(instance_self, *args, _db_session=active, **kwargs)

        with _default_manager.session_scope() as session:
            return func(instance_self, *args, _db_session=session, **kwargs)

    return wrapper


__all__ = [
    "DatabaseSessionManager",
    "close_database",
    "configure_database",
    "get_active_session",
    "get_db",
    "get_engine",
    "get_session_manager",
    "session_scope",
    "with_session",
]
