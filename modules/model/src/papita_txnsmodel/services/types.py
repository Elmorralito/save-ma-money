"""Types service module for the Papita Transactions system.

This module provides services for managing type entities in the system. Types are used
to categorize various entities like accounts, assets, and liabilities. The module
implements the necessary functionality to create, retrieve, and manage type records
along with their classifications.

Classes:
    TypesService: Service for managing type entities and their classifications in the system.
"""

import logging
from typing import Annotated

from pydantic import Field

from papita_txnsmodel.access.types.dto import TypesClassificationsDTO, TypesDTO
from papita_txnsmodel.access.types.repository import TypesRepository
from papita_txnsmodel.database.upsert import OnUpsertConflictDo

from .extends import TypedEntitiesService

logger = logging.getLogger(__name__)


class TypesService(TypedEntitiesService):
    """Service for managing type entities in the Papita Transactions system.

    This service extends the base service to provide type-specific functionality.
    Types are used to categorize various entities in the system, such as different
    kinds of accounts, assets, or liabilities.

    Attributes:
        type_id_column_name (str): The column name used for type identification in the database.
            Set to "classification".
        type_id_field_name (str): The field name used for type identification in the DTO.
            Set to "classification".
        dto_type (type[TypesDTO]): Data Transfer Object type for types.
            Set to TypesDTO.
        repository_type (type[TypesRepository]): Repository class for type
            database operations. Set to TypesRepository.
        types_dto_type (type[TypesClassificationsDTO]): Data Transfer Object type for
            type classifications. Set to TypesClassificationsDTO.
        missing_upsertions_tol (float): Tolerance threshold for missing upsertions
            as a fraction between 0 and 0.5. Defaults to 0.0 (0%).
        on_conflict_do (OnUpsertConflictDo | str): Action to take on upsert conflicts.
            Set to OnUpsertConflictDo.UPDATE to update existing records.
    """

    type_id_column_name: str = "classification"
    type_id_field_name: str = "classification"
    dto_type: type[TypesDTO] = TypesDTO
    repository_type: type[TypesRepository] = TypesRepository
    types_dto_type: type[TypesClassificationsDTO] = TypesClassificationsDTO

    missing_upsertions_tol: Annotated[float, Field(ge=0, le=0.5)] = 0.0
    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE
