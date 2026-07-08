"""Categories service module for the Papita Transactions system.

This module provides services for managing category entities in the system. Categories
replace the legacy Types taxonomy and classify income/expense transactions.

Classes:
    CategoriesService: Service for managing category entities in the system.
"""

import logging
from typing import Annotated

from pydantic import Field

from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.categories.repository import CategoriesRepository
from papita_txnsmodel.database.upsert import OnUpsertConflictDo

from .base import BaseService

logger = logging.getLogger(__name__)


class CategoriesService(BaseService):
    """Service for managing category entities in the Papita Transactions system.

    Categories may be global or user-owned and are used to classify transaction
    templates and posted transactions.

    Attributes:
        dto_type (type[CategoriesDTO]): Data Transfer Object type for categories.
        repository_type (type[CategoriesRepository]): Repository class for category
            database operations.
        missing_upsertions_tol (float): Tolerance threshold for missing upsertions.
        on_conflict_do (OnUpsertConflictDo | str): Action to take on upsert conflicts.
    """

    dto_type: type[CategoriesDTO] = CategoriesDTO
    repository_type: type[CategoriesRepository] = CategoriesRepository

    missing_upsertions_tol: Annotated[float, Field(ge=0, le=0.5)] = 0.0
    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE
