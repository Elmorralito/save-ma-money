"""Read-only DTO for the account_balances materialized view."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AccountBalancesDTO(BaseModel):
    """Projection row from papita_transactions.account_balances."""

    model_config = ConfigDict(from_attributes=True)

    owner_id: uuid.UUID
    account_id: uuid.UUID
    currency: str = Field(min_length=3, max_length=3)
    balance: float
    last_activity_ts: datetime | None = None
