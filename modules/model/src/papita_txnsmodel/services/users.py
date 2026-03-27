"""Users service module for the Papita Transactions system.

This module provides the UsersService class which implements operations for
managing user entities in the system. It extends the base service functionality
with user-specific configurations and behavior. UsersService is the canonical
service for resolving owner_id to UsersDTO for use as owner= in other services.

Classes:
    UsersService: Service for managing user entities in the system.
"""

import uuid
from typing import Annotated

from pydantic import Field

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.access.users.repository import UsersRepository
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.services.base import BaseService


class UsersService(BaseService):
    """Service for managing user entities in the Papita Transactions system.

    This service extends the base service to provide user-specific functionality.
    It configures the appropriate DTO and repository types for user operations
    and sets upsert parameters for user registration and updates. Use get_owner()
    to resolve an owner_id to a UsersDTO for passing as owner= to other services
    and handlers that use the owner column.

    Attributes:
        dto_type (type[UsersDTO]): Data Transfer Object type for users.
            Set to UsersDTO.
        repository_type (type[UsersRepository]): Repository class for user
            database operations. Set to UsersRepository.
        missing_upsertions_tol (float): Tolerance threshold for missing upsertions.
            Set to 0.01 (1%).
        on_conflict_do (OnUpsertConflictDo | str): Action to take on upsert conflicts.
            Set to OnUpsertConflictDo.UPDATE to update existing user records.
    """

    dto_type: type[UsersDTO] = UsersDTO
    repository_type: type[UsersRepository] = UsersRepository

    missing_upsertions_tol: Annotated[float, Field(ge=0, le=0.5)] = 0.01
    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE

    def get_owner(self, owner_id: uuid.UUID | str) -> UsersDTO | None:
        """Resolve an owner id to a UsersDTO for use as owner= in other services.

        Use this when you have an owner_id (e.g. from JWT or request context)
        and need a UsersDTO to pass as the owner= argument to create, get_records,
        load, dump, and similar methods on other services and handlers.

        Args:
            owner_id: User id (UUID or string) to resolve.

        Returns:
            UsersDTO if the user exists, None otherwise.
        """
        return self.get(obj=owner_id, owner=None)
