"""Accounts service module for the Papita Transactions system.

This module provides the AccountsService class which implements operations for
managing account entities in the system. It extends the base service functionality
with account-specific configurations and behavior.

Classes:
    AccountsService: Service for managing account entities in the system.
"""

from typing import Annotated

from pydantic import Field

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.accounts.repository import AccountsRepository
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.services.base import BaseService


class AccountsService(BaseService):
    """Service for managing account entities in the Papita Transactions system.

    This service extends the base service to provide account-specific functionality.
    It configures the appropriate DTO and repository types for account operations
    and sets stricter upsert parameters to ensure data integrity for accounts.

    Attributes:
        dto_type (type[AccountsDTO]): Data Transfer Object type for accounts.
            Set to AccountsDTO.
        repository_type (type[AccountsRepository]): Repository class for account
            database operations. Set to AccountsRepository.
        missing_upsertions_tol (float): Tolerance threshold for missing upsertions.
            Set to 0.0, meaning no tolerance for missing upsertions.
        on_conflict_do (OnUpsertConflictDo | str): Action to take on upsert conflicts.
            Set to OnUpsertConflictDo.UPDATE to update existing records.
    """

    dto_type: type[AccountsDTO] = AccountsDTO
    repository_type: type[AccountsRepository] = AccountsRepository

    missing_upsertions_tol: Annotated[float, Field(ge=0, le=0.5)] = 0.0
    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE
