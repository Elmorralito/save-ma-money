"""Read-only service for owner_yearly_balances materialized view queries."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from papita_txnsmodel.access.owner_yearly_balances.dto import OwnerYearlyBalancesDTO
from papita_txnsmodel.access.owner_yearly_balances.repository import OwnerYearlyBalancesRepository
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.session import get_session_manager


class OwnerYearlyBalancesService(BaseModel):
    """Combined yearly balance queries across all accounts for one owner."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    connector: Any = Field(default_factory=get_session_manager)
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

        return self._repository.get_yearly_balances(
            owner=owner,
            balance_year=balance_year,
            currency=currency,
            **kwargs,
        )

    def refresh(self, *, concurrently: bool = False, **kwargs) -> None:
        """Refresh the owner_yearly_balances materialized view."""
        self._repository.refresh_materialized_view(concurrently=concurrently, **kwargs)
