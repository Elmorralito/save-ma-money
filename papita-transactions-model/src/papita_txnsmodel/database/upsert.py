"""
Upsert operations module.

This module provides classes and methods to perform upsert operations in SQL databases
using SQLAlchemy. Upsert (update or insert) operations are useful for ensuring that records
are either inserted if they do not exist or updated if they do.

Classes:
    OnUpsertConflictDo: Enum class defining actions to take on conflict.
    Upserter: Base class for upsert operations, not tied to any specific SQL dialect.
    PostgresUpserter: Class for upsert operations specific to PostgreSQL.
    DuckDBUpserter: Class for upsert operations specific to DuckDB.

Usage:
    - Define a subclass of `Upserter` for your specific SQL dialect.
    - Implement the `_on_conflict_do_nothing` and `_on_conflict_do_update` methods.
    - Use the `upsert` method to perform upsert operations.
"""

import inspect
import itertools
import logging
import sys
import traceback
from enum import Enum
from typing import Any, Callable, Generator, Iterator, Sequence

import pandas as pd
from sqlalchemy import Table
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import DeclarativeMeta
from sqlmodel import Session

logger = logging.getLogger(__name__)


class OnUpsertConflictDo(Enum):
    """
    Enum representing actions to take on conflict during an upsert operation.

    Attributes:
        NOTHING: Do nothing on conflict.
        UPDATE: Update the existing record on conflict.
    """

    NOTHING = "nothing"
    UPDATE = "update"


class Upserter:
    """
    Base class for upsert operations.

    This class provides a template for performing upsert operations in SQL databases.
    Subclasses should define the `__supported_dialect__` attribute and implement the
    `_on_conflict_do_nothing` and `_on_conflict_do_update` methods.

    Attributes:
        __supported_dialect__ (str): The SQL dialect supported by this upserter.
        _insert (Callable | None): The SQL insert method.
        _pks (Sequence[Any]): Primary keys for the table.
    """

    __supported_dialect__: str = ""

    _insert: Callable
    _pks: set[str]
    _upsert_method: Callable[[Any, Engine | Connection, Sequence[str], Iterator], int]
    _table_cols: Sequence[str]
    _table_name: str = ""

    @staticmethod
    def slice_batches(data: pd.DataFrame | Generator | Iterator, batch_size: int):
        if isinstance(data, pd.DataFrame):
            data = map(lambda x: x[1], data.iterrows())

        if isinstance(data, Generator):
            data = iter(data)

        while True:
            slice_ = list(itertools.islice(data, batch_size))
            if not slice_:
                break

            yield slice_

    @classmethod
    def upsert(
        cls,
        *,
        schema_name: str,
        table: str | Table | DeclarativeMeta,
        pks: Sequence[str],
        df: pd.DataFrame,
        db_session: Session,
        on_conflict_do: OnUpsertConflictDo = OnUpsertConflictDo.NOTHING,
        **to_sql_kwargs,
    ) -> int:
        """
        Perform an upsert operation.

        Args:
            schema_name (str): The schema name.
            table_name (str | sqlalchemy.Table | sqlalchemy.orm.DeclarativeMeta): The table object.
            pks (Sequence[str]): Primary keys for the table.
            df (pd.DataFrame): DataFrame containing the data to upsert.
            db_session (DBSession): SQLAlchemy session object.
            on_conflict_do (OnUpsertConflictDo): Action to take on conflict.
            **to_sql_kwargs: Additional arguments for the `to_sql` method.

        Returns:
            int: Number of rows affected by the upsert operation.

        Raises:
            AssertionError: If the SQL dialect is not supported.
        """
        assert db_session.bind.dialect.name == cls.__supported_dialect__, "Dialect not supported."
        cls._pks = set(list(pks))
        cls._upsert_method = getattr(cls, f"_on_conflict_do_{on_conflict_do.value.lower()}")
        match table:
            case str():
                table_name = table
                table_columns = df.columns
            case DeclarativeMeta():
                table_name = table.__tablename__
                table_columns = [column.key for column in table.__table__.c]
            case Table():
                table_name = table.table_name
                table_columns = [column.key for column in table.columns]
            case _:
                raise TypeError("Table type not supported.")

        return cls._upsert_fallback(
            schema_name=schema_name,
            table_name=table_name,
            table=table,
            columns=table_columns,
            df=df,
            db_session=db_session,
            **to_sql_kwargs,
        )

    @classmethod
    def _upsert_fallback(
        cls,
        *,
        schema_name: str,
        table_name: str,
        table: Table | DeclarativeMeta,
        columns: Sequence[str],
        df: pd.DataFrame,
        db_session: Session,
        **to_sql_kwargs,
    ) -> int:
        """
        Perform a fallback upsert operation when the primary method fails.

        This method attempts to insert data from a DataFrame into a specified SQL table,
        handling conflicts by retrying the operation in batches if necessary. It uses the
        `to_sql` method of the DataFrame to perform the initial upsert, and falls back to a
        batch processing approach if this fails.

        Args:
            schema_name (str): The name of the database schema.
            table_name (str): The name of the table into which data is to be upserted.
            table (Table | DeclarativeMeta): The SQLAlchemy table or declarative metadata object.
            columns (Sequence[str]): The column names of the table.
            df (pd.DataFrame): The DataFrame containing data to be upserted.
            db_session (DBSession): The SQLAlchemy session object for database transactions.
            **to_sql_kwargs: Additional keyword arguments to pass to the DataFrame's `to_sql` method.

        Returns:
            int: The number of rows affected by the upsert operation.

        Raises:
            AssertionError: If the table is not of type `DeclarativeMeta` or `Table`.
        """
        try:
            result = df.to_sql(
                table_name,
                con=db_session.bind,
                schema=schema_name,
                if_exists="append",
                index=to_sql_kwargs.pop("index", False),
                method=cls._upsert_method,
                **to_sql_kwargs,
            )
        except Exception:
            logger.warning(
                "Couldn't upsert records using pandas. Due to:\n%s",
                traceback.format_exc(),
            )

        assert isinstance(
            table,
            (
                DeclarativeMeta,
                Table,
            ),
        ), "The upsert operation cannot bve performed with object types different from DeclarativeMeta or Table."
        logger.info("Retrying to upsert the records.")
        batches = cls.slice_batches(df, to_sql_kwargs.get("batch_size", 5000))
        if not inspect.ismethod(cls._upsert_method):
            raise TypeError("There is no method set for upserting.")

        result = sum(
            map(
                lambda x: 0 if x == -1 or not isinstance(x, int) else x,
                [cls._upsert_method(table, db_session, columns, batch) for batch in batches],
            )
        )
        db_session.commit()
        return result or len(df.index)

    @classmethod
    def _on_conflict_do_nothing(cls, table: Any, conn: Engine, keys: Sequence[str], data_iter: Iterator) -> int:
        """
        Handle conflict by doing nothing.

        Args:
            table (Any): The table object.
            conn (Engine): SQLAlchemy engine connection.
            keys (Sequence[str]): Column keys.
            data_iter (Iterator): Data iterator.

        Returns:
            int: Number of rows affected.

        Raises:
            NotImplementedError: This method should be implemented by subclasses.
        """
        raise NotImplementedError()

    @classmethod
    def _on_conflict_do_update(cls, table: Any, conn: Engine, keys: Sequence[str], data_iter: Iterator) -> int:
        """
        Handle conflict by updating the existing record.

        Args:
            table (Any): The table object.
            conn (Engine): SQLAlchemy engine connection.
            keys (Sequence[str]): Column keys.
            data_iter (Iterator): Data iterator.

        Returns:
            int: Number of rows affected.

        Raises:
            NotImplementedError: This method should be implemented by subclasses.
        """
        raise NotImplementedError()


class PostgreSQLUpserter(Upserter):
    """
    Upserter class for PostgreSQL.

    This class implements the upsert operations for PostgreSQL using the
    `sqlalchemy.dialects.postgresql.insert` method.

    Attributes:
        __supported_dialect__ (str): The SQL dialect supported by this upserter ("postgresql").
        _insert (Callable | None): The SQL insert method for PostgreSQL.
    """

    __supported_dialect__: str = "postgresql"

    from sqlalchemy.dialects.postgresql import insert

    _insert: Callable = insert

    @classmethod
    def _on_conflict_do_nothing(cls, table: Any, conn: Engine, keys: Sequence[str], data_iter: Iterator) -> int:
        """
        Handle conflict by doing nothing for PostgreSQL.

        Args:
            table (Any): The table object.
            conn (Engine): SQLAlchemy engine connection.
            keys (Sequence[str]): Column keys.
            data_iter (Iterator): Data iterator.

        Returns:
            int: Number of rows affected.
        """
        try:
            data_ = [row[keys].to_dict() for row in data_iter]
        except Exception:
            data_ = [dict(zip(keys, row)) for row in data_iter]

        stmt = cls._insert(getattr(table, "table", table)).values(data_).on_conflict_do_nothing(index_elements=cls._pks)
        result = conn.execute(stmt)
        try:
            return result.rowcount
        except Exception:
            return -1

    @classmethod
    def _on_conflict_do_update(cls, table: Any, conn: Engine, keys: Sequence[str], data_iter: Iterator) -> int:
        """
        Handle conflict by updating the existing record for PostgreSQL.

        Args:
            table (Any): The table object.
            conn (Engine): SQLAlchemy engine connection.
            keys (Sequence[str]): Column keys.
            data_iter (Iterator): Data iterator.

        Returns:
            int: Number of rows affected.
        """
        try:
            data_ = [row[keys].to_dict() for row in data_iter]
        except Exception:
            data_ = [dict(zip(keys, row)) for row in data_iter]

        stmt = cls._insert(getattr(table, "table", table)).values(data_)
        stmt = stmt.on_conflict_do_update(
            index_elements=cls._pks,
            set_={key: getattr(stmt.excluded, key) for key in set(stmt.excluded.keys()) - set(cls._pks)},
        )
        result = conn.execute(stmt)
        try:
            return result.rowcount
        except Exception:
            return -1


class DuckDBUpserter(PostgreSQLUpserter):
    """
    Upserter class for DuckDB.

    This class inherits from `PostgresUpserter` and sets the supported SQL dialect to "duckdb".

    Attributes:
        __supported_dialect__ (str): The SQL dialect supported by this upserter ("duckdb").
    """

    __supported_dialect__: str = "duckdb"


class UpserterFactory:

    @classmethod
    def get_upserter(cls, db_session: Session) -> type[Upserter]:
        dialect = db_session.bind.dialect.name
        for _, cls_ in inspect.getmembers(sys.modules[__name__], inspect.isclass):
            if not issubclass(cls_, Upserter) and cls_ != Upserter:
                continue

            if cls_.__supported_dialect__.lower() == dialect.lower():
                return cls_

        raise ValueError(f"Unsupported dialect: {dialect}")
