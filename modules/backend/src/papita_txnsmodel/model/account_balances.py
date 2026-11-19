"""Read-only SQLModel mapping for the account_balances materialized view."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from papita_txnsmodel.model.base import SCHEMA_NAME
from papita_txnsmodel.model.contstants import ACCOUNT_BALANCES_VIEW


class AccountBalances(SQLModel, table=True):  # type: ignore[call-arg]
    """ORM projection of ``papita_transactions.account_balances``."""

    __tablename__ = ACCOUNT_BALANCES_VIEW
    __table_args__ = {"schema": SCHEMA_NAME}

    owner_id: uuid.UUID = Field(primary_key=True)
    account_id: uuid.UUID = Field(primary_key=True)
    currency: str = Field(min_length=3, max_length=3)
    balance: float
    last_activity_ts: datetime | None = None
