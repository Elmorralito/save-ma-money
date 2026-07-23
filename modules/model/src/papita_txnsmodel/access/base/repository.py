"""Base repository module for the Papita Transactions system.

This module provides the foundation for all repositories in the Papita Transactions system.
It defines the BaseRepository class which implements common database operations like
querying, inserting, updating, and deleting records. It handles both hard and soft
deletions, as well as upsert operations with conflict resolution strategies.

Classes:
    BaseRepository: Base class for all repositories in the Papita Transactions system.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Sequence, Type

import pandas as pd
from sqlalchemy import func
from sqlalchemy import inspect as db_inspector
from sqlmodel import Session, delete, select, update
from sqlmodel.sql.expression import Select

from papita_txnsmodel.access.users.dto import OwnedTableDTO, UsersDTO
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.database.upsert import OnUpsertConflictDo, UpserterFactory
from papita_txnsmodel.model import SCHEMA_NAME

from .dto import TableDTO

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository class providing common database operations for all repositories.

    This class serves as the foundation for all repository classes in the system,
    implementing common operations like querying, inserting, updating, and deleting
    records. It handles both hard and soft deletions, as well as upsert operations
    with conflict resolution strategies.

    Soft-delete semantics (default):
        ``get_records`` / ``count_records`` / ``get_page_with_total`` exclude inactive
        rows (``active=True`` and ``deleted_at IS NULL`` when those columns exist).
        Pass ``include_deleted=True`` to include soft-deleted rows. Upserting a
        soft-deleted id raises unless ``reactivate=True``.

    Attributes:
        __expected_dto__ (type[TableDTO]): The expected DTO type for this repository.
            Defaults to TableDTO.
    """

    __expected_dto__: type[TableDTO] = TableDTO

    @staticmethod
    def _soft_delete_read_filters(dao: type, *, include_deleted: bool) -> list:
        """Build default active-only predicates for list/count queries.

        Args:
            dao: SQLModel table class for the query.
            include_deleted: When ``True``, return no extra filters.

        Returns:
            List of SQLAlchemy filter expressions (may be empty).
        """
        if include_deleted:
            return []
        filters: list = []
        if hasattr(dao, "active"):
            filters.append(dao.active.is_(True))
        if hasattr(dao, "deleted_at"):
            filters.append(dao.deleted_at.is_(None))
        return filters

    @SQLDatabaseConnector.connect
    def hard_delete_records(
        self, *query_filters, dto_type: Type[TableDTO], _db_session: Session, **kwargs
    ) -> pd.DataFrame:
        """Permanently delete records from the database based on query filters.

        This method performs a hard delete operation, completely removing records
        from the database that match the provided query filters.

        Args:
            *query_filters: Variable length list of query filter conditions.
            dto_type: The DTO type for the records to delete.
            _db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments for filtering or configuration.

        Returns:
            pd.DataFrame: DataFrame containing the deleted records.
        """
        records = self.get_records(*query_filters, dto_type=dto_type, **kwargs)
        if getattr(records, "empty", True):
            logger.warning("No records to delete were found.")
            return pd.DataFrame([])

        dao = dto_type.__dao_type__
        inspector = db_inspector(dao)
        primary_keys = [col.name for col in inspector.primary_key]
        try:
            for _, where in records[primary_keys].iterrows():
                statement = delete(dao).where(*[getattr(dao, col) == value for col, value in where.items()])
                _db_session.exec(statement)
        except Exception:
            logger.exception("The deletion process failed due to:")
            _db_session.rollback()
        else:
            logger.debug(
                "The removal process has been successfully performed. Wiping out %d records.", len(records.index)
            )
            _db_session.commit()

        return records

    @staticmethod
    def _flatten_records_dataframe(records: pd.DataFrame, dto_type: type[TableDTO]) -> pd.DataFrame:
        """Expand single-column SQLModel result frames into plain dict rows."""
        if getattr(records, "empty", True) or len(records.columns) != 1:
            return records

        dao_type = dto_type.__dao_type__
        first_cell = records.iloc[0, 0]
        if not isinstance(first_cell, dao_type):
            return records

        return pd.DataFrame([row.model_dump(mode="python") for row in records.iloc[:, 0]])

    @SQLDatabaseConnector.connect
    def soft_delete_records(
        self, *query_filters, dto_type: Type[TableDTO], _db_session: Session, **kwargs
    ) -> pd.DataFrame:
        """Mark records as deleted without removing them from the database.

        This method performs a soft delete operation, marking records as inactive
        and setting a deletion timestamp without actually removing them from the database.

        Args:
            *query_filters: Variable length list of query filter conditions.
            dto_type: The DTO type for the records to soft-delete.
            _db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments including:
                - active_column_name (str): Name of the column indicating active status.
                - deleted_at_column_name (str): Name of the column for deletion timestamp.

        Returns:
            pd.DataFrame: DataFrame containing the soft-deleted records.
        """
        records = self.get_records(*query_filters, dto_type=dto_type, **kwargs)
        records = self._flatten_records_dataframe(records, dto_type)
        if getattr(records, "empty", True):
            logger.warning("No records to delete were found.")
            return pd.DataFrame([])

        dao = dto_type.__dao_type__
        inspector = db_inspector(dao)
        primary_keys = [col.name for col in inspector.primary_key]
        values = {
            kwargs.get("active_column_name", "active"): False,
            kwargs.get("deleted_at_column_name", "deleted_at"): datetime.now(),
            kwargs.get("updated_at_column_name", "updated_at"): datetime.now(),
        }
        try:
            for _, where in records[primary_keys].iterrows():
                statement = (
                    update(dao).where(*[getattr(dao, col) == value for col, value in where.items()]).values(**values)
                )
                _db_session.exec(statement)
        except Exception:
            logger.exception("The deletion process failed due to:")
            _db_session.rollback()
        else:
            logger.debug(
                "The soft-deletion process has been successfully performed. Soft-deleting %d records.",
                len(records.index),
            )
            _db_session.commit()

        return records

    @SQLDatabaseConnector.connect
    def run_query(self, statement: Select, _db_session: Session, **kwargs) -> pd.DataFrame:
        """Execute a SQL query and return the results as a DataFrame.
        Args:
            statement: The SQL statement to execute.
            _db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments including:
                - params: Query parameters.
                - statement_params: Alternative name for query parameters.

        Returns:
            pd.DataFrame: DataFrame containing the query results.

        Raises:
            TypeError: If the provided session is not a valid Session object.
        """
        if not isinstance(_db_session, Session):
            raise TypeError("Session not supported.")
        try:
            results = _db_session.exec(statement, params=kwargs.get("params", kwargs.get("statement_params"))).all()
            if not results:
                return pd.DataFrame([])
            return pd.DataFrame([self._query_result_item_to_mapping(item) for item in results])
        except Exception as exc:
            logger.exception("The query has failed due to: %s", exc)

        return pd.DataFrame([])

    @staticmethod
    def _query_result_item_to_mapping(item: Any) -> Any:
        """Normalize a SQLModel/SQLAlchemy result row into a plain mapping.

        ``Session.exec(select(DAO))`` may yield the DAO directly or a ``Row`` that
        wraps a single entity. Returning nested ``{DAOName: entity}`` frames breaks
        ``standardize_dataframe`` / DTO validation on list helpers.
        """
        if hasattr(item, "model_dump"):
            return item.model_dump(mode="python")
        try:
            length = len(item)
            entity = item[0]
        except (TypeError, KeyError, IndexError):
            return item
        if length == 1 and hasattr(entity, "model_dump"):
            return entity.model_dump(mode="python")
        return item

    def _dataframe_row_to_dto(self, output_df: pd.DataFrame, dto_type: type[TableDTO], **kwargs) -> TableDTO | None:
        """Convert the first row of a query DataFrame into a validated DTO."""
        if getattr(output_df, "empty", True):
            return None

        dao_type = dto_type.__dao_type__
        if len(output_df.columns) == 1:
            cell = output_df.iloc[0, 0]
            if isinstance(cell, dao_type):
                return dto_type.from_dao(cell)

        row_dict = dto_type.standardized_dataframe(output_df, **kwargs).iloc[0].to_dict()
        return dto_type.model_validate(row_dict)

    @SQLDatabaseConnector.connect
    def upsert_record(self, dto: TableDTO, *, _db_session: Session, **kwargs) -> None:
        """Insert or update a single record in the database.

        Looks up the existing row including soft-deleted records. Merging a
        soft-deleted row is refused unless ``reactivate=True`` (which clears
        ``deleted_at`` and sets ``active=True`` on the DTO before merge).

        Args:
            dto: The DTO containing the record data to upsert.
            _db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments for configuration, including:
                - reactivate (bool): Allow restoring a soft-deleted row (default False).

        Returns:
            TableDTO | None: The upserted DTO if successful, None otherwise.

        Raises:
            ValueError: If the DTO does not have an ID, or if the row is soft-deleted
                and ``reactivate`` is not true.
        """
        if not dto.id:
            raise ValueError("There is no id in the DTO")

        reactivate = bool(kwargs.pop("reactivate", False))
        record = self.get_record_by_id(dto.id, dto_type=type(dto), include_deleted=True, **kwargs)
        if record is not None and not getattr(record, "active", True):
            if not reactivate:
                raise ValueError(f"Cannot upsert soft-deleted record '{dto.id}'; pass reactivate=True to restore.")
            dto.active = True
            dto.deleted_at = None

        dao = dto.to_dao()
        if hasattr(dao, "updated_at"):
            setattr(dao, "updated_at", datetime.now())

        try:
            logger.debug("Upserting single record with id '%s'", dto.id)
            if record is None:
                _db_session.add(dao)
            else:
                dao = _db_session.merge(dao)
            _db_session.commit()
            _db_session.refresh(dao)
            return dto.model_validate(dao.model_dump(mode="python"), strict=True)
        except ValueError:
            raise
        except Exception as exc:
            logger.exception("The upsert operation has failed due to: %s", exc)
            _db_session.rollback()

        return None

    @SQLDatabaseConnector.connect
    def upsert_records(
        self,
        dto_type: type[TableDTO],
        mappings: pd.DataFrame,
        *,
        _db_session: Session,
        on_conflict_do: OnUpsertConflictDo = OnUpsertConflictDo.NOTHING,
        **kwargs,
    ) -> int:
        """Insert or update multiple records in the database.

        This method performs bulk upsert operations for multiple records based on
        the provided DataFrame.

        Args:
            dto_type: The DTO type for the records to upsert.
            mappings: DataFrame containing the records to upsert.
            _db_session: Database session provided by the connector decorator.
            on_conflict_do: Action to take on conflicts. Defaults to NOTHING.
            **kwargs: Additional keyword arguments to pass to the upserter.

        Returns:
            int: Number of records successfully upserted.
        """
        dao = dto_type.__dao_type__
        inspector = db_inspector(dao)
        if "updated_at" in mappings.columns or hasattr(dao, "updated_at"):
            mappings["updated_at"] = datetime.now()

        if "created_at" not in mappings.columns and hasattr(dao, "created_at"):
            mappings["created_at"] = datetime.now()

        if "owner_id" not in mappings.columns and hasattr(dao, "owner_id"):
            mappings["owner_id"] = kwargs.get("owner_id")

        kwargs.pop("owner_id", None)
        kwargs.pop("owner", None)
        return UpserterFactory.get_upserter(_db_session).upsert(
            schema_name=SCHEMA_NAME,
            table=dao,
            pks=[col.name for col in inspector.primary_key],
            df=mappings,
            db_session=_db_session,
            on_conflict_do=on_conflict_do,
            **kwargs,
        )

    @staticmethod
    def _apply_list_options(
        statement: Select,
        *,
        order_by: Any | Sequence[Any] | None = None,
        skip: int | None = None,
        limit: int | None = None,
    ) -> Select:
        """Apply ordering and pagination clauses to a SELECT statement."""
        if order_by is not None:
            if isinstance(order_by, Sequence) and not isinstance(order_by, (str, bytes)):
                statement = statement.order_by(*order_by)
            else:
                statement = statement.order_by(order_by)
        if skip is not None:
            statement = statement.offset(skip)
        if limit is not None:
            statement = statement.limit(limit)
        return statement

    @SQLDatabaseConnector.connect
    def count_records(
        self,
        *query_filters,
        dto_type: type[TableDTO],
        _db_session: Session,
        **kwargs,
    ) -> int:
        """Count rows matching query filters without fetching the full result set.

        Soft-deleted rows are excluded by default. Pass ``include_deleted=True`` to
        count inactive rows as well.
        """
        if not isinstance(_db_session, Session):
            raise TypeError("Session not supported.")

        include_deleted = bool(kwargs.pop("include_deleted", False))
        dao = dto_type.__dao_type__
        filters = [*self._soft_delete_read_filters(dao, include_deleted=include_deleted), *query_filters]
        statement = select(func.count()).select_from(dao)  # pylint: disable=not-callable
        if filters:
            statement = statement.where(*filters)
        try:
            return int(_db_session.exec(statement).one())
        except Exception as exc:
            logger.exception("The count query has failed due to: %s", exc)
            return 0

    def get_records(self, *query_filters, dto_type: type[TableDTO], **kwargs) -> pd.DataFrame:
        """Retrieve records from the database based on query filters.

        Soft-deleted rows are excluded by default (``active=True`` and
        ``deleted_at IS NULL`` when present on the DAO). Pass ``include_deleted=True``
        to include inactive rows (e.g. repair/admin paths).

        Args:
            *query_filters: Variable length list of query filter conditions.
            dto_type: The DTO type for the records to retrieve.
            **kwargs: Additional keyword arguments to pass to run_query, including:
                - include_deleted (bool): Include soft-deleted rows (default False).
                - order_by / skip / limit: List options.

        Returns:
            DataFrame containing the retrieved records.
        """
        order_by = kwargs.pop("order_by", None)
        skip = kwargs.pop("skip", None)
        limit = kwargs.pop("limit", None)
        include_deleted = bool(kwargs.pop("include_deleted", False))
        dao = dto_type.__dao_type__
        filters = [*self._soft_delete_read_filters(dao, include_deleted=include_deleted), *query_filters]
        statement = Select(dao).where(*filters) if filters else Select(dao)
        statement = self._apply_list_options(statement, order_by=order_by, skip=skip, limit=limit)
        output_df = self.run_query(statement, **kwargs)
        if getattr(output_df, "empty", True):
            return output_df

        return output_df

    @SQLDatabaseConnector.connect
    def get_page_with_total(  # pylint: disable=too-many-locals
        self,
        *query_filters,
        dto_type: type[TableDTO],
        _db_session: Session,
        **kwargs,
    ) -> tuple[pd.DataFrame, int]:
        """Return a paginated page and matching total in one query when possible.

        Uses ``COUNT(*) OVER()`` on the page SELECT so list endpoints avoid a
        separate count round-trip. When the page is empty (e.g. ``skip`` past the
        end), falls back to an in-session ``COUNT(*)`` so ``total`` stays correct.

        Args:
            *query_filters: WHERE predicates (same as ``get_records``).
            dto_type: DTO type whose ``__dao_type__`` is queried.
            _db_session: Database session (injected by connector).
            **kwargs: ``order_by`` / ``skip`` / ``limit`` / ``include_deleted``.

        Returns:
            Tuple of (page DataFrame without the window column, total row count).

        Raises:
            TypeError: If ``_db_session`` is not a SQLModel ``Session``.
        """
        if not isinstance(_db_session, Session):
            raise TypeError("Session not supported.")

        order_by = kwargs.pop("order_by", None)
        skip = kwargs.pop("skip", None)
        limit = kwargs.pop("limit", None)
        include_deleted = bool(kwargs.pop("include_deleted", False))
        dao = dto_type.__dao_type__
        filters = [*self._soft_delete_read_filters(dao, include_deleted=include_deleted), *query_filters]

        total_col = func.count().over().label("_total")  # pylint: disable=not-callable
        statement = select(dao, total_col)
        if filters:
            statement = statement.where(*filters)
        statement = self._apply_list_options(statement, order_by=order_by, skip=skip, limit=limit)

        try:
            rows = list(_db_session.exec(statement).all())
        except Exception as exc:
            logger.exception("The page+total query has failed due to: %s", exc)
            return pd.DataFrame([]), 0

        if not rows:
            count_statement = select(func.count()).select_from(dao)  # pylint: disable=not-callable
            if filters:
                count_statement = count_statement.where(*filters)
            try:
                total = int(_db_session.exec(count_statement).one())
            except Exception as exc:
                logger.exception("The empty-page count fallback has failed due to: %s", exc)
                return pd.DataFrame([]), 0
            return pd.DataFrame([]), total

        first = rows[0]
        total = int(first[1])
        parsed: list[Any] = []
        for row in rows:
            entity = row[0]
            parsed.append(entity.model_dump(mode="python") if hasattr(entity, "model_dump") else entity)
        return pd.DataFrame(parsed), total

    def get_records_from_attributes(self, dto: TableDTO, **kwargs) -> pd.DataFrame:
        """Retrieve records from the database based on DTO attributes.

        This method constructs query filters from the non-None attributes of the
        provided DTO and uses them to retrieve matching records.

        Args:
            dto: The DTO containing attributes to filter by.
            **kwargs: Additional keyword arguments to pass to get_records.

        Returns:
            pd.DataFrame: DataFrame containing the retrieved records.
        """
        dao = dto.__dao_type__
        query_filters = [
            getattr(dao, key) == getattr(dto, key)
            for key in dto.model_fields_set
            if (value := getattr(dto, key, None)) is not None
            and not (isinstance(value, str) and value == "")
            and hasattr(dto.__dao_type__, key)
        ]
        dto_type = kwargs.pop("dto_type", type(dto))
        return self.get_records(*query_filters, dto_type=dto_type, **kwargs)

    def get_record_by_id(
        self, id_: TableDTO | str | dict | uuid.UUID, dto_type: type[TableDTO], **kwargs
    ) -> TableDTO | None:
        """Retrieve a single record from the database by ID.

        Args:
            id_: The ID of the record to retrieve, either as a UUID, string, or DTO.
            dto_type: The DTO type for the record to retrieve.
            **kwargs: Additional keyword arguments to pass to get_records.

        Returns:
            TableDTO | None: The retrieved record as a DTO, or None if not found.

        Raises:
            TypeError: If the provided ID is not of a supported type.
        """
        if isinstance(id_, str):
            id_ = uuid.UUID(id_)
        elif isinstance(id_, self.__expected_dto__):
            id_ = id_.id  # type: ignore

        if not isinstance(id_, uuid.UUID):
            raise TypeError(f"Expected 'UUID', got {type(id_).__name__}")

        dao = dto_type.__dao_type__
        output_df = self.get_records(dao.id == id_, dto_type=dto_type, **kwargs)
        return self._dataframe_row_to_dto(output_df, dto_type, **kwargs)

    def get_record_from_attributes(self, dto: TableDTO, **kwargs) -> TableDTO | None:
        """Retrieve a single record from the database based on DTO attributes.

        This method retrieves records based on the attributes of the provided DTO
        and returns the first matching record if found.

        Args:
            dto: The DTO containing attributes to filter by.
            **kwargs: Additional keyword arguments to pass to get_records_from_attributes.

        Returns:
            TableDTO | None: The retrieved record as a DTO, or None if not found.
        """
        dto_type = kwargs.pop("dto_type", type(dto))
        output_df = self.get_records_from_attributes(dto, dto_type=dto_type, **kwargs)
        return self._dataframe_row_to_dto(output_df, dto_type, **kwargs)


class OwnedTableRepository(BaseRepository):
    """Repository for tables that are owned by a user.

    This repository extends BaseRepository to provide multi-tenant support by
    enforcing ownership constraints on all database operations. All CRUD operations
    require a UsersDTO to ensure users can only access and modify their own records.

    Attributes:
        __expected_dto__ (type[OwnedTableDTO]): The expected DTO type for this
            repository. Defaults to OwnedTableDTO.
    """

    def _get_owner_filter(self, owner: UsersDTO | uuid.UUID, dao_type: type) -> Any:
        """Create a filter condition for owner-based queries.

        Args:
            owner: The user who owns the records, or a raw owner UUID.
            dao_type: The DAO type to create the filter for.

        Returns:
            Any: A SQLAlchemy filter condition matching the owner's ID.
        """
        owner_id = owner.id if isinstance(owner, UsersDTO) else owner
        return dao_type.owner_id == owner_id

    @SQLDatabaseConnector.connect
    def hard_delete_records(
        self, *query_filters, dto_type: Type[OwnedTableDTO], _db_session: Session, **kwargs
    ) -> pd.DataFrame:
        """Permanently delete records owned by the specified user.

        This method extends the base hard_delete_records to include ownership
        filtering, ensuring only records owned by the specified user are deleted.

        Args:
            *query_filters: Variable length list of query filter conditions.
            owner: The user who owns the records to delete.
            dto_type: The DTO type for the records to delete.
            _db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments for filtering or configuration.

        Returns:
            pd.DataFrame: DataFrame containing the deleted records.
        """
        owner = kwargs.pop("owner", None)
        if not isinstance(owner, UsersDTO):
            raise ValueError("Owner is required for hard_delete_records")

        owner_filter = self._get_owner_filter(owner, dto_type.__dao_type__)
        return super().hard_delete_records(
            owner_filter, *query_filters, dto_type=dto_type, _db_session=_db_session, owner=owner, **kwargs
        )

    @SQLDatabaseConnector.connect
    def soft_delete_records(
        self, *query_filters, dto_type: Type[OwnedTableDTO], _db_session: Session, **kwargs
    ) -> pd.DataFrame:
        """Mark records owned by the specified user as deleted.

        This method extends the base soft_delete_records to include ownership
        filtering, ensuring only records owned by the specified user are soft-deleted.

        Args:
            *query_filters: Variable length list of query filter conditions.
            owner: The user who owns the records to soft-delete.
            dto_type: The DTO type for the records to soft-delete.
            _db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments including:
                - active_column_name (str): Name of the column indicating active status.
                - deleted_at_column_name (str): Name of the column for deletion timestamp.

        Returns:
            pd.DataFrame: DataFrame containing the soft-deleted records.
        """
        owner = kwargs.pop("owner", None)
        if not isinstance(owner, UsersDTO):
            raise ValueError("Owner is required for soft_delete_records")

        owner_filter = self._get_owner_filter(owner, dto_type.__dao_type__)
        return super().soft_delete_records(
            owner_filter, *query_filters, dto_type=dto_type, _db_session=_db_session, owner=owner, **kwargs
        )

    @SQLDatabaseConnector.connect
    def upsert_record(self, dto: OwnedTableDTO, *, _db_session: Session, **kwargs) -> OwnedTableDTO | None:
        """Insert or update a single record with ownership validation.

        This method ensures that the record being upserted belongs to the specified
        owner. If the DTO doesn't have an owner_id set, it will be assigned. If it
        has a different owner_id, a ValueError is raised.

        Args:
            dto: The DTO containing the record data to upsert.
            owner: The user who owns the record.
            _db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments for configuration.

        Returns:
            OwnedTableDTO | None: The upserted DTO if successful, None otherwise.

        Raises:
            ValueError: If the DTO's owner_id doesn't match the provided owner.
        """
        owner = kwargs.pop("owner", None)
        if not isinstance(owner, UsersDTO):
            raise ValueError("Owner is required for upsert_record")

        if dto.owner_id != owner.id:
            if dto.owner_id and dto.owner_id != owner.id:
                raise ValueError("DTO owner_id does not match the provided owner.")
            dto.owner_id = owner.id  # type: ignore

        return super().upsert_record(dto, _db_session=_db_session, owner=owner, **kwargs)

    @SQLDatabaseConnector.connect
    def upsert_records(
        self,
        dto_type: Type[OwnedTableDTO],
        mappings: pd.DataFrame,
        *,
        _db_session: Session,
        on_conflict_do: OnUpsertConflictDo = OnUpsertConflictDo.NOTHING,
        **kwargs,
    ) -> int:
        """Insert or update multiple records with ownership assignment.

        This method performs bulk upsert operations while automatically assigning
        the owner_id to all records in the DataFrame.

        Args:
            dto_type: The DTO type for the records to upsert.
            mappings: DataFrame containing the records to upsert.
            owner: The user who owns the records, either as UsersDTO or UUID.
            _db_session: Database session provided by the connector decorator.
            on_conflict_do: Action to take on conflicts. Defaults to NOTHING.
            **kwargs: Additional keyword arguments to pass to the upserter.

        Returns:
            int: Number of records successfully upserted.
        """
        owner = kwargs.pop("owner", None)
        if not isinstance(owner, (UsersDTO, uuid.UUID)):
            raise ValueError("Owner is required for upsert_records")

        mappings["owner_id"] = owner if isinstance(owner, uuid.UUID) else owner.id
        return super().upsert_records(
            dto_type, mappings, _db_session=_db_session, on_conflict_do=on_conflict_do, **kwargs
        )

    def get_records(self, *query_filters, dto_type: Type[OwnedTableDTO], **kwargs) -> pd.DataFrame:
        """Retrieve records owned by the specified user.

        This method extends the base get_records to include ownership filtering,
        ensuring only records owned by the specified user are retrieved.

        Args:
            *query_filters: Variable length list of query filter conditions.
            owner: The user who owns the records.
            dto_type: The DTO type for the records to retrieve.
            **kwargs: Additional keyword arguments to pass to run_query.

        Returns:
            pd.DataFrame: DataFrame containing the retrieved records.
        """
        owner = kwargs.pop("owner", None)
        if not isinstance(owner, (UsersDTO, uuid.UUID)):
            raise ValueError("Owner is required for get_records")

        owner_filter = self._get_owner_filter(owner, dto_type.__dao_type__)
        return super().get_records(owner_filter, *query_filters, dto_type=dto_type, **kwargs)

    def count_records(self, *query_filters, dto_type: Type[OwnedTableDTO], **kwargs) -> int:
        """Count tenant-owned rows matching query filters."""
        owner = kwargs.pop("owner", None)
        if not isinstance(owner, (UsersDTO, uuid.UUID)):
            raise ValueError("Owner is required for count_records")

        owner_filter = self._get_owner_filter(owner, dto_type.__dao_type__)
        return super().count_records(owner_filter, *query_filters, dto_type=dto_type, **kwargs)

    def get_page_with_total(self, *query_filters, dto_type: Type[OwnedTableDTO], **kwargs) -> tuple[pd.DataFrame, int]:
        """Return a tenant-owned page and total matching count."""
        owner = kwargs.pop("owner", None)
        if not isinstance(owner, (UsersDTO, uuid.UUID)):
            raise ValueError("Owner is required for get_page_with_total")

        owner_filter = self._get_owner_filter(owner, dto_type.__dao_type__)
        return super().get_page_with_total(owner_filter, *query_filters, dto_type=dto_type, **kwargs)

    def get_records_from_attributes(self, dto: OwnedTableDTO, **kwargs) -> pd.DataFrame:
        """Retrieve records owned by the specified user based on DTO attributes.

        This method sets the owner_id on the DTO and retrieves matching records
        that belong to the specified owner.

        Args:
            dto: The DTO containing attributes to filter by.
            owner: The user who owns the records, either as UsersDTO or UUID.
            **kwargs: Additional keyword arguments to pass to get_records.

        Returns:
            pd.DataFrame: DataFrame containing the retrieved records.
        """
        owner = kwargs.pop("owner", None)
        if not isinstance(owner, (UsersDTO, uuid.UUID)):
            raise ValueError("Owner is required for get_records_from_attributes")

        dto.owner_id = owner if isinstance(owner, uuid.UUID) else owner.id  # type: ignore
        return super().get_records_from_attributes(dto, owner=owner, **kwargs)

    def get_record_from_attributes(self, dto: OwnedTableDTO, **kwargs) -> OwnedTableDTO | None:
        """Retrieve a single record owned by the specified user based on DTO attributes.

        This method sets the owner_id on the DTO and retrieves the first matching
        record that belongs to the specified owner.

        Args:
            dto: The DTO containing attributes to filter by.
            owner: The user who owns the record, either as UsersDTO or UUID.
            **kwargs: Additional keyword arguments to pass to get_records_from_attributes.

        Returns:
            OwnedTableDTO | None: The retrieved record as a DTO, or None if not found.
        """
        owner = kwargs.pop("owner", None)
        if not isinstance(owner, (UsersDTO, uuid.UUID)):
            raise ValueError("Owner is required for get_record_from_attributes")

        dto.owner_id = owner if isinstance(owner, uuid.UUID) else owner.id  # type: ignore
        return super().get_record_from_attributes(dto, owner=owner, **kwargs)
