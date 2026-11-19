"""Read-only DTO for the owner_yearly_balances materialized view."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class OwnerYearlyBalancesDTO(BaseModel):
    """Projection row from papita_transactions.owner_yearly_balances."""

    model_config = ConfigDict(from_attributes=True)

    owner_id: uuid.UUID
    balance_year: int = Field(ge=1900, le=9999)
    currency: str = Field(min_length=3, max_length=3)
    yearly_net_change: float
    total_balance: float
