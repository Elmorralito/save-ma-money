"""Read-only service for owner_yearly_balances materialized view queries."""

from __future__ import annotations

from typing import Type

import pandas as pd
from pydantic import BaseModel, ConfigDict, model_validator

from papita_txnsmodel.access.owner_yearly_balances.dto import OwnerYearlyBalancesDTO
from papita_txnsmodel.access.owner_yearly_balances.repository import OwnerYearlyBalancesRepository
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.connector import SQLDatabaseConnector


class OwnerYearlyBalancesService(BaseModel):
    """Combined yearly balance queries across all accounts for one owner."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    connector: Type[SQLDatabaseConnector] = SQLDatabaseConnector
    repository_type: type[OwnerYearlyBalancesRepository] = OwnerYearlyBalancesRepository
    dto_type: type[OwnerYearlyBalancesDTO] = OwnerYearlyBalancesDTO

    _repository: OwnerYearlyBalancesRepository | None = None

    @model_validator(mode="after")
    def _validate(self) -> "OwnerYearlyBalancesService":
        """Initialize repository."""
        self._repository = self.repository_type()
        return self

    def close(self) -> None:
        """Close the database connection."""
        self.connector.close()

    def get_yearly_balances(
        self,
        *,
        owner: UsersDTO,
        balance_year: int | None = None,
        currency: str | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Return combined yearly balance rows for a tenant owner."""
        if owner is None:
            raise ValueError("owner=UsersDTO is required for yearly balance queries.")

        filters: dict[str, object] = {}
        if balance_year is not None:
            filters["balance_year"] = balance_year
        if currency is not None:
            filters["currency"] = currency

        from papita_txnsmodel.access.balance_reports.filter_validation import validate_report_filters
        from papita_txnsmodel.access.balance_reports.repository import BalanceReportsRepository

        validated = validate_report_filters("owner_yearly_balances", filters)
        return BalanceReportsRepository().query(
            report_id="owner_yearly_balances",
            owner=owner,
            filters=validated,
            **kwargs,
        )

    def refresh(self, *, concurrently: bool = False, **kwargs) -> None:
        """Refresh the owner_yearly_balances materialized view."""
        self._repository.refresh_materialized_view(concurrently=concurrently, **kwargs)
