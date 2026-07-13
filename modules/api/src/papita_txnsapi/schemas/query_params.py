"""Query-parameter helpers for transaction and movement list routes."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, TypedDict

from fastapi import Query
from pydantic import BaseModel, Field

from papita_txnsapi.schemas.converters import parse_transaction_kind, parse_transaction_status
from papita_txnsmodel.model.enums import TransactionKind, TransactionStatus


class TransactionListServiceKwargs(TypedDict):
    """Keyword arguments accepted by ``TransactionsService.list_transactions``."""

    account_id: uuid.UUID | None
    category_id: uuid.UUID | None
    transaction_kind: TransactionKind | None
    exclude_transfer: bool
    status: TransactionStatus | None
    start_date: date | None
    end_date: date | None
    min_amount: float | None
    max_amount: float | None
    search: str | None


class MovementListServiceKwargs(TypedDict):
    """Keyword arguments accepted by ``TransactionsService.list_transfers``."""

    source_account_id: uuid.UUID | None
    destination_account_id: uuid.UUID | None
    status: TransactionStatus | None
    start_date: date | None
    end_date: date | None


class TransactionListQuery(BaseModel):
    """Bundled query parameters for ``GET /transactions``."""

    account_id: uuid.UUID | None = Field(default=None, description="Filter by primary account (from or to)")
    category_id: uuid.UUID | None = Field(default=None, description="Filter by category")
    transaction_type: str | None = Field(default=None, description="Filter by income/expense/transfer")
    status: str | None = Field(default=None, description="Filter by pending/completed/cancelled")
    start_date: date | None = Field(default=None, description="Filter by start date")
    end_date: date | None = Field(default=None, description="Filter by end date")
    min_amount: float | None = Field(default=None, description="Minimum amount filter", ge=0)
    max_amount: float | None = Field(default=None, description="Maximum amount filter", ge=0)
    search: str | None = Field(default=None, description="Search in description")

    def service_kwargs(self) -> TransactionListServiceKwargs:
        """Map API query parameters to ``TransactionsService.list_transactions`` kwargs."""
        transaction_kind = parse_transaction_kind(self.transaction_type) if self.transaction_type else None
        return TransactionListServiceKwargs(
            account_id=self.account_id,
            category_id=self.category_id,
            transaction_kind=transaction_kind,
            exclude_transfer=self.transaction_type is None,
            status=parse_transaction_status(self.status) if self.status else None,
            start_date=self.start_date,
            end_date=self.end_date,
            min_amount=self.min_amount,
            max_amount=self.max_amount,
            search=self.search,
        )


class MovementListQuery(BaseModel):
    """Bundled query parameters for ``GET /movements``."""

    source_account_id: uuid.UUID | None = Field(default=None, description="Filter by source account")
    destination_account_id: uuid.UUID | None = Field(default=None, description="Filter by destination account")
    status: str | None = Field(default=None, description="Filter by pending/completed/cancelled")
    start_date: date | None = Field(default=None, description="Filter by start date")
    end_date: date | None = Field(default=None, description="Filter by end date")

    def service_kwargs(self) -> MovementListServiceKwargs:
        """Map API query parameters to ``TransactionsService.list_transfers`` kwargs."""
        return MovementListServiceKwargs(
            source_account_id=self.source_account_id,
            destination_account_id=self.destination_account_id,
            status=parse_transaction_status(self.status) if self.status else None,
            start_date=self.start_date,
            end_date=self.end_date,
        )


def get_transaction_list_query(  # pylint: disable=too-many-arguments
    *,
    account_id: Annotated[uuid.UUID | None, Query(description="Filter by primary account (from or to)")] = None,
    category_id: Annotated[uuid.UUID | None, Query(description="Filter by category")] = None,
    transaction_type: Annotated[str | None, Query(description="Filter by income/expense/transfer")] = None,
    status: Annotated[str | None, Query(description="Filter by pending/completed/cancelled")] = None,
    start_date: Annotated[date | None, Query(description="Filter by start date")] = None,
    end_date: Annotated[date | None, Query(description="Filter by end date")] = None,
    min_amount: Annotated[float | None, Query(description="Minimum amount filter", ge=0)] = None,
    max_amount: Annotated[float | None, Query(description="Maximum amount filter", ge=0)] = None,
    search: Annotated[str | None, Query(description="Search in description")] = None,
) -> TransactionListQuery:
    """FastAPI dependency that collects transaction list query parameters."""
    return TransactionListQuery(
        account_id=account_id,
        category_id=category_id,
        transaction_type=transaction_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        search=search,
    )


def get_movement_list_query(
    *,
    source_account_id: Annotated[uuid.UUID | None, Query(description="Filter by source account")] = None,
    destination_account_id: Annotated[uuid.UUID | None, Query(description="Filter by destination account")] = None,
    status: Annotated[str | None, Query(description="Filter by pending/completed/cancelled")] = None,
    start_date: Annotated[date | None, Query(description="Filter by start date")] = None,
    end_date: Annotated[date | None, Query(description="Filter by end date")] = None,
) -> MovementListQuery:
    """FastAPI dependency that collects movement list query parameters."""
    return MovementListQuery(
        source_account_id=source_account_id,
        destination_account_id=destination_account_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )
