"""SQLModel filter builders for tenant-scoped transaction list queries."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import or_

from papita_txnsmodel.model.enums import TransactionKind, TransactionStatus
from papita_txnsmodel.model.transactions import Transactions


@dataclass(frozen=True)
class TransactionListFilterSpec:  # pylint: disable=too-many-instance-attributes
    """Filter criteria for tenant-scoped ``Transactions`` list queries."""

    transaction_kind: TransactionKind | None = None
    exclude_transfer: bool = False
    status: TransactionStatus | None = None
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    source_account_id: uuid.UUID | None = None
    destination_account_id: uuid.UUID | None = None
    start_date: date | datetime | None = None
    end_date: date | datetime | None = None
    min_amount: float | None = None
    max_amount: float | None = None
    search: str | None = None


def _append_kind_filters(filters: list[Any], spec: TransactionListFilterSpec) -> None:
    """Append transaction-kind filters when requested."""
    if spec.transaction_kind is not None:
        filters.append(Transactions.transaction_kind == spec.transaction_kind)
    elif spec.exclude_transfer:
        filters.append(Transactions.transaction_kind != TransactionKind.TRANSFER)


def _append_amount_filters(filters: list[Any], spec: TransactionListFilterSpec) -> None:
    """Append optional minimum and maximum amount filters."""
    if spec.min_amount is not None:
        filters.append(Transactions.amount >= spec.min_amount)
    if spec.max_amount is not None:
        filters.append(Transactions.amount <= spec.max_amount)


def _append_search_filter(filters: list[Any], spec: TransactionListFilterSpec) -> None:
    """Append a case-insensitive description substring filter."""
    if spec.search is None:
        return
    needle = spec.search.strip()
    if needle:
        filters.append(Transactions.description.ilike(f"%{needle}%"))


def build_transaction_list_filters(spec: TransactionListFilterSpec) -> tuple[Any, ...]:
    """Build SQLAlchemy WHERE clauses for ``Transactions`` list queries.

    Args:
        spec: Filter criteria describing kind, status, account legs, dates, amounts,
            and description search.

    Returns:
        Tuple of SQLAlchemy boolean expressions for ``get_records(*filters)``.
    """
    filters: list[Any] = []

    _append_kind_filters(filters, spec)

    if spec.status is not None:
        filters.append(Transactions.status == spec.status)

    if spec.account_id is not None:
        filters.append(
            or_(
                Transactions.from_account_id == spec.account_id,
                Transactions.to_account_id == spec.account_id,
            )
        )

    if spec.category_id is not None:
        filters.append(Transactions.category_id == spec.category_id)

    if spec.source_account_id is not None:
        filters.append(Transactions.from_account_id == spec.source_account_id)

    if spec.destination_account_id is not None:
        filters.append(Transactions.to_account_id == spec.destination_account_id)

    if spec.start_date is not None:
        start_ts = (
            spec.start_date if isinstance(spec.start_date, datetime) else datetime.combine(spec.start_date, time.min)
        )
        filters.append(Transactions.transaction_ts >= start_ts)

    if spec.end_date is not None:
        end_ts = spec.end_date if isinstance(spec.end_date, datetime) else datetime.combine(spec.end_date, time.max)
        filters.append(Transactions.transaction_ts <= end_ts)

    _append_amount_filters(filters, spec)
    _append_search_filter(filters, spec)

    return tuple(filters)
