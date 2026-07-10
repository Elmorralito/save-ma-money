"""Accounts service module for the Papita Transactions system.

This module provides the AccountsService class which implements operations for
managing account entities in the system. It extends the base service functionality
with account-specific configurations and behavior.

Classes:
    AccountsService: Service for managing account entities in the system.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Self

from pydantic import Field, model_validator

from papita_txnsmodel.access.account_balances.dto import AccountBalancesDTO
from papita_txnsmodel.access.account_details.dto import AccountDetailsDTO
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.accounts.repository import AccountsRepository
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.services.account_balances import AccountBalancesService
from papita_txnsmodel.services.account_extension_routing import extension_spec_for_kind, requires_extension
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

    balances_service: AccountBalancesService | None = None

    @model_validator(mode="after")
    def _wire_balances_service(self) -> Self:
        """Instantiate balances_service from the shared connector when omitted."""
        if not isinstance(self.balances_service, AccountBalancesService):
            self.balances_service = AccountBalancesService.model_validate({"connector": self.connector})
        return self

    def _parse_extension_payload(
        self,
        account: AccountsDTO,
        extension: dict[str, Any] | AccountDetailsDTO | None,
    ) -> AccountDetailsDTO | None:
        """Build an extension DTO for the account kind when payload is provided."""
        if extension is None:
            return None

        spec = extension_spec_for_kind(account.account_kind)
        if spec is None:
            return None

        _, extension_dto_type = spec
        if isinstance(extension, extension_dto_type):
            return extension

        payload = dict(extension)
        payload["account_id"] = account.id
        return extension_dto_type.model_validate(payload)

    def _upsert_extension(
        self,
        account: AccountsDTO,
        extension: dict[str, Any] | AccountDetailsDTO | None,
        *,
        owner: UsersDTO | None,
        **kwargs,
    ) -> AccountDetailsDTO | None:
        """Create or update the 1:1 extension row for an account kind."""
        extension_dto = self._parse_extension_payload(account, extension)
        if extension_dto is None:
            if requires_extension(account.account_kind) and extension is not None:
                raise ValueError(f"account_kind {account.account_kind.value} requires a valid extension payload.")
            return None

        spec = extension_spec_for_kind(account.account_kind)
        if spec is None:
            return None

        extension_service_type, _ = spec
        extension_service = extension_service_type.model_validate({"connector": self.connector})
        return extension_service.create(obj=extension_dto, owner=owner, **kwargs)

    def create_account(
        self,
        *,
        obj: AccountsDTO | dict[str, Any],
        extension: dict[str, Any] | AccountDetailsDTO | None = None,
        owner: UsersDTO | None = None,
        **kwargs,
    ) -> AccountsDTO:
        """Create an account and optional kind-specific extension row.

        Args:
            obj: Account attributes as DTO or dict. May include an ``extension`` key.
            extension: Optional extension payload; overrides ``obj["extension"]`` when set.
            owner: Tenant owner for owned-table writes.
            **kwargs: Forwarded to repository upsert helpers.

        Returns:
            AccountsDTO: Persisted account row.

        Raises:
            ValueError: When a kind that requires extensions is missing extension data.
        """
        payload = dict(obj) if isinstance(obj, dict) else obj.model_dump(mode="python")
        nested_extension = payload.pop("extension", None)
        extension_payload = extension if extension is not None else nested_extension

        account = super().create(obj=payload, owner=owner, **kwargs)
        if requires_extension(account.account_kind) and extension_payload is None:
            raise ValueError(f"account_kind {account.account_kind.value} requires extension details on create.")

        self._upsert_extension(account, extension_payload, owner=owner, **kwargs)
        return account

    def update_account(
        self,
        *,
        obj: AccountsDTO | dict[str, Any],
        extension: dict[str, Any] | AccountDetailsDTO | None = None,
        owner: UsersDTO | None = None,
        **kwargs,
    ) -> AccountsDTO:
        """Update an account and optional extension row keyed by ``account_kind``."""
        payload = dict(obj) if isinstance(obj, dict) else obj.model_dump(mode="python")
        nested_extension = payload.pop("extension", None)
        extension_payload = extension if extension is not None else nested_extension

        account = super().create(obj=payload, owner=owner, **kwargs)
        if extension_payload is not None:
            self._upsert_extension(account, extension_payload, owner=owner, **kwargs)
        return account

    def get_with_extension(
        self,
        *,
        obj: AccountsDTO | str | dict | uuid.UUID,
        owner: UsersDTO | None = None,
        **kwargs,
    ) -> tuple[AccountsDTO | None, AccountDetailsDTO | None]:
        """Retrieve an account and its extension row when applicable."""
        account = self.get(obj=obj, owner=owner, **kwargs)
        if account is None:
            return None, None

        spec = extension_spec_for_kind(account.account_kind)
        if spec is None:
            return account, None

        extension_service_type, extension_dto_type = spec
        extension_service = extension_service_type.model_validate({"connector": self.connector})
        records = extension_service.get_records(
            extension_dto_type.model_construct(account_id=account.id),
            owner=owner,
            **kwargs,
        )
        if getattr(records, "empty", True):
            return account, None

        dao_type = extension_dto_type.__dao_type__
        if len(records.columns) == 1 and isinstance(records.iloc[0, 0], dao_type):
            return account, extension_dto_type.from_dao(records.iloc[0, 0])

        return account, extension_dto_type.model_validate(records.iloc[0].to_dict())

    def get_balance(
        self,
        *,
        owner: UsersDTO,
        account_id: uuid.UUID,
        **kwargs,
    ) -> AccountBalancesDTO | None:
        """Return the current balance row from ``account_balances`` for one account."""
        if self.balances_service is None:
            raise RuntimeError("balances_service is not configured.")
        return self.balances_service.get_balance(owner=owner, account_id=account_id, **kwargs)
