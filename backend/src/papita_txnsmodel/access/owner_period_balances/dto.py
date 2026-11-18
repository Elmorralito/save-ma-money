"""Read-only DTOs for owner period balance materialized views."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class OwnerMonthlyBalancesDTO(BaseModel):
    """Projection row from papita_transactions.owner_monthly_balances."""

    model_config = ConfigDict(from_attributes=True)

    owner_id: uuid.UUID
    balance_year: int = Field(ge=1900, le=9999)
    balance_month: int = Field(ge=1, le=12)
    currency: str = Field(min_length=3, max_length=3)
    monthly_net_change: float
    total_balance: float


class OwnerQuarterlyBalancesDTO(BaseModel):
    """Projection row from papita_transactions.owner_quarterly_balances."""

    model_config = ConfigDict(from_attributes=True)

    owner_id: uuid.UUID
    balance_year: int = Field(ge=1900, le=9999)
    balance_quarter: int = Field(ge=1, le=4)
    currency: str = Field(min_length=3, max_length=3)
    quarterly_net_change: float
    total_balance: float


class OwnerBiannualBalancesDTO(BaseModel):
    """Projection row from papita_transactions.owner_biannual_balances."""

    model_config = ConfigDict(from_attributes=True)

    owner_id: uuid.UUID
    balance_year: int = Field(ge=1900, le=9999)
    balance_half: int = Field(ge=1, le=2)
    currency: str = Field(min_length=3, max_length=3)
    biannual_net_change: float
    total_balance: float
