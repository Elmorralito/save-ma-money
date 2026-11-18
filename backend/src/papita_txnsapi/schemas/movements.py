"""Movement request/response schemas for PPT-037 TRANSFER alias router.

Maps REST movement payloads to ``TransactionsDTO`` transfer rows. Field names
``source_account_id`` / ``destination_account_id`` map to ``from_account_id`` /
``to_account_id`` in the model layer.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from papita_txnsapi.config.settings import MAX_DESCRIPTION_LENGTH
from papita_txnsapi.schemas.accounts import paginate_dataframe
from papita_txnsapi.schemas.converters import enum_to_api_slug
from papita_txnsapi.schemas.transactions import _parse_transaction_date, _relation_uuid, transactions_from_dataframe
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.model.enums import TransactionKind


class MovementCreate(BaseModel):
    """Request body for ``POST /movements``."""

    model_config = ConfigDict(extra="forbid")

    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    description: str = Field(default="", max_length=MAX_DESCRIPTION_LENGTH)
    movement_date: date | datetime
    scheduled: bool = False

    def to_transactions_dto(self, *, owner_id: uuid.UUID) -> TransactionsDTO:
        """Build a transfer ``TransactionsDTO`` for ``TransactionsService.create_transfer``."""
        return TransactionsDTO(
            owner_id=owner_id,
            transaction_kind=TransactionKind.TRANSFER,
            amount=self.amount,
            currency=self.currency.upper(),
            transaction_ts=_parse_transaction_date(self.movement_date),
            from_account_id=self.source_account_id,
            to_account_id=self.destination_account_id,
            description=self.description,
        )


class MovementUpdate(BaseModel):
    """Request body for ``PUT /movements/{movement_id}`` (PENDING only)."""

    model_config = ConfigDict(extra="forbid")

    source_account_id: uuid.UUID | None = None
    destination_account_id: uuid.UUID | None = None
    amount: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    movement_date: date | datetime | None = None

    def apply_to(self, existing: TransactionsDTO) -> TransactionsDTO:
        """Merge partial update fields onto an existing transfer DTO."""
        updates = self.model_dump(exclude_unset=True, exclude={"movement_date"})
        if self.currency is not None:
            updates["currency"] = self.currency.upper()
        if self.movement_date is not None:
            updates["transaction_ts"] = _parse_transaction_date(self.movement_date)
        if self.source_account_id is not None:
            updates["from_account_id"] = self.source_account_id
        if self.destination_account_id is not None:
            updates["to_account_id"] = self.destination_account_id
        return existing.model_copy(update=updates)


class MovementResponse(BaseModel):
    """Movement (TRANSFER) resource returned by alias CRUD endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    source_account_name: str | None = None
    destination_account_name: str | None = None
    amount: float
    currency: str
    status: str
    description: str
    movement_date: date
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_dto(cls, transfer: TransactionsDTO, *, include_names: bool = False) -> MovementResponse:
        """Build an API response from a transfer ``TransactionsDTO``."""
        source_name: str | None = None
        destination_name: str | None = None
        if include_names:
            from_account = transfer.from_account_id
            to_account = transfer.to_account_id
            if isinstance(from_account, AccountsDTO):
                source_name = from_account.name
            if isinstance(to_account, AccountsDTO):
                destination_name = to_account.name

        source_id = _relation_uuid(transfer.from_account_id)
        destination_id = _relation_uuid(transfer.to_account_id)
        if source_id is None or destination_id is None:
            raise ValueError("Transfer requires source and destination account ids.")

        ts = transfer.transaction_ts
        movement_date = ts.date() if isinstance(ts, datetime) else ts
        return cls(
            id=transfer.id,
            source_account_id=source_id,
            destination_account_id=destination_id,
            source_account_name=source_name,
            destination_account_name=destination_name,
            amount=float(transfer.amount),
            currency=transfer.currency,
            status=enum_to_api_slug(transfer.status),
            description=transfer.description,
            movement_date=movement_date,
            created_at=transfer.created_at,
            updated_at=transfer.updated_at,
        )


class MovementExecuteResponse(BaseModel):
    """Response body for ``POST /movements/{movement_id}/execute``."""

    id: uuid.UUID
    status: str
    executed_at: datetime


def movements_from_dataframe(df: pd.DataFrame) -> list[TransactionsDTO]:
    """Convert a transfer query DataFrame to DTO instances."""
    return transactions_from_dataframe(df)


__all__ = [
    "MovementCreate",
    "MovementExecuteResponse",
    "MovementResponse",
    "MovementUpdate",
    "movements_from_dataframe",
    "paginate_dataframe",
]
