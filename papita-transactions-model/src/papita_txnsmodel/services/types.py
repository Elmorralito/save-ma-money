import logging
import uuid
from typing import Annotated, Any, get_args

import pandas as pd
from pydantic import ConfigDict, Field

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.access.types.dto import DiscriminatedTypesModel, TypesDTO
from papita_txnsmodel.access.types.repository import TypesRepository
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.utils.datautils import standardize_dataframe

logger = logging.getLogger(__name__)


class TypesService(BaseService):
    model_config = ConfigDict(extra="allow")

    dto_type: type[TypesDTO] = TypesDTO
    repository_type: type[TypesRepository] = TypesRepository
    discriminator_type: type[DiscriminatedTypesModel] = DiscriminatedTypesModel

    missing_upsertions_tol: Annotated[float, Field(ge=0, le=0.5)] = 0.0
    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE

    def check_expected_dto_type(self, dto: type[TypesDTO] | TypesDTO | None) -> type[TypesDTO]:
        dto_type = super().check_expected_dto_type(dto)
        if dto_type == self.dto_type:
            raise ValueError(f"Please provide a child class of {self.dto_type.__name__}")

        return dto_type

    def setup_record_type(
        self, *, obj: TypesDTO | dict[str, Any] | uuid.UUID, dto_type: type[TypesDTO], **kwargs
    ) -> TypesDTO | uuid.UUID:
        if issubclass(obj.__class__, dto_type) or isinstance(obj, uuid.UUID):
            record = obj
        elif not issubclass(obj.__class__, dto_type) and isinstance(obj, self.dto_type):
            record = dto_type.model_validate(obj.model_dump(mode="python"), strict=True)
        elif isinstance(obj, dict):
            record = dto_type.model_validate(obj, strict=True)
        else:
            raise ValueError("Type of DTO not supported.")

        return record  # type: ignore

    def create(self, *, obj: TableDTO | dict[str, Any], **kwargs) -> TableDTO:
        dto_type = self.check_expected_dto_type(kwargs.pop("dto_type", self.dto_type))
        old_dto_type = self.dto_type
        try:
            record = self.setup_record_type(obj=obj, dto_type=dto_type, **kwargs)
            self.dto_type = dto_type
            if isinstance(record, uuid.UUID):
                raise ValueError("It's not possible to create the DTO since there is only an UUID.")

            self.check_expected_dto_type(record)
            return super().create(obj=record, **kwargs)
        except Exception as exc:
            raise exc
        finally:
            self.dto_type = old_dto_type

    def get(self, *, obj: TableDTO | dict[str, Any] | uuid.UUID, **kwargs) -> TableDTO | None:
        dto_type = self.check_expected_dto_type(kwargs.pop("dto_type", self.dto_type))
        old_dto_type = self.dto_type
        try:
            record = self.setup_record_type(obj=obj, dto_type=dto_type, **kwargs)
            self.dto_type = dto_type
            dto = super().get(obj=record, **kwargs)
        except Exception:
            logger.exception("It was not possible to retrieve the TypesDTO due to:")
            dto = None
        finally:
            self.dto_type = old_dto_type

        return dto

    def get_records(self, dto: pd.DataFrame, **kwargs):
        return NotImplementedError()

    def get_types(self, dto: TypesDTO | dict | None, dto_type: type[TypesDTO], **kwargs) -> list[TypesDTO]:
        old_dto_type = self.dto_type
        try:
            discriminator = next(iter(get_args(dto_type.model_fields["__discriminator__"].annotation)))
            self.dto_type = self.check_expected_dto_type(dto_type)
            raw_dtos = super().get_records(dto or {"__discriminator__": discriminator}, **kwargs)
            raw_dtos["__discriminator__"] = discriminator
            dtos = self.standardize_dataframe(raw_dtos, **kwargs)
        except Exception:
            logger.exception("It was not possible to retrieve the types due to:")
            dtos = []
        finally:
            self.dto_type = old_dto_type

        return dtos

    def standardize_dataframe(
        self, df: pd.DataFrame, dto_type: type[TypesDTO] | None = None, **kwargs
    ) -> list[TypesDTO]:
        if "__discriminator__" not in df.columns:
            raise ValueError("It's not possible to determine the type requested.")

        discriminated_types = df.pop("__discriminator__")
        dto_type = self.check_expected_dto_type(dto_type or self.dto_type)
        mappings = standardize_dataframe(dto_type, df, **kwargs)
        mappings["__discriminator__"] = discriminated_types
        return [
            self.discriminator_type.model_validate({"type_dto": row.to_dict()}).type_dto
            for _, row in mappings.iterrows()
            if row["__discriminator__"]
        ]

    def upsert_records(self, *, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        dto_type = self.check_expected_dto_type(kwargs.pop("dto_type", self.dto_type))
        if "__discriminator__" not in df.columns:
            df["__discriminator__"] = next(iter(get_args(dto_type.model_fields["__discriminator__"].annotation)))

        dtos = [
            self.create(obj=record, dto_type=record.__discriminator__, **kwargs).row
            for record in self.standardize_dataframe(df, dto_type=dto_type, **kwargs)
        ]
        return pd.DataFrame(dtos)
