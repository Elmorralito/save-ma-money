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
from typing import Any, Type

import pandas as pd
from sqlalchemy import inspect as db_inspector
from sqlmodel import Session, delete, update
from sqlmodel.sql.expression import Select

from papita_txnsmodel.database.upsert import OnUpsertConflictDo, UpserterFactory
from papita_txnsmodel.model.base import BaseSQLModel
from papita_txnsmodel.model.constants import SCHEMA_NAME
from papita_txnsmodel.model.users import Users

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository class providing common database operations for all repositories.

    This class serves as the foundation for all repository classes in the system,
    implementing common operations like querying, inserting, updating, and deleting
    records. It handles both hard and soft deletions, as well as upsert operations
    with conflict resolution strategies.

    Attributes:
        __expected_dto__ (type[TableDTO]): The expected DTO type for this repository.
            Defaults to TableDTO.
    """

    __expected_dao_type__: Type[BaseSQLModel] = BaseSQLModel

    def hard_delete_records(
        self, *query_filters, dao_type: Type[BaseSQLModel], db_session: Session, **kwargs
    ) -> pd.DataFrame:
        """Permanently delete records from the database based on query filters.

        This method performs a hard delete operation, completely removing records
        from the database that match the provided query filters.

        Args:
            *query_filters: Variable length list of query filter conditions.
            dao_type: The DAO type for the records to delete.
            _db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments for filtering or configuration.

        Returns:
            pd.DataFrame: DataFrame containing the deleted records.
        """
        records = self.get_records(*query_filters, dao_type=dao_type, **kwargs)
        if getattr(records, "empty", True):
            logger.warning("No records to delete were found.")
            return pd.DataFrame([])

        inspector = db_inspector(dao_type)
        primary_keys = [col.name for col in inspector.primary_key]
        try:
            for _, where in records[primary_keys].iterrows():
                statement = delete(dao_type).where(*[getattr(dao_type, col) == value for col, value in where.items()])
                db_session.exec(statement)
        except Exception:
            logger.exception("The deletion process failed due to:")
            db_session.rollback()
        else:
            logger.debug(
                "The removal process has been successfully performed. Wiping out %d records.", len(records.index)
            )
            db_session.commit()

        return records

    def soft_delete_records(
        self, *query_filters, dao_type: Type[BaseSQLModel], db_session: Session, **kwargs
    ) -> pd.DataFrame:
        """Mark records as deleted without removing them from the database.

        This method performs a soft delete operation, marking records as inactive
        and setting a deletion timestamp without actually removing them from the database.

        Args:
            *query_filters: Variable length list of query filter conditions.
            dao_type: The DAO type for the records to soft-delete.
            db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments including:
                - active_column_name (str): Name of the column indicating active status.
                - deleted_at_column_name (str): Name of the column for deletion timestamp.

        Returns:
            pd.DataFrame: DataFrame containing the soft-deleted records.
        """
        records = self.get_records(*query_filters, dao_type=dao_type, **kwargs)
        if getattr(records, "empty", True):
            logger.warning("No records to delete were found.")
            return pd.DataFrame([])

        inspector = db_inspector(dao_type)
        primary_keys = [col.name for col in inspector.primary_key]
        values = {
            kwargs.get("active_column_name", "active"): False,
            kwargs.get("deleted_at_column_name", "deleted_at"): datetime.now(),
            kwargs.get("updated_at_column_name", "updated_at"): datetime.now(),
        }
        try:
            for _, where in records[primary_keys].iterrows():
                statement = (
                    update(dao_type)
                    .where(*[getattr(dao_type, col) == value for col, value in where.items()])
                    .values(**values)
                )
                db_session.exec(statement)
        except Exception:
            logger.exception("The deletion process failed due to:")
            db_session.rollback()
        else:
            logger.debug(
                "The soft-deletion process has been successfully performed. Soft-deleting %d records.",
                len(records.index),
            )
            db_session.commit()

        return records

    def run_query(self, *, statement: Select, db_session: Session, **kwargs) -> pd.DataFrame:
        """Execute a SQL query and return the results as a DataFrame.
        Args:
            statement: The SQL statement to execute.
            db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments including:
                - params: Query parameters.
                - statement_params: Alternative name for query parameters.

        Returns:
            pd.DataFrame: DataFrame containing the query results.

        Raises:
            TypeError: If the provided session is not a valid Session object.
        """
        if not isinstance(db_session, Session):
            raise TypeError("Session not supported.")
        try:
            return pd.DataFrame(
                db_session.exec(statement, params=kwargs.get("params", kwargs.get("statement_params"))).all()
            )
        except Exception as exc:
            logger.exception("The query has failed due to: %s", exc)

        return pd.DataFrame([])

    def upsert_record(self, *, dao: BaseSQLModel, db_session: Session, **kwargs) -> BaseSQLModel | None:
        """Insert or update a single record in the database.

        This method performs an upsert operation (insert or update) for a single record
        based on the provided DTO.

        Args:
            dto: The DTO containing the record data to upsert.
            _db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments for configuration.

        Returns:
            TableDTO | None: The upserted DTO if successful, None otherwise.

        Raises:
            ValueError: If the DTO does not have an ID.
        """

        if not dao.id:
            raise ValueError("There is no id in the DTO")

        record = self.get_record_by_id(dao.id, dao_type=dao.__class__, db_session=db_session, **kwargs)
        if hasattr(dao, "updated_at"):
            setattr(dao, "updated_at", datetime.now())

        db_session.begin()
        try:
            logger.debug("Upserting single record with id '%s'", dao.id)
            _ = db_session.add(dao) if isinstance(record, dao) else db_session.merge(dao)
            db_session.commit()
            db_session.refresh(dao)
            return dao.model_validate(dao.model_dump(), strict=True)
        except Exception as exc:
            logger.exception("The upsert operation has failed due to: %s", exc)
            db_session.rollback()

        return None

    def upsert_records(
        self,
        *,
        dao_type: Type[BaseSQLModel],
        mappings: pd.DataFrame,
        db_session: Session,
        on_conflict_do: OnUpsertConflictDo = OnUpsertConflictDo.NOTHING,
        **kwargs,
    ) -> int:
        """Insert or update multiple records in the database.

        This method performs bulk upsert operations for multiple records based on
        the provided DataFrame.

        Args:
            dao_type: The DAO type for the records to upsert.
            mappings: DataFrame containing the records to upsert.
            db_session: Database session provided by the connector decorator.
            on_conflict_do: Action to take on conflicts. Defaults to NOTHING.
            **kwargs: Additional keyword arguments to pass to the upserter.

        Returns:
            int: Number of records successfully upserted.
        """
        inspector = db_inspector(dao_type)
        if "updated_at" in mappings.columns or hasattr(dao_type, "updated_at"):
            mappings["updated_at"] = datetime.now()

        if "created_at" not in mappings.columns and hasattr(dao_type, "created_at"):
            mappings["created_at"] = datetime.now()

        if "owner_id" not in mappings.columns and hasattr(dao_type, "owner_id"):
            mappings["owner_id"] = kwargs.get("owner_id")

        kwargs.pop("owner_id", None)
        kwargs.pop("owner", None)
        return UpserterFactory.get_upserter(db_session).upsert(
            schema_name=SCHEMA_NAME,
            table=dao_type,
            pks=[col.name for col in inspector.primary_key],
            df=mappings,
            db_session=db_session,
            on_conflict_do=on_conflict_do,
            **kwargs,
        )

    def get_records(self, *query_filters, dao_type: Type[BaseSQLModel], db_session: Session, **kwargs) -> pd.DataFrame:
        """Retrieve records from the database based on query filters.
        Args:
            *query_filters: Variable length list of query filter conditions.
            dao_type: The DAO type for the records to retrieve.
            db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments to pass to the query.

        Returns:
            pd.DataFrame: DataFrame containing the retrieved records.
        """
        statement = Select(dao_type).where(*query_filters) if query_filters else Select(dao_type)
        output_df = self.run_query(statement=statement, db_session=db_session, **kwargs)
        if getattr(output_df, "empty", True):
            return output_df

        return output_df

    def get_records_from_attributes(self, *, dao: BaseSQLModel, db_session: Session, **kwargs) -> pd.DataFrame:
        """Retrieve records from the database based on DTO attributes.

        This method constructs query filters from the non-None attributes of the
        provided DAO and uses them to retrieve matching records.

        Args:
            dao: The DAO containing attributes to filter by.
            db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments to pass to get_records.

        Returns:
            pd.DataFrame: DataFrame containing the retrieved records.
        """
        query_filters = [
            getattr(dao, key) == getattr(dao, key)
            for key in dao.model_fields_set
            if getattr(dao, key, None) is not None and hasattr(dao, key)
        ]
        return self.get_records(*query_filters, dao_type=dao.__class__, db_session=db_session, **kwargs)

    def get_record_by_id(
        self, id_: BaseSQLModel | str | dict | uuid.UUID, *, dao_type: Type[BaseSQLModel], db_session: Session, **kwargs
    ) -> BaseSQLModel | None:
        """Retrieve a single record from the database by ID.

        Args:
            id_: The ID of the record to retrieve, either as a UUID, string, or DTO.
            dao_type: The DAO type for the record to retrieve.
            db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments to pass to get_records.

        Returns:
            TableDTO | None: The retrieved record as a DTO, or None if not found.

        Raises:
            TypeError: If the provided ID is not of a supported type.
        """
        if isinstance(id_, str):
            id_ = uuid.UUID(id_)
        elif isinstance(id_, self.__expected_dao_type__):
            id_ = id_.id

        if not isinstance(id_, uuid.UUID):
            raise TypeError(f"Expected 'UUID', got {type(id_).__name__}")

        output_df = self.get_records(dao_type.id == id_, dao_type=dao_type, db_session=db_session, **kwargs)
        return (
            None
            if getattr(output_df, "empty", True)
            else dao_type.standardized_dataframe(output_df, **kwargs).iloc[0].to_dict()
        )

    def get_record_from_attributes(self, *, dao: BaseSQLModel, db_session: Session, **kwargs) -> BaseSQLModel | None:
        """Retrieve a single record from the database based on DTO attributes.

        This method retrieves records based on the attributes of the provided DTO
        and returns the first matching record if found.

        Args:
            dao: The DAO containing attributes to filter by.
            db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments to pass to get_records_from_attributes.

        Returns:
            TableDTO | None: The retrieved record as a DTO, or None if not found.
        """
        output_df = self.get_records_from_attributes(dao=dao, db_session=db_session, **kwargs)
        dao_type = dao.__class__
        return (
            None
            if getattr(output_df, "empty", True)
            else dao_type.standardized_dataframe(output_df, **kwargs).iloc[0].to_dict()
        )


class OwnedTableRepository(BaseRepository):
    """Repository for tables that are owned by a user.

    This repository extends BaseRepository to provide multi-tenant support by
    enforcing ownership constraints on all database operations. All CRUD operations
    require a Users to ensure users can only access and modify their own records.

    Attributes:
        __expected_dao_type__ (type[BaseSQLModel]): The expected DAO type for this
            repository. Defaults to BaseSQLModel.
    """

    def _get_owner_filter(self, *, owner: Users | uuid.UUID, dao_type: Type[BaseSQLModel]) -> Any:
        """Create a filter condition for owner-based queries.

        Args:
            owner: The user who owns the records.
            dao_type: The DAO type to create the filter for.

        Returns:
            Any: A SQLAlchemy filter condition matching the owner's ID.
        """
        return dao_type.owner_id == (owner if isinstance(owner, uuid.UUID) else owner.id)

    def hard_delete_records(
        self, *query_filters, dao_type: Type[BaseSQLModel], db_session: Session, **kwargs
    ) -> pd.DataFrame:
        """Permanently delete records owned by the specified user.

        This method extends the base hard_delete_records to include ownership
        filtering, ensuring only records owned by the specified user are deleted.

        Args:
            *query_filters: Variable length list of query filter conditions.
            owner: The user who owns the records to delete.
            dao_type: The DAO type for the records to delete.
            _db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments for filtering or configuration.

        Returns:
            pd.DataFrame: DataFrame containing the deleted records.
        """
        owner = kwargs.pop("owner", None)
        if not isinstance(owner, Users):
            raise ValueError("Owner is required for hard_delete_records")

        owner_filter = self._get_owner_filter(owner=owner, dao_type=dao_type)
        return super().hard_delete_records(
            owner_filter, *query_filters, dao_type=dao_type, db_session=db_session, **kwargs
        )

    def soft_delete_records(
        self, *query_filters, dao_type: Type[BaseSQLModel], db_session: Session, **kwargs
    ) -> pd.DataFrame:
        """Mark records owned by the specified user as deleted.

        This method extends the base soft_delete_records to include ownership
        filtering, ensuring only records owned by the specified user are soft-deleted.

        Args:
            *query_filters: Variable length list of query filter conditions.
            owner: The user who owns the records to soft-delete.
            dao_type: The DAO type for the records to soft-delete.
            _db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments including:
                - active_column_name (str): Name of the column indicating active status.
                - deleted_at_column_name (str): Name of the column for deletion timestamp.

        Returns:
            pd.DataFrame: DataFrame containing the soft-deleted records.
        """
        owner = kwargs.pop("owner", None)
        if not isinstance(owner, (Users, uuid.UUID)):
            raise ValueError("Owner is required for soft_delete_records")

        owner_filter = self._get_owner_filter(owner=owner, dao_type=dao_type)
        return super().soft_delete_records(
            owner_filter, *query_filters, dao_type=dao_type, db_session=db_session, **kwargs
        )

    def upsert_record(self, *, dao: BaseSQLModel, db_session: Session, **kwargs) -> BaseSQLModel | None:
        """Insert or update a single record with ownership validation.

        This method ensures that the record being upserted belongs to the specified
        owner. If the DAO doesn't have an owner_id set, it will be assigned. If it
        has a different owner_id, a ValueError is raised.

        Args:
            dao: The DAO containing the record data to upsert.
            db_session: Database session provided by the connector decorator.
            owner: The user who owns the record.
            **kwargs: Additional keyword arguments for configuration.

        Returns:
            BaseSQLModel | None: The upserted DAO if successful, None otherwise.

        Raises:
            ValueError: If the DAO's owner_id doesn't match the provided owner.
        """
        owner = kwargs.pop("owner", None)
        if not isinstance(owner, (Users, uuid.UUID)):
            raise ValueError("Owner is required for upsert_record")

        if dao.owner_id != (owner if isinstance(owner, uuid.UUID) else owner.id):
            if dao.owner_id and dao.owner_id != (owner if isinstance(owner, uuid.UUID) else owner.id):
                raise ValueError("DAO owner_id does not match the provided owner.")

            dao.owner_id = owner if isinstance(owner, uuid.UUID) else owner.id

        kwargs.pop("owner", None)
        return super().upsert_record(dao=dao, db_session=db_session, **kwargs)

    def upsert_records(
        self,
        *,
        dao_type: Type[BaseSQLModel],
        mappings: pd.DataFrame,
        db_session: Session,
        on_conflict_do: OnUpsertConflictDo = OnUpsertConflictDo.NOTHING,
        **kwargs,
    ) -> int:
        """Insert or update multiple records with ownership assignment.

        This method performs bulk upsert operations while automatically assigning
        the owner_id to all records in the DataFrame.

        Args:
            dao_type: The DAO type for the records to upsert.
            mappings: DataFrame containing the records to upsert.
            db_session: Database session provided by the connector decorator.
            owner: The user who owns the records, either as Users or UUID.
            db_session: Database session provided by the connector decorator.
            on_conflict_do: Action to take on conflicts. Defaults to NOTHING.
            **kwargs: Additional keyword arguments to pass to the upserter.

        Returns:
            int: Number of records successfully upserted.
        """
        owner = kwargs.pop("owner", None)
        if not isinstance(owner, (Users, uuid.UUID)):
            raise ValueError("Owner is required for upsert_records")

        mappings["owner_id"] = owner if isinstance(owner, uuid.UUID) else owner.id
        return super().upsert_records(
            dao_type=dao_type, mappings=mappings, db_session=db_session, on_conflict_do=on_conflict_do, **kwargs
        )

    def get_records(self, *query_filters, dao_type: Type[BaseSQLModel], db_session: Session, **kwargs) -> pd.DataFrame:
        """Retrieve records owned by the specified user.

        This method extends the base get_records to include ownership filtering,
        ensuring only records owned by the specified user are retrieved.

        Args:
            *query_filters: Variable length list of query filter conditions.
            owner: The user who owns the records.
            dao_type: The DAO type for the records to retrieve.
            db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments to pass to the query.

        Returns:
            pd.DataFrame: DataFrame containing the retrieved records.
        """
        owner = kwargs.pop("owner", None)
        if not isinstance(owner, (Users, uuid.UUID)):
            raise ValueError("Owner is required for get_records")

        owner_filter = self._get_owner_filter(owner=owner, dao_type=dao_type)
        return super().get_records(owner_filter, *query_filters, dao_type=dao_type, db_session=db_session, **kwargs)

    def get_records_from_attributes(self, *, dao: BaseSQLModel, db_session: Session, **kwargs) -> pd.DataFrame:
        """Retrieve records owned by the specified user based on DAO attributes.

        This method sets the owner_id on the DAO and retrieves matching records
        that belong to the specified owner.

        Args:
            dao: The DAO containing attributes to filter by.
            owner: The user who owns the records, either as Users or UUID.
            db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments to pass to get_records.

        Returns:
            pd.DataFrame: DataFrame containing the retrieved records.
        """
        owner = kwargs.pop("owner", None)
        if not isinstance(owner, (Users, uuid.UUID)):
            raise ValueError("Owner is required for get_records_from_attributes")

        dao.owner_id = owner if isinstance(owner, uuid.UUID) else owner.id
        return super().get_records_from_attributes(dao=dao, db_session=db_session, **kwargs)

    def get_record_from_attributes(self, *, dao: BaseSQLModel, db_session: Session, **kwargs) -> BaseSQLModel | None:
        """Retrieve a single record owned by the specified user based on DAO attributes.

        This method sets the owner_id on the DAO and retrieves the first matching
        record that belongs to the specified owner.

        Args:
            dao: The DAO containing attributes to filter by.
            owner: The user who owns the record, either as Users or UUID.
            db_session: Database session provided by the connector decorator.
            **kwargs: Additional keyword arguments to pass to get_records_from_attributes.

        Returns:
            BaseSQLModel | None: The retrieved record as a DAO, or None if not found.
        """
        owner = kwargs.pop("owner", None)
        if not isinstance(owner, (Users, uuid.UUID)):
            raise ValueError("Owner is required for get_record_from_attributes")

        dao.owner_id = owner if isinstance(owner, uuid.UUID) else owner.id
        return super().get_record_from_attributes(dao=dao, db_session=db_session, **kwargs)
