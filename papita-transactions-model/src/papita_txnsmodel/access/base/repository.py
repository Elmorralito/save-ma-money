import logging
import uuid
from datetime import datetime
from typing import Type

import pandas as pd
from sqlalchemy import inspect as db_inspector
from sqlmodel import Session, delete, update
from sqlmodel.sql.expression import Select

from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.database.upsert import OnUpsertConflictDo, UpserterFactory
from papita_txnsmodel.model import SCHEMA_NAME

from .dto import TableDTO

logger = logging.getLogger(__name__)


class BaseRepository:
    __expected_dto__: type[TableDTO] = TableDTO

    @SQLDatabaseConnector.connect
    def hard_delete_records(
        self, *query_filters, dto_type: Type[TableDTO], _db_session: Session, **kwargs
    ) -> pd.DataFrame:
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

    @SQLDatabaseConnector.connect
    def soft_delete_records(
        self, *query_filters, dto_type: Type[TableDTO], _db_session: Session, **kwargs
    ) -> pd.DataFrame:
        records = self.get_records(*query_filters, dto_type=dto_type, **kwargs)
        if getattr(records, "empty", True):
            logger.warning("No records to delete were found.")
            return pd.DataFrame([])

        dao = dto_type.__dao_type__
        inspector = db_inspector(dao)
        primary_keys = [col.name for col in inspector.primary_key]
        values = {
            kwargs.get("active_column_name", "active"): False,
            kwargs.get("deleted_at_column_name", "deleted_at"): datetime.now(),
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
        if not isinstance(_db_session, Session):
            raise TypeError("Session not supported.")

        try:
            return pd.DataFrame(
                _db_session.exec(statement, params=kwargs.get("params", kwargs.get("statement_params"))).all()
            )
        except Exception as exc:
            logger.exception("The query has failed due to: %s", exc)

        return pd.DataFrame([])

    @SQLDatabaseConnector.connect
    def upsert_record(self, dto: TableDTO, *, _db_session: Session, **kwargs) -> None:
        dao = dto.to_dao()
        if not dto.id:
            raise ValueError("There is no id in the DTO")

        record = self.get_record_by_id(dto.id, dto, **kwargs)
        try:
            logger.debug("Upserting single record with identified by '%s'", dto.id)
            _ = _db_session.add(dao) if isinstance(record, dto) else _db_session.merge(dao)
            _db_session.commit()
            _db_session.refresh(dao)
            return dto.model_validate(dao.model_dump(), strict=True)
        except Exception as exc:
            logger.exception("The insert has failed due to: %s", exc)
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
        dao = dto_type.__dao_type__
        inspector = db_inspector(dao)
        return UpserterFactory.get_upserter(_db_session).upsert(
            schema_name=SCHEMA_NAME,
            table=dao.__tablename__,
            pks=[col.name for col in inspector.primary_key],
            df=mappings,
            db_session=_db_session,
            on_conflict_do=on_conflict_do,
            **kwargs,
        )

    def get_records(self, *query_filters, dto_type: type[TableDTO], **kwargs) -> pd.DataFrame:
        statement = Select(dto_type.__dao_type__).where(*query_filters)
        output_df = self.run_query(statement, **kwargs)
        if getattr(output_df, "empty", True):
            return output_df

        return output_df

    def get_records_from_attributes(self, dto: TableDTO, **kwargs) -> pd.DataFrame:
        dao = dto.__dao_type__
        query_filters = [
            getattr(dao, key) == getattr(dto, key)
            for key in dto.model_fields_set
            if getattr(dto, key, None) is not None and hasattr(dto.__dao_type__, key)
        ]
        return self.get_records(*query_filters, dto=dto, **kwargs)

    def get_record_by_id(self, id_: uuid.UUID | str | TableDTO, dto_type: type[TableDTO], **kwargs) -> TableDTO | None:
        if isinstance(id_, str):
            id_ = uuid.UUID(id_)
        elif isinstance(id_, self.__expected_dto__):
            id_ = id_.id  # type: ignore

        if not isinstance(id_, uuid.UUID):
            raise TypeError(f"Expected 'UUID', got {type(id_).__name__}")

        dao = dto_type.__dao_type__
        output_df = self.get_records(dao.id == id_, dto_type=dto_type, **kwargs)
        return (
            None
            if getattr(output_df, "empty", True)
            else dto_type.standardized_dataframe(output_df, **kwargs).iloc[0].to_dict()
        )

    def get_record_from_attributes(self, dto: TableDTO, **kwargs) -> TableDTO | None:
        output_df = self.get_records_from_attributes(dto, **kwargs)
        return (
            None
            if getattr(output_df, "empty", True)
            else dto.standardized_dataframe(output_df, **kwargs).iloc[0].to_dict()
        )
