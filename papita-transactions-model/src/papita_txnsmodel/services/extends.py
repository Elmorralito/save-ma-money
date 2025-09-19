import logging
import uuid
from typing import Any, Dict

import pandas as pd
from pydantic import BaseModel

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.access.types.dto import TypesDTO
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.services.types import TypesService

logger = logging.getLogger(__name__)


class TypedEntitiesService(BaseService):

    types_service: TypesService
    type_id_column_name: str = ""
    type_id_field_name: str = ""
    types_dto_type: type[TypesDTO] = TypesDTO

    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE

    def create(self, *, obj: TableDTO | dict[str, Any], **kwargs) -> TableDTO:
        type_dto = self.types_service.get_or_create(obj=getattr(obj, self.type_id_field_name), **kwargs)
        dto = super().create(obj=obj, **kwargs)
        setattr(dto, self.type_id_field_name, type_dto)
        return dto

    def get(self, *, obj: TableDTO | dict[str, Any] | uuid.UUID, **kwargs) -> TableDTO | None:
        typed_dto = super().get(obj=obj, **kwargs)
        if kwargs.get("include_type", True) and isinstance(typed_dto, self.dto_type):
            typed_dto = self.dto_type.model_validate(
                typed_dto.model_dump(mode="python")
                | {
                    self.type_id_field_name: self.types_service.get(
                        obj=getattr(typed_dto, self.type_id_field_name), dto_type=self.types_dto_type, **kwargs
                    )
                }
            )

        return typed_dto

    def get_records_by_type(self, type_dto: TypesDTO | dict[str, Any] | uuid.UUID, **kwargs) -> pd.DataFrame:
        if isinstance(type_dto, self.types_dto_type):
            type_id = type_dto.id
        elif isinstance(type_dto, dict):
            type_id = type_dto.get(self.type_id_column_name, type_dto["id"])
        elif isinstance(type_dto, uuid.UUID):
            type_id = type_dto
        else:
            raise TypeError("Not supported")

        return self._repository.get_records(
            getattr(self.dto_type.__dao_type__, self.type_id_column_name) == type_id, dto_type=self.dto_type, **kwargs
        )


class LinkedEntity(BaseModel):

    expected_other_entity_service_type: type[BaseService] = BaseService
    other_entity_link_column_name: str = ""
    other_entity_link_field_name: str = ""
    own_entity_link_column_name: str = ""
    own_entity_link_field_name: str = ""

    other_entity_service: BaseService | None = None

    def load_other_entity_service(self, service: BaseService, **kwargs) -> "LinkedEntity":
        if not isinstance(service, self.expected_other_entity_service_type):
            raise TypeError(
                f"Expected {self.expected_other_entity_service_type.__name__}. Got {service.__class__.__name__}"
            )

        if isinstance(self.other_entity_service, self.expected_other_entity_service_type) and kwargs.get(
            "reload", False
        ):
            setattr(self, "other_entity_service", service)

        return self


class LinkedEntitiesService(BaseService):

    __links__: Dict[str, LinkedEntity] = {}

    def load_link_services(
        self, links: Dict[str, BaseService], reload: bool = True, **kwargs
    ) -> "LinkedEntitiesService":
        if not self.__links__:
            raise RuntimeError("The __links__ are not supposed to be empty.")

        dto_fields = self.dto_type.model_fields
        updated_links = {
            link_name: self.__links__[link_name].load_other_entity_service(service, reload=reload, **kwargs)
            for link_name, service in links.items()
            if link_name in self.__links__ and link_name in dto_fields
        }
        setattr(self, "__links__", updated_links)
        return self

    def create(self, *, obj: TableDTO | dict[str, Any], **kwargs) -> TableDTO:
        linked_dtos = {}
        for column_name, entity in self.__links__.items():
            linked_service = entity.other_entity_service
            if not isinstance(linked_service, BaseService):
                raise TypeError(f"Service of the linked enity in field {column_name} has not been loaded.")

            linked_dto = self.linked_service.get_or_create(
                obj=getattr(obj, entity.own_entity_link_field_name), **kwargs
            )
            linked_dtos[self.type_id_field_name] = linked_dto

        dto = super().create(obj=obj, **kwargs)
        for field_name, dto in linked_dtos.items():
            setattr(dto, field_name, dto)

        return dto

    def get(self, *, obj: TableDTO | dict[str, Any] | uuid.UUID, **kwargs) -> TableDTO | None:
        dto = super().get(obj=obj, **kwargs)
        if kwargs.get("include_linked_dtos", True) and isinstance(dto, self.dto_type):
            linked_dtos = {
                link.own_entity_link_field_name: link.other_entity_service.get(
                    obj=getattr(obj, self.own_entity_link_field_name), **kwargs
                )
                or getattr(obj, self.own_entity_link_field_name)
                for link in self.__links__.values()
                if isinstance(link.other_entity_service, link.expected_other_entity_service_type)
            }
            dto = self.dto_type.model_validate(dto.model_dump(mode="python") | linked_dtos)

        return dto


class TypedLinkedEntitiesServiceMixin(LinkedEntitiesService, TypedEntitiesService):

    def create(self, *, obj: TableDTO | dict[str, Any], **kwargs) -> TableDTO:
        typed_dto = super(TypedEntitiesService).create(obj=obj, **kwargs)
        return super(LinkedEntitiesService).create(obj=typed_dto, **kwargs)

    def get(self, *, obj: TableDTO | dict[str, Any] | uuid.UUID, **kwargs) -> TableDTO | None:
        typed_dto = super(TypedEntitiesService).get(obj=obj, **kwargs)
        return super(LinkedEntitiesService).get(obj=typed_dto, **kwargs)
