"""Read-only service for owner monthly/quarterly/biannual balance materialized views."""

from __future__ import annotations

from typing import Type

import pandas as pd
from pydantic import BaseModel, ConfigDict, model_validator

from papita_txnsmodel.access.owner_period_balances.repository import OwnerPeriodBalancesRepository
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.connector import SQLDatabaseConnector


class OwnerPeriodBalancesService(BaseModel):
    """Combined monthly, quarterly, and biannual balance queries for one owner."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    connector: Type[SQLDatabaseConnector] = SQLDatabaseConnector
    repository_type: type[OwnerPeriodBalancesRepository] = OwnerPeriodBalancesRepository

    _repository: OwnerPeriodBalancesRepository | None = None

    @model_validator(mode="after")
    def _validate(self) -> "OwnerPeriodBalancesService":
        """Initialize repository."""
        self._repository = self.repository_type()
        return self

    def close(self) -> None:
        """Close the database connection."""
        self.connector.close()

    def get_monthly_balances(
        self,
        *,
        owner: UsersDTO,
        balance_year: int | None = None,
        balance_month: int | None = None,
        currency: str | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Return monthly combined balance rows for a tenant owner."""
        if owner is None:
            raise ValueError("owner=UsersDTO is required for monthly balance queries.")

        filters: dict[str, object] = {}
        if balance_year is not None:
            filters["balance_year"] = balance_year
        if balance_month is not None:
            filters["balance_month"] = balance_month
        if currency is not None:
            filters["currency"] = currency

        from papita_txnsmodel.access.balance_reports.filter_validation import validate_report_filters
        from papita_txnsmodel.access.balance_reports.repository import BalanceReportsRepository

        validated = validate_report_filters("owner_monthly_balances", filters)
        return BalanceReportsRepository().query(
            report_id="owner_monthly_balances",
            owner=owner,
            filters=validated,
            **kwargs,
        )

    def get_quarterly_balances(
        self,
        *,
        owner: UsersDTO,
        balance_year: int | None = None,
        balance_quarter: int | None = None,
        currency: str | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Return quarterly combined balance rows for a tenant owner."""
        if owner is None:
            raise ValueError("owner=UsersDTO is required for quarterly balance queries.")

        filters: dict[str, object] = {}
        if balance_year is not None:
            filters["balance_year"] = balance_year
        if balance_quarter is not None:
            filters["balance_quarter"] = balance_quarter
        if currency is not None:
            filters["currency"] = currency

        from papita_txnsmodel.access.balance_reports.filter_validation import validate_report_filters
        from papita_txnsmodel.access.balance_reports.repository import BalanceReportsRepository

        validated = validate_report_filters("owner_quarterly_balances", filters)
        return BalanceReportsRepository().query(
            report_id="owner_quarterly_balances",
            owner=owner,
            filters=validated,
            **kwargs,
        )

    def get_biannual_balances(
        self,
        *,
        owner: UsersDTO,
        balance_year: int | None = None,
        balance_half: int | None = None,
        currency: str | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Return biannual combined balance rows for a tenant owner."""
        if owner is None:
            raise ValueError("owner=UsersDTO is required for biannual balance queries.")

        filters: dict[str, object] = {}
        if balance_year is not None:
            filters["balance_year"] = balance_year
        if balance_half is not None:
            filters["balance_half"] = balance_half
        if currency is not None:
            filters["currency"] = currency

        from papita_txnsmodel.access.balance_reports.filter_validation import validate_report_filters
        from papita_txnsmodel.access.balance_reports.repository import BalanceReportsRepository

        validated = validate_report_filters("owner_biannual_balances", filters)
        return BalanceReportsRepository().query(
            report_id="owner_biannual_balances",
            owner=owner,
            filters=validated,
            **kwargs,
        )

    def refresh(self, *, concurrently: bool = False, **kwargs) -> None:
        """Refresh monthly, quarterly, and biannual owner balance materialized views."""
        self._repository.refresh_materialized_views(concurrently=concurrently, **kwargs)
