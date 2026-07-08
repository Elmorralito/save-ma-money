"""Read-only service for account_balances materialized view queries."""

from __future__ import annotations

import uuid
from typing import Type

import pandas as pd
from pydantic import BaseModel, ConfigDict, model_validator

from papita_txnsmodel.access.account_balances.dto import AccountBalancesDTO
from papita_txnsmodel.access.account_balances.repository import AccountBalancesRepository
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.connector import SQLDatabaseConnector


class AccountBalancesService(BaseModel):
    """Read-only balance queries for API #25 wiring."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    connector: Type[SQLDatabaseConnector] = SQLDatabaseConnector
    repository_type: type[AccountBalancesRepository] = AccountBalancesRepository
    dto_type: type[AccountBalancesDTO] = AccountBalancesDTO

    _repository: AccountBalancesRepository | None = None

    @model_validator(mode="after")
    def _validate(self) -> "AccountBalancesService":
        """Initialize repository."""
        self._repository = self.repository_type()
        return self

    def close(self) -> None:
        """Close the database connection."""
        self.connector.close()

    def get_balances(
        self,
        *,
        owner: UsersDTO,
        account_id: uuid.UUID | None = None,
        currency: str | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Return balance rows for a tenant owner."""
        if owner is None:
            raise ValueError("owner=UsersDTO is required for account balance queries.")

        filters: dict[str, object] = {}
        if account_id is not None:
            filters["account_id"] = account_id
        if currency is not None:
            filters["currency"] = currency

        from papita_txnsmodel.access.balance_reports.filter_validation import validate_report_filters
        from papita_txnsmodel.access.balance_reports.repository import BalanceReportsRepository

        validated = validate_report_filters("account_balances", filters)
        return BalanceReportsRepository().query(
            report_id="account_balances",
            owner=owner,
            filters=validated,
            **kwargs,
        )

    def get_balance(
        self,
        *,
        owner: UsersDTO,
        account_id: uuid.UUID,
        **kwargs,
    ) -> AccountBalancesDTO | None:
        """Return a single account balance row when present."""
        records = self.get_balances(owner=owner, account_id=account_id, **kwargs)
        if getattr(records, "empty", True):
            return None

        return self.dto_type.model_validate(records.iloc[0].to_dict())

    def refresh(self, *, concurrently: bool = False, **kwargs) -> None:
        """Refresh the account_balances materialized view."""
        self._repository.refresh_materialized_view(concurrently=concurrently, **kwargs)
