import inspect
import logging
import uuid
from typing import Annotated, Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.access.base.repository import BaseRepository
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.utils.datautils import standardize_dataframe

logger = logging.getLogger(__name__)


class BaseService(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra=True)

    connector: type[SQLDatabaseConnector] = SQLDatabaseConnector
    dto_type: type[TableDTO] = TableDTO
    repository_type: type[BaseRepository] = BaseRepository
    missing_upsertions_tol: Annotated[float, Field(ge=0, le=0.5)] = 0.01
    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.NOTHING

    _repository: BaseRepository | None = None

    @model_validator(mode="after")
    def _validate(self) -> "BaseService":
        self._repository = self.repository_type()
        self.on_conflict_do = OnUpsertConflictDo(getattr(self.on_conflict_do, "value", self.on_conflict_do).lower())
        return self

    def check_expected_dto_type(self, dto: type[TableDTO] | TableDTO | None) -> type[TableDTO]:
        dto_type = dto if inspect.isclass(dto) else dto.__class__

        if not inspect.isclass(self.dto_type):
            raise TypeError("Expected type not properly configured.")

        if not issubclass(dto_type, self.dto_type):  # type: ignore
            raise TypeError(
                f"The type {dto_type.__name__} of the DTO differ from the expected " + self.dto_type.__name__
            )

        return dto_type  # type: ignore

    def close(self) -> None:
        self.connector.close()

    def create(self, *, obj: TableDTO | dict[str, Any], **kwargs) -> TableDTO:
        obj = obj if isinstance(obj, self.dto_type) else self.dto_type.model_validate(**obj)
        self.check_expected_dto_type(obj)
        kwargs.pop("_db_session", None)
        self._repository.upsert_record(obj, **kwargs)
        return obj

    def delete(self, *, obj: TableDTO | dict[str, Any], hard: bool = False, **kwargs) -> pd.DataFrame:
        """
        Delete records based on the provided object.

        Args:
            obj: The object to delete, either as a DTO or a dictionary of attributes
            hard: If True, perform a hard delete (completely remove records), otherwise perform a soft delete
            **kwargs: Additional keyword arguments to pass to the repository method

        Returns:
            DataFrame containing the deleted records
        """
        parsed_obj = obj if isinstance(obj, self.dto_type) else self.dto_type.model_validate(obj)
        self.check_expected_dto_type(parsed_obj)
        dao = self.dto_type.__dao_type__
        query_filters = [
            getattr(dao, key) == getattr(parsed_obj, key)
            for key in parsed_obj.model_fields_set
            if getattr(parsed_obj, key, None) is not None and hasattr(dao, key)
        ]
        kwargs.pop("_db_session", None)
        if hard:
            return self._repository.hard_delete_records(*query_filters, dto_type=self.dto_type, **kwargs)

        return self._repository.soft_delete_records(*query_filters, dto_type=self.dto_type, **kwargs)

    def get(self, *, obj: TableDTO | dict[str, Any] | uuid.UUID, **kwargs) -> TableDTO | None:
        dto = self._repository.get_record_by_id(id_=obj, dto_type=self.dto_type, **kwargs)  # type: ignore
        if not dto and isinstance(obj, (dict, self.dto_type)):
            obj = obj if isinstance(obj, self.dto_type) else self.dto_type.model_construct(**obj)
            self.check_expected_dto_type(obj)
            dto = self._repository.get_record_from_attributes(dto=obj, **kwargs)

        return dto

    def get_or_create(self, *, obj: TableDTO | dict | uuid.UUID, **kwargs) -> TableDTO:
        """popo"""
        if not isinstance(obj, (TableDTO, dict, uuid.UUID)):
            raise ValueError("Input object not supported. Supported: TableDTO | dict | uuid.UUID")

        dto = self.get(obj=obj, **kwargs)
        if isinstance(dto, self.dto_type):
            return dto

        if isinstance(obj, uuid.UUID):
            raise ValueError("The id does not exist.")

        return self.create(obj=obj, **kwargs)

    def get_records(self, dto: TableDTO | dict, **kwargs) -> pd.DataFrame:
        parsed_dto = self.dto_type.model_validate(dto, strict=True) if isinstance(dto, dict) else dto
        self.check_expected_dto_type(parsed_dto)
        records_df = self._repository.get_records_from_attributes(parsed_dto, **kwargs)
        return standardize_dataframe(self.dto_type, records_df, **kwargs)

    def upsert_records(self, *, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        mappings = standardize_dataframe(self.dto_type, df, **kwargs)
        kwargs.pop("_db_session", None)
        on_conflict_do = kwargs.pop("on_conflict_do", self.on_conflict_do)
        on_conflict_do = OnUpsertConflictDo(getattr(on_conflict_do, "name", on_conflict_do).lower())
        upsertions = self._repository.upsert_records(
            dto_type=self.dto_type, mappings=mappings, on_conflict_do=on_conflict_do, **kwargs
        )
        if upsertions < (len(mappings.index) * (1 - self.missing_upsertions_tol)):
            raise RuntimeError(
                "Not all records were correctly upserted and the mismatch has overpass the tolerance threshold of"
                f"{(self.missing_upsertions_tol * 100):2f}%"
            )

        return mappings
