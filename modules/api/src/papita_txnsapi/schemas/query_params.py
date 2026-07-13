"""Query-parameter helpers for transaction, movement, and report list routes."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated, Literal, TypedDict

from fastapi import Query
from pydantic import BaseModel, Field, model_validator

from papita_txnsapi.schemas.converters import parse_transaction_kind, parse_transaction_status
from papita_txnsmodel.model.enums import TransactionKind, TransactionStatus

_ALLOWED_SPENDING_GROUP_BY = frozenset({"category", "account"})
_ALLOWED_TREND_PERIODS = frozenset({"daily", "weekly", "monthly", "yearly"})
_ALLOWED_EXPORT_REPORT_TYPES = frozenset({"spending", "cash-flow", "trends"})
_ALLOWED_EXPORT_FORMATS = frozenset({"csv", "json"})
DEFERRED_EXPORT_FORMATS = frozenset({"xlsx", "pdf"})


def date_to_start_datetime(value: date) -> datetime:
    """Convert a calendar date to an inclusive UTC start-of-day timestamp."""
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def date_to_end_datetime(value: date) -> datetime:
    """Convert a calendar date to an inclusive UTC end-of-day timestamp."""
    return datetime.combine(value, time.max, tzinfo=timezone.utc)


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


class ReportSpendingServiceKwargs(TypedDict):
    """Keyword arguments accepted by ``ReportService.spending``."""

    start_date: datetime
    end_date: datetime
    group_by: Literal["category", "account"]
    account_id: uuid.UUID | None


class ReportCashFlowServiceKwargs(TypedDict):
    """Keyword arguments accepted by ``ReportService.cash_flow``."""

    start_date: datetime
    end_date: datetime
    account_id: uuid.UUID | None
    refresh_balances: bool


class ReportTrendsServiceKwargs(TypedDict):
    """Keyword arguments accepted by ``ReportService.trends``."""

    start_date: datetime
    end_date: datetime
    period: Literal["daily", "weekly", "monthly", "yearly"]
    account_id: uuid.UUID | None
    category_id: uuid.UUID | None


class ReportExportServiceKwargs(TypedDict):
    """Keyword arguments accepted by ``ReportService.export``."""

    report_type: Literal["spending", "cash-flow", "trends"]
    export_format: Literal["csv", "json"]
    start_date: datetime
    end_date: datetime
    account_id: uuid.UUID | None
    group_by: Literal["category", "account"]
    period: Literal["daily", "weekly", "monthly", "yearly"]


class ReportSpendingQuery(BaseModel):
    """Bundled query parameters for ``GET /reports/spending``."""

    start_date: date = Field(description="Report start date")
    end_date: date = Field(description="Report end date")
    group_by: str = Field(default="category", description="Group by category or account")
    account_id: uuid.UUID | None = Field(default=None, description="Optional account filter")

    @model_validator(mode="after")
    def _validate_window(self) -> ReportSpendingQuery:
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        if self.group_by not in _ALLOWED_SPENDING_GROUP_BY:
            raise ValueError("group_by must be one of: category, account")
        return self

    def service_kwargs(self) -> ReportSpendingServiceKwargs:
        """Map API query parameters to ``ReportService.spending`` kwargs."""
        return ReportSpendingServiceKwargs(
            start_date=date_to_start_datetime(self.start_date),
            end_date=date_to_end_datetime(self.end_date),
            group_by=self.group_by,  # type: ignore[typeddict-item]
            account_id=self.account_id,
        )


class ReportCashFlowQuery(BaseModel):
    """Bundled query parameters for ``GET /reports/cash-flow``."""

    start_date: date = Field(description="Report start date")
    end_date: date = Field(description="Report end date")
    account_id: uuid.UUID | None = Field(default=None, description="Optional account filter")
    refresh_balances: bool = Field(default=True, description="Refresh account_balances MVs before query (G9)")

    @model_validator(mode="after")
    def _validate_window(self) -> ReportCashFlowQuery:
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self

    def service_kwargs(self) -> ReportCashFlowServiceKwargs:
        """Map API query parameters to ``ReportService.cash_flow`` kwargs."""
        return ReportCashFlowServiceKwargs(
            start_date=date_to_start_datetime(self.start_date),
            end_date=date_to_end_datetime(self.end_date),
            account_id=self.account_id,
            refresh_balances=self.refresh_balances,
        )


class ReportTrendsQuery(BaseModel):
    """Bundled query parameters for ``GET /reports/trends``."""

    months: int = Field(default=6, ge=1, le=120, description="Number of months to analyze")
    period: str = Field(default="monthly", description="Series bucket size")
    start_date: date | None = Field(default=None, description="Explicit analysis start date")
    end_date: date | None = Field(default=None, description="Explicit analysis end date")
    category_id: uuid.UUID | None = Field(default=None, description="Optional category filter")
    account_id: uuid.UUID | None = Field(default=None, description="Optional account filter")

    @model_validator(mode="after")
    def _validate_window(self) -> ReportTrendsQuery:
        if self.period not in _ALLOWED_TREND_PERIODS:
            raise ValueError("period must be one of: daily, weekly, monthly, yearly")
        resolved_end = self.end_date or date.today()
        resolved_start = self.start_date or (resolved_end - timedelta(days=30 * self.months))
        if resolved_start > resolved_end:
            raise ValueError("start_date must be on or before end_date")
        self.start_date = resolved_start
        self.end_date = resolved_end
        return self

    def service_kwargs(self) -> ReportTrendsServiceKwargs:
        """Map API query parameters to ``ReportService.trends`` kwargs."""
        if self.start_date is None or self.end_date is None:
            raise ValueError("start_date and end_date must be resolved")
        return ReportTrendsServiceKwargs(
            start_date=date_to_start_datetime(self.start_date),
            end_date=date_to_end_datetime(self.end_date),
            period=self.period,  # type: ignore[typeddict-item]
            account_id=self.account_id,
            category_id=self.category_id,
        )


class ReportExportQuery(BaseModel):
    """Bundled query parameters for ``GET /reports/export``."""

    report_type: str = Field(description="Report to export (spending, cash-flow, trends)")
    export_format: str = Field(description="Export format (csv or json; xlsx/pdf deferred)")
    start_date: date = Field(description="Report start date")
    end_date: date = Field(description="Report end date")
    account_id: uuid.UUID | None = Field(default=None, description="Optional account filter")
    group_by: str = Field(default="category", description="Spending group_by when report_type=spending")
    period: str = Field(default="monthly", description="Trends period when report_type=trends")

    @model_validator(mode="after")
    def _validate_export(self) -> ReportExportQuery:
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        if self.report_type not in _ALLOWED_EXPORT_REPORT_TYPES:
            raise ValueError("report_type must be one of: spending, cash-flow, trends")
        if self.export_format in DEFERRED_EXPORT_FORMATS:
            return self
        if self.export_format not in _ALLOWED_EXPORT_FORMATS:
            raise ValueError("format must be one of: csv, json, xlsx, pdf")
        if self.group_by not in _ALLOWED_SPENDING_GROUP_BY:
            raise ValueError("group_by must be one of: category, account")
        if self.period not in _ALLOWED_TREND_PERIODS:
            raise ValueError("period must be one of: daily, weekly, monthly, yearly")
        return self

    @property
    def is_deferred_format(self) -> bool:
        """Return True when the requested export format is deferred (501)."""
        return self.export_format in DEFERRED_EXPORT_FORMATS

    def service_kwargs(self) -> ReportExportServiceKwargs:
        """Map API query parameters to ``ReportService.export`` kwargs."""
        if self.is_deferred_format:
            raise ValueError(f"Export format '{self.export_format}' is deferred")
        return ReportExportServiceKwargs(
            report_type=self.report_type,  # type: ignore[typeddict-item]
            export_format=self.export_format,  # type: ignore[typeddict-item]
            start_date=date_to_start_datetime(self.start_date),
            end_date=date_to_end_datetime(self.end_date),
            account_id=self.account_id,
            group_by=self.group_by,  # type: ignore[typeddict-item]
            period=self.period,  # type: ignore[typeddict-item]
        )


def get_report_spending_query(  # pylint: disable=too-many-arguments
    *,
    start_date: Annotated[date, Query(description="Report start date")],
    end_date: Annotated[date, Query(description="Report end date")],
    group_by: Annotated[str, Query(description="Group by category or account")] = "category",
    account_id: Annotated[uuid.UUID | None, Query(description="Optional account filter")] = None,
) -> ReportSpendingQuery:
    """FastAPI dependency that collects spending report query parameters."""
    return ReportSpendingQuery(
        start_date=start_date,
        end_date=end_date,
        group_by=group_by,
        account_id=account_id,
    )


def get_report_cash_flow_query(
    *,
    start_date: Annotated[date, Query(description="Report start date")],
    end_date: Annotated[date, Query(description="Report end date")],
    account_id: Annotated[uuid.UUID | None, Query(description="Optional account filter")] = None,
    refresh_balances: Annotated[bool, Query(description="Refresh balance MVs before query")] = True,
) -> ReportCashFlowQuery:
    """FastAPI dependency that collects cash-flow report query parameters."""
    return ReportCashFlowQuery(
        start_date=start_date,
        end_date=end_date,
        account_id=account_id,
        refresh_balances=refresh_balances,
    )


def get_report_trends_query(  # pylint: disable=too-many-arguments
    *,
    months: Annotated[int, Query(description="Number of months to analyze", ge=1, le=120)] = 6,
    period: Annotated[str, Query(description="Series bucket size")] = "monthly",
    start_date: Annotated[date | None, Query(description="Explicit analysis start date")] = None,
    end_date: Annotated[date | None, Query(description="Explicit analysis end date")] = None,
    category_id: Annotated[uuid.UUID | None, Query(description="Optional category filter")] = None,
    account_id: Annotated[uuid.UUID | None, Query(description="Optional account filter")] = None,
) -> ReportTrendsQuery:
    """FastAPI dependency that collects trends report query parameters."""
    return ReportTrendsQuery(
        months=months,
        period=period,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        account_id=account_id,
    )


def get_report_export_query(  # pylint: disable=too-many-arguments
    *,
    report_type: Annotated[str, Query(description="Report to export")],
    export_format: Annotated[str, Query(alias="format", description="Export format (csv or json)")],
    start_date: Annotated[date, Query(description="Report start date")],
    end_date: Annotated[date, Query(description="Report end date")],
    account_id: Annotated[uuid.UUID | None, Query(description="Optional account filter")] = None,
    group_by: Annotated[str, Query(description="Spending group_by")] = "category",
    period: Annotated[str, Query(description="Trends period")] = "monthly",
) -> ReportExportQuery:
    """FastAPI dependency that collects export report query parameters."""
    return ReportExportQuery(
        report_type=report_type,
        export_format=export_format,
        start_date=start_date,
        end_date=end_date,
        account_id=account_id,
        group_by=group_by,
        period=period,
    )
