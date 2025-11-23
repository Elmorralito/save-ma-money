"""Extended service module for the Papita Transactions system.

This module provides specialized service classes that extend the base service functionality
with type-aware operations and entity linking capabilities. It defines services for
handling typed entities, linked entities, and combinations of both.

Classes:
    TypedEntitiesService: Service for entities with type associations.
    LinkedEntity: Model for defining entity relationships.
    LinkedEntitiesService: Service for entities with relationships to other entities.
    TypedLinkedEntitiesServiceMixin: Combined service for typed entities with relationships.
"""

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
    """Service for entities that have type associations.

    This service extends the base service to handle entities that are associated with
    types from the Types table. It provides functionality to automatically handle
    type relationships when creating, retrieving, or querying entities.

    Attributes:
        types_service (TypesService): Service for handling type entities.
        type_id_column_name (str): Name of the column in the database table that
            stores the type ID. Defaults to empty string.
        type_id_field_name (str): Name of the field in the DTO that stores the
            type ID or type object. Defaults to empty string.
        types_dto_type (type[TypesDTO]): DTO type for type entities. Defaults to TypesDTO.
        on_conflict_do (OnUpsertConflictDo | str): Action to take on upsert conflicts.
            Defaults to OnUpsertConflictDo.UPDATE.
    """

    types_service: TypesService
    type_id_column_name: str = ""
    type_id_field_name: str = ""
    types_dto_type: type[TypesDTO] = TypesDTO

    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE

    def create(self, *, obj: TableDTO | dict[str, Any], **kwargs) -> TableDTO:
        """Create a new typed entity record in the database.

        This method extends the base create method to handle type relationships.
        It ensures the associated type exists (creating it if necessary) before
        creating the entity.

        Args:
            obj: The object to create, either as a DTO or a dictionary of attributes.
            **kwargs: Additional keyword arguments to pass to the repository method.

        Returns:
            TableDTO: The created object as a DTO with type information.
        """
        type_dto = self.types_service.get_or_create(obj=getattr(obj, self.type_id_field_name), **kwargs)
        dto = super().create(obj=obj, **kwargs)
        setattr(dto, self.type_id_field_name, type_dto)
        return dto

    def get(self, *, obj: TableDTO | str | dict | uuid.UUID, **kwargs) -> TableDTO | None:
        """Retrieve a typed entity record from the database.

        This method extends the base get method to include type information in the
        retrieved entity if requested.

        Args:
            obj: The object to retrieve, either as a DTO, a dictionary of attributes,
                or a UUID.
            **kwargs: Additional keyword arguments including:
                - include_type (bool): Whether to include type information. Defaults to True.

        Returns:
            TableDTO | None: The retrieved object as a DTO with type information,
                or None if not found.
        """
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
        """Retrieve multiple entity records of a specific type from the database.

        Args:
            type_dto: The type to filter by, either as a TypesDTO, a dictionary,
                or a UUID.
            **kwargs: Additional keyword arguments to pass to the repository method.

        Returns:
            pd.DataFrame: DataFrame containing the retrieved records of the specified type.

        Raises:
            TypeError: If the type_dto is not a supported type.
        """
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
    """Model for defining relationships between entities.

    This class defines how entities are linked to each other, specifying the
    relationship fields and expected service types.

    Attributes:
        expected_other_entity_service_type (type[BaseService]): Expected type of the
            service for the linked entity. Defaults to BaseService.
        other_entity_link_column_name (str): Name of the column in the linked entity's
            table that stores the relationship. Defaults to empty string.
        other_entity_link_field_name (str): Name of the field in the linked entity's
            DTO that stores the relationship. Defaults to empty string.
        own_entity_link_column_name (str): Name of the column in this entity's table
            that stores the relationship. Defaults to empty string.
        own_entity_link_field_name (str): Name of the field in this entity's DTO
            that stores the relationship. Defaults to empty string.
        other_entity_service (BaseService | None): Service instance for the linked
            entity. Defaults to None.
    """

    expected_other_entity_service_type: type[BaseService] = BaseService
    other_entity_link_column_name: str = ""
    other_entity_link_field_name: str = ""
    own_entity_link_column_name: str = ""
    own_entity_link_field_name: str = ""

    other_entity_service: BaseService | None = None

    def load_other_entity_service(self, service: BaseService, **kwargs) -> "LinkedEntity":
        """Load or update the service for the linked entity.

        Args:
            service: The service instance to use for the linked entity.
            **kwargs: Additional keyword arguments including:
                - reload (bool): Whether to reload the service if already set.

        Returns:
            LinkedEntity: This LinkedEntity instance with the updated service.

        Raises:
            TypeError: If the provided service is not of the expected type.
        """
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
    """Service for entities that have relationships with other entities.

    This service extends the base service to handle entities that are linked to
    other entities. It provides functionality to automatically handle these
    relationships when creating or retrieving entities.

    Attributes:
        __links__ (Dict[str, LinkedEntity]): Dictionary mapping field names to
            LinkedEntity objects that define the relationships.
    """

    __links__: Dict[str, LinkedEntity] = {}

    def load_link_services(
        self, links: Dict[str, BaseService], reload: bool = True, **kwargs
    ) -> "LinkedEntitiesService":
        """Load or update the services for linked entities.

        Args:
            links: Dictionary mapping field names to service instances.
            reload: Whether to reload services that are already set. Defaults to True.
            **kwargs: Additional keyword arguments to pass to the load_other_entity_service method.

        Returns:
            LinkedEntitiesService: This service instance with updated link services.

        Raises:
            RuntimeError: If the __links__ dictionary is empty.
        """
        if not self.__links__:
            raise RuntimeError("The __links__ are not supposed to be empty.")

        dto_fields = tuple(self.dto_type.model_fields.keys())
        logger.debug("DTO fields: %s", dto_fields)
        updated_links = {
            link_name: self.__links__[link_name].load_other_entity_service(service, reload=reload, **kwargs)
            for link_name, service in links.items()
            if link_name in self.__links__ and link_name in dto_fields
        }
        logger.debug("Updated links: %s", updated_links)
        setattr(self, "__links__", updated_links)
        return self

    def create(self, *, obj: TableDTO | dict[str, Any], **kwargs) -> TableDTO:
        """Create a new linked entity record in the database.

        This method extends the base create method to handle entity relationships.
        It ensures the linked entities exist (creating them if necessary) before
        creating the entity.

        Args:
            obj: The object to create, either as a DTO or a dictionary of attributes.
            **kwargs: Additional keyword arguments to pass to the repository method.

        Returns:
            TableDTO: The created object as a DTO with linked entity information.

        Raises:
            TypeError: If a linked entity service has not been loaded.
        """
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

    def get(self, *, obj: TableDTO | str | dict | uuid.UUID, **kwargs) -> TableDTO | None:
        """Retrieve a linked entity record from the database.

        This method extends the base get method to include linked entity information
        in the retrieved entity if requested.

        Args:
            obj: The object to retrieve, either as a DTO, a dictionary of attributes,
                or a UUID.
            **kwargs: Additional keyword arguments including:
                - include_linked_dtos (bool): Whether to include linked entity information.
                  Defaults to True.

        Returns:
            TableDTO | None: The retrieved object as a DTO with linked entity information,
                or None if not found.
        """
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
    """Service mixin that combines typed entity and linked entity functionality.

    This mixin class combines the functionality of TypedEntitiesService and
    LinkedEntitiesService to handle entities that both have type associations
    and relationships with other entities.
    """

    def create(self, *, obj: TableDTO | dict[str, Any], **kwargs) -> TableDTO:
        """Create a new typed and linked entity record in the database.

        This method combines the create methods of TypedEntitiesService and
        LinkedEntitiesService to handle both type associations and entity relationships.

        Args:
            obj: The object to create, either as a DTO or a dictionary of attributes.
            **kwargs: Additional keyword arguments to pass to the repository method.

        Returns:
            TableDTO: The created object as a DTO with type and linked entity information.
        """
        typed_dto = super(TypedEntitiesService).create(obj=obj, **kwargs)
        return super(LinkedEntitiesService).create(obj=typed_dto, **kwargs)

    def get(self, *, obj: TableDTO | str | dict | uuid.UUID, **kwargs) -> TableDTO | None:
        """Retrieve a typed and linked entity record from the database.

        This method combines the get methods of TypedEntitiesService and
        LinkedEntitiesService to include both type and linked entity information
        in the retrieved entity.

        Args:
            obj: The object to retrieve, either as a DTO, a dictionary of attributes,
                or a UUID.
            **kwargs: Additional keyword arguments to pass to the repository methods.

        Returns:
            TableDTO | None: The retrieved object as a DTO with type and linked entity
                information, or None if not found.
        """
        typed_dto = super(TypedEntitiesService).get(obj=obj, **kwargs)
        return super(LinkedEntitiesService).get(obj=typed_dto, **kwargs)
