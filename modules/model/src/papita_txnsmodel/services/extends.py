"""Extended service module for the Papita Transactions system.

This module provides specialized service classes that extend the base service functionality
with category-aware operations and entity linking capabilities. It defines services for
handling categorized entities, linked entities, and combinations of both.

Classes:
    CategorizedEntitiesService: Service for entities with category associations.
    LinkedEntity: Model for defining entity relationships.
    LinkedEntitiesService: Service for entities with relationships to other entities.
    CategorizedLinkedEntitiesServiceMixin: Combined service for categorized entities with relationships.
"""

import logging
import uuid
from typing import TYPE_CHECKING, Any, Dict, Self

import pandas as pd
from pydantic import BaseModel, model_validator

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.services.categories import CategoriesService

if TYPE_CHECKING:
    from papita_txnsmodel.access.users.dto import UsersDTO

logger = logging.getLogger(__name__)


class CategorizedEntitiesService(BaseService):
    """Service for entities that have category associations.

    This service extends the base service to handle entities associated with
    categories. It provides functionality to automatically handle category
    relationships when creating, retrieving, or querying entities.

    Attributes:
        categories_service (CategoriesService): Service for handling category entities.
        category_id_column_name (str): Name of the column storing the category ID.
        category_id_field_name (str): Name of the DTO field storing the category.
        categories_dto_type (type[CategoriesDTO]): DTO type for categories.
        on_conflict_do (OnUpsertConflictDo | str): Action to take on upsert conflicts.
    """

    categories_service: CategoriesService | None = None
    category_id_column_name: str = "category_id"
    category_id_field_name: str = ""
    categories_dto_type: type[CategoriesDTO] = CategoriesDTO

    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE

    @model_validator(mode="after")
    def _wire_categories_service(self) -> Self:
        """Instantiate categories_service from the shared connector when omitted."""
        if not isinstance(self.categories_service, CategoriesService):
            self.categories_service = CategoriesService.model_validate({"connector": self.connector})
        return self

    def create(self, *, obj: TableDTO | dict[str, Any], owner: "UsersDTO | None" = None, **kwargs) -> TableDTO:
        """Create a new categorized entity record in the database.

        Args:
            obj: The object to create, either as a DTO or a dictionary of attributes.
            owner: The owner of the record. Defaults to None.
            **kwargs: Additional keyword arguments to pass to the repository method.

        Returns:
            TableDTO: The created object as a DTO with category information.
        """
        category_dto = self.categories_service.get_or_create(
            obj=getattr(obj, self.category_id_field_name), owner=owner, **kwargs
        )
        dto = super().create(obj=obj, owner=owner, **kwargs)
        setattr(dto, self.category_id_field_name, category_dto)
        return dto

    def get(
        self, *, obj: TableDTO | str | dict | uuid.UUID, owner: "UsersDTO | None" = None, **kwargs
    ) -> TableDTO | None:
        """Retrieve a categorized entity record from the database.

        Args:
            obj: The object to retrieve, either as a DTO, a dictionary of attributes,
                or a UUID.
            owner: The owner of the record. Defaults to None.
            **kwargs: Additional keyword arguments including:
                - include_category (bool): Whether to include category information.

        Returns:
            TableDTO | None: The retrieved object as a DTO with category information,
                or None if not found.
        """
        categorized_dto = super().get(obj=obj, owner=owner, **kwargs)
        if kwargs.get("include_category", True) and isinstance(categorized_dto, self.dto_type):
            categorized_dto = self.dto_type.model_validate(
                categorized_dto.model_dump(mode="python")
                | {
                    self.category_id_field_name: self.categories_service.get(
                        obj=getattr(categorized_dto, self.category_id_field_name),
                        owner=owner,
                        dto_type=self.categories_dto_type,
                        **kwargs,
                    )
                }
            )

        return categorized_dto

    def get_records(self, dto: TableDTO | dict | None, owner: "UsersDTO | None" = None, **kwargs) -> pd.DataFrame:
        """Retrieve records and optionally batch-hydrate category references."""
        records_df = super().get_records(dto=dto, owner=owner, **kwargs)
        if not kwargs.get("include_category", True) or getattr(records_df, "empty", True):
            return records_df

        if self.category_id_column_name not in records_df.columns:
            return records_df

        category_ids = records_df[self.category_id_column_name].dropna().unique()
        category_cache = {
            category_id: self.categories_service.get(obj=category_id, owner=owner, **kwargs)
            for category_id in category_ids
        }
        records_df = records_df.copy()
        records_df[self.category_id_column_name] = records_df[self.category_id_column_name].map(
            lambda category_id: category_cache.get(category_id, category_id)
        )
        return records_df

    def get_records_by_category(
        self,
        category_dto: CategoriesDTO | dict[str, Any] | uuid.UUID,
        owner: "UsersDTO | None" = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Retrieve multiple entity records of a specific category from the database.

        Args:
            category_dto: The category to filter by, either as a CategoriesDTO, a dictionary,
                or a UUID.
            owner: The owner of the records. Defaults to None.
            **kwargs: Additional keyword arguments to pass to the repository method.

        Returns:
            pd.DataFrame: DataFrame containing the retrieved records of the specified category.

        Raises:
            TypeError: If the category_dto is not a supported type.
        """
        if isinstance(category_dto, self.categories_dto_type):
            category_id = category_dto.id
        elif isinstance(category_dto, dict):
            category_id = category_dto.get(self.category_id_column_name, category_dto["id"])
        elif isinstance(category_dto, uuid.UUID):
            category_id = category_dto
        else:
            raise TypeError("Not supported")

        return self._repository.get_records(
            getattr(self.dto_type.__dao_type__, self.category_id_column_name) == category_id,
            owner=owner,
            dto_type=self.dto_type,
            **kwargs,
        )


# Backward-compatible alias for callers still using the legacy name.
TypedEntitiesService = CategorizedEntitiesService


class LinkedEntity(BaseModel):
    """Model for defining relationships between entities.

    Attributes:
        expected_other_entity_service_type (type[BaseService]): Expected type of the
            service for the linked entity.
        other_entity_link_column_name (str): Column in the linked entity's table.
        other_entity_link_field_name (str): Field in the linked entity's DTO.
        own_entity_link_column_name (str): Column in this entity's table.
        own_entity_link_field_name (str): Field in this entity's DTO.
        other_entity_service (BaseService | None): Service instance for the linked entity.
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
            **kwargs: Additional keyword arguments including reload flag.

        Returns:
            LinkedEntity: This LinkedEntity instance with the updated service.

        Raises:
            TypeError: If the provided service is not of the expected type.
        """
        if not isinstance(service, self.expected_other_entity_service_type):
            raise TypeError(
                f"Expected {self.expected_other_entity_service_type.__name__}. Got {service.__class__.__name__}"
            )

        if self.other_entity_service is None or kwargs.get("reload", False):
            setattr(self, "other_entity_service", service)

        return self


class LinkedEntitiesService(BaseService):
    """Service for entities that have relationships with other entities."""

    __links__: Dict[str, LinkedEntity] = {}

    def load_link_services(
        self, links: Dict[str, BaseService], reload: bool = True, **kwargs
    ) -> "LinkedEntitiesService":
        """Load or update the services for linked entities.

        Args:
            links: Dictionary mapping field names to service instances.
            reload: Whether to reload services that are already set.
            **kwargs: Additional keyword arguments.

        Returns:
            LinkedEntitiesService: This service instance with updated link services.

        Raises:
            RuntimeError: If the __links__ dictionary is empty.
        """
        if not self.__links__:
            raise RuntimeError("The __links__ are not supposed to be empty.")

        dto_fields = tuple(self.dto_type.model_fields.keys())
        logger.debug("DTO fields: %s", dto_fields)
        updated_links = dict(self.__links__)
        for link_name, service in links.items():
            if link_name not in self.__links__ or link_name not in dto_fields:
                continue
            updated_links[link_name] = self.__links__[link_name].load_other_entity_service(
                service, reload=reload, **kwargs
            )
        logger.debug("Updated links: %s", updated_links)
        setattr(self, "__links__", updated_links)
        return self

    def create(self, *, obj: TableDTO | dict[str, Any], owner: "UsersDTO | None" = None, **kwargs) -> TableDTO:
        """Create a new linked entity record in the database.

        Optional FK fields whose value is ``None`` are skipped (no linked service call).
        Non-null FK fields require the matching linked service to already be loaded.

        Args:
            obj: The object to create.
            owner: The owner of the record.
            **kwargs: Additional keyword arguments.

        Returns:
            TableDTO: The created object as a DTO with linked entity information.

        Raises:
            TypeError: If a required linked entity service has not been loaded.
        """
        linked_dtos = {}
        for column_name, entity in self.__links__.items():
            field_name = entity.own_entity_link_field_name
            field_value = obj.get(field_name) if isinstance(obj, dict) else getattr(obj, field_name, None)
            if field_value is None:
                continue

            linked_service = entity.other_entity_service
            if not isinstance(linked_service, BaseService):
                raise TypeError(f"Service of the linked enity in field {column_name} has not been loaded.")

            linked_dto = linked_service.get_or_create(obj=field_value, owner=owner, **kwargs)
            linked_dtos[field_name] = linked_dto

        dto = super().create(obj=obj, owner=owner, **kwargs)
        for field_name, linked_dto in linked_dtos.items():
            setattr(dto, field_name, linked_dto)

        return dto

    def get(
        self, *, obj: TableDTO | str | dict | uuid.UUID, owner: "UsersDTO | None" = None, **kwargs
    ) -> TableDTO | None:
        """Retrieve a linked entity record from the database.

        Args:
            obj: The object to retrieve.
            owner: The owner of the record.
            **kwargs: Additional keyword arguments.

        Returns:
            TableDTO | None: The retrieved object as a DTO with linked entity information.
        """
        dto = super().get(obj=obj, owner=owner, **kwargs)
        if kwargs.get("include_linked_dtos", True) and isinstance(dto, self.dto_type):
            # Skip null FKs (e.g. expense has from_account only; transfer has no category).
            linked_dtos: dict[str, Any] = {}
            for link in self.__links__.values():
                if not isinstance(link.other_entity_service, link.expected_other_entity_service_type):
                    continue
                field_name = link.own_entity_link_field_name
                field_value = getattr(dto, field_name, None)
                if field_value is None:
                    continue
                linked_dtos[field_name] = (
                    link.other_entity_service.get(obj=field_value, owner=owner, **kwargs) or field_value
                )
            if linked_dtos:
                dto = self.dto_type.model_validate(dto.model_dump(mode="python") | linked_dtos)

        return dto


class CategorizedLinkedEntitiesServiceMixin(LinkedEntitiesService, CategorizedEntitiesService):
    """Service mixin combining categorized entity and linked entity functionality."""

    def create(self, *, obj: TableDTO | dict[str, Any], owner: "UsersDTO | None" = None, **kwargs) -> TableDTO:
        """Create a new categorized and linked entity record in the database."""
        categorized_dto = CategorizedEntitiesService.create(self, obj=obj, owner=owner, **kwargs)
        return LinkedEntitiesService.create(self, obj=categorized_dto, owner=owner, **kwargs)

    def get(
        self, *, obj: TableDTO | str | dict | uuid.UUID, owner: "UsersDTO | None" = None, **kwargs
    ) -> TableDTO | None:
        """Retrieve a categorized and linked entity record from the database."""
        categorized_dto = CategorizedEntitiesService.get(self, obj=obj, owner=owner, **kwargs)
        return LinkedEntitiesService.get(self, obj=categorized_dto, owner=owner, **kwargs)  # type: ignore


TypedLinkedEntitiesServiceMixin = CategorizedLinkedEntitiesServiceMixin
