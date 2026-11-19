"""Read-only service for owner monthly/quarterly/biannual balance materialized views."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from papita_txnsmodel.access.owner_period_balances.repository import OwnerPeriodBalancesRepository
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.session import get_session_manager


class OwnerPeriodBalancesService(BaseModel):
    """Combined monthly, quarterly, and biannual balance queries for one owner."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    connector: Any = Field(default_factory=get_session_manager)
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

        return self._repository.get_monthly_balances(
            owner=owner,
            balance_year=balance_year,
            balance_month=balance_month,
            currency=currency,
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

        return self._repository.get_quarterly_balances(
            owner=owner,
            balance_year=balance_year,
            balance_quarter=balance_quarter,
            currency=currency,
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

        return self._repository.get_biannual_balances(
            owner=owner,
            balance_year=balance_year,
            balance_half=balance_half,
            currency=currency,
            **kwargs,
        )

    def refresh(self, *, concurrently: bool = False, **kwargs) -> None:
        """Refresh monthly, quarterly, and biannual owner balance materialized views."""
        self._repository.refresh_materialized_views(concurrently=concurrently, **kwargs)
