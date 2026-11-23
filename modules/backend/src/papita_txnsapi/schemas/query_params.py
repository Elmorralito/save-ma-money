"""FastAPI query-parameter models and dependencies for list and report routes.

Bridges HTTP query strings to service-layer keyword arguments for transactions,
transfer movements, and reports. OpenAPI ``Query`` dependencies build Pydantic
models; each model exposes ``service_kwargs()`` that normalizes enums, date
windows, and defaults before calling ``TransactionsService`` / ``ReportService``.

Calendar dates for reports become inclusive UTC day bounds via
``date_to_start_datetime`` / ``date_to_end_datetime``. Export formats ``xlsx`` and
``pdf`` are deferred (``DEFERRED_EXPORT_FORMATS``) and must be rejected by the
router with HTTP 501 rather than forwarded to the service.

Key exports:
    DEFERRED_EXPORT_FORMATS: ``xlsx`` / ``pdf`` formats for router 501 handling.
    date_to_start_datetime / date_to_end_datetime: Inclusive UTC day bounds.
    TransactionListQuery / MovementListQuery (+ ``*ServiceKwargs``, ``get_*``).
    UpcomingDuesQuery / get_upcoming_dues_query (PPT-073).
    ReportSpendingQuery / ReportCashFlowQuery / ReportTrendsQuery /
    ReportExportQuery (+ matching TypedDicts and ``get_report_*_query`` helpers).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated, Literal, TypedDict

from fastapi import Depends, Query, Request
from pydantic import BaseModel, Field, model_validator

from papita_txnsapi.config.settings import MAX_REPORT_WINDOW_DAYS, MAX_SEARCH_LENGTH, Settings, get_settings
from papita_txnsapi.core.client_contract import (
    COMPAT_SUNSET_DATE,
    HEADER_DEPRECATION,
    HEADER_SUNSET,
    cash_flow_refresh_balances_default,
)
from papita_txnsapi.schemas.converters import (
    parse_cashflow_bucket,
    parse_settlement_status,
    parse_transaction_kind,
    parse_transaction_status,
)
from papita_txnsmodel.model.enums import CashflowBucket, SettlementStatus, TransactionKind, TransactionStatus

_ALLOWED_SPENDING_GROUP_BY = frozenset({"category", "account"})
_ALLOWED_TREND_PERIODS = frozenset({"daily", "weekly", "monthly", "yearly"})
_ALLOWED_EXPORT_REPORT_TYPES = frozenset({"spending", "cash-flow", "trends"})
_ALLOWED_EXPORT_FORMATS = frozenset({"csv", "json"})
# Accepted in query validation but not implemented; routers should return HTTP 501.
DEFERRED_EXPORT_FORMATS = frozenset({"xlsx", "pdf"})
"""Export formats that validate on the query model but must not reach the service.

Routers check ``ReportExportQuery.is_deferred_format`` (or membership in this set)
and respond with HTTP 501. ``service_kwargs()`` raises ``ValueError`` if called
for these formats.
"""


def _validate_report_window(start: date, end: date, *, max_days: int = MAX_REPORT_WINDOW_DAYS) -> None:
    """Ensure report date windows are ordered and within the max span.

    Args:
        start: Inclusive window start.
        end: Inclusive window end.
        max_days: Inclusive maximum span from settings (PPT-044).

    Raises:
        ValueError: When the window is inverted or longer than ``max_days``.
    """
    if start > end:
        raise ValueError("start_date must be on or before end_date")
    if (end - start).days > max_days:
        raise ValueError(f"report window must be at most {max_days} days")


def _enforce_report_window(start: date, end: date, settings: Settings) -> None:
    """Apply settings-backed report window bound (raises domain ``ValueError``)."""
    _validate_report_window(start, end, max_days=settings.API_REPORT_WINDOW_MAX_DAYS)


def date_to_start_datetime(value: date) -> datetime:
    """Convert a calendar date to an inclusive UTC start-of-day timestamp.

    Args:
        value: Calendar date in the caller's report window (date-only, no time).

    Returns:
        Timezone-aware ``datetime`` at ``00:00:00.000000`` UTC on ``value``.
    """
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def date_to_end_datetime(value: date) -> datetime:
    """Convert a calendar date to an inclusive UTC end-of-day timestamp.

    Args:
        value: Calendar date in the caller's report window (date-only, no time).

    Returns:
        Timezone-aware ``datetime`` at ``23:59:59.999999`` UTC on ``value``.
    """
    return datetime.combine(value, time.max, tzinfo=timezone.utc)


class TransactionListServiceKwargs(TypedDict):
    """Keyword arguments accepted by ``TransactionsService.list_transactions``.

    Attributes:
        account_id: Optional primary account filter (from or to side).
        source_account_id: Optional source (from) account filter.
        destination_account_id: Optional destination (to) account filter.
        category_id: Optional category filter.
        transaction_kind: Parsed ``TransactionKind``, or ``None`` when omitted.
        exclude_transfer: When ``True``, omit transfer rows.
        status: Parsed ``TransactionStatus``, or ``None`` when omitted.
        start_date: Inclusive lower bound as a calendar date, if any.
        end_date: Inclusive upper bound as a calendar date, if any.
        min_amount: Optional non-negative minimum amount.
        max_amount: Optional non-negative maximum amount.
        search: Optional description search string.
    """

    account_id: uuid.UUID | None
    source_account_id: uuid.UUID | None
    destination_account_id: uuid.UUID | None
    category_id: uuid.UUID | None
    transaction_kind: TransactionKind | None
    exclude_transfer: bool
    status: TransactionStatus | None
    settlement_status: SettlementStatus | None
    start_date: date | None
    end_date: date | None
    min_amount: float | None
    max_amount: float | None
    search: str | None


class TransactionListQuery(BaseModel):
    """Bundled query parameters for ``GET /transactions``."""

    account_id: uuid.UUID | None = Field(default=None, description="Filter by primary account (from or to)")
    source_account_id: uuid.UUID | None = Field(default=None, description="Filter by source (from) account")
    destination_account_id: uuid.UUID | None = Field(default=None, description="Filter by destination (to) account")
    category_id: uuid.UUID | None = Field(default=None, description="Filter by category")
    transaction_type: str | None = Field(default=None, description="Filter by income/expense/transfer")
    exclude_transfer: bool | None = Field(default=None, description="Exclude transfer rows when true")
    status: str | None = Field(default=None, description="Filter by pending/completed/cancelled")
    settlement_status: str | None = Field(default=None, description="Filter by settled/in_transit")
    start_date: date | None = Field(default=None, description="Filter by start date")
    end_date: date | None = Field(default=None, description="Filter by end date")
    min_amount: float | None = Field(default=None, description="Minimum amount filter", ge=0)
    max_amount: float | None = Field(default=None, description="Maximum amount filter", ge=0)
    search: str | None = Field(
        default=None,
        description="Search in description",
        max_length=MAX_SEARCH_LENGTH,
    )

    def service_kwargs(self) -> TransactionListServiceKwargs:
        """Map API query parameters to ``TransactionsService.list_transactions`` kwargs."""
        transaction_kind = parse_transaction_kind(self.transaction_type) if self.transaction_type else None
        if self.exclude_transfer is not None:
            resolved_exclude_transfer = self.exclude_transfer
        else:
            resolved_exclude_transfer = (
                self.transaction_type is None and self.source_account_id is None and self.destination_account_id is None
            )
        return TransactionListServiceKwargs(
            account_id=self.account_id,
            source_account_id=self.source_account_id,
            destination_account_id=self.destination_account_id,
            category_id=self.category_id,
            transaction_kind=transaction_kind,
            exclude_transfer=resolved_exclude_transfer,
            status=parse_transaction_status(self.status) if self.status else None,
            settlement_status=parse_settlement_status(self.settlement_status) if self.settlement_status else None,
            start_date=self.start_date,
            end_date=self.end_date,
            min_amount=self.min_amount,
            max_amount=self.max_amount,
            search=self.search,
        )


def get_transaction_list_query(  # pylint: disable=too-many-arguments
    *,
    account_id: Annotated[uuid.UUID | None, Query(description="Filter by primary account (from or to)")] = None,
    source_account_id: Annotated[uuid.UUID | None, Query(description="Filter by source account")] = None,
    destination_account_id: Annotated[uuid.UUID | None, Query(description="Filter by destination account")] = None,
    category_id: Annotated[uuid.UUID | None, Query(description="Filter by category")] = None,
    transaction_type: Annotated[str | None, Query(description="Filter by income/expense/transfer")] = None,
    exclude_transfer: Annotated[bool | None, Query(description="Exclude transfer rows when true")] = None,
    status: Annotated[str | None, Query(description="Filter by pending/completed/cancelled")] = None,
    settlement_status: Annotated[str | None, Query(description="Filter by settled/in_transit")] = None,
    start_date: Annotated[date | None, Query(description="Filter by start date")] = None,
    end_date: Annotated[date | None, Query(description="Filter by end date")] = None,
    min_amount: Annotated[float | None, Query(description="Minimum amount filter", ge=0)] = None,
    max_amount: Annotated[float | None, Query(description="Maximum amount filter", ge=0)] = None,
    search: Annotated[
        str | None,
        Query(description="Search in description", max_length=MAX_SEARCH_LENGTH),
    ] = None,
) -> TransactionListQuery:
    """Collect ``GET /transactions`` query parameters for FastAPI dependency injection."""
    return TransactionListQuery(
        account_id=account_id,
        source_account_id=source_account_id,
        destination_account_id=destination_account_id,
        category_id=category_id,
        transaction_type=transaction_type,
        exclude_transfer=exclude_transfer,
        status=status,
        settlement_status=settlement_status,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        search=search,
    )


class ReportSpendingServiceKwargs(TypedDict):
    """Keyword arguments accepted by ``ReportService.spending``.

    Attributes:
        start_date: Inclusive UTC start of the report window.
        end_date: Inclusive UTC end of the report window.
        group_by: Aggregation dimension (``category`` or ``account``).
        account_id: Optional account scope filter.
    """

    start_date: datetime
    end_date: datetime
    group_by: Literal["category", "account"]
    account_id: uuid.UUID | None


class ReportCashFlowServiceKwargs(TypedDict):
    """Keyword arguments accepted by ``ReportService.cash_flow``.

    Attributes:
        start_date: Inclusive UTC start of the report window.
        end_date: Inclusive UTC end of the report window.
        account_id: Optional account scope filter.
        refresh_balances: When ``True``, refresh balance materialized views first.
    """

    start_date: datetime
    end_date: datetime
    account_id: uuid.UUID | None
    refresh_balances: bool


class ReportTrendsServiceKwargs(TypedDict):
    """Keyword arguments accepted by ``ReportService.trends``.

    Attributes:
        start_date: Inclusive UTC start of the analysis window.
        end_date: Inclusive UTC end of the analysis window.
        period: Bucket size (``daily``, ``weekly``, ``monthly``, or ``yearly``).
        account_id: Optional account scope filter.
        category_id: Optional category scope filter.
    """

    start_date: datetime
    end_date: datetime
    period: Literal["daily", "weekly", "monthly", "yearly"]
    account_id: uuid.UUID | None
    category_id: uuid.UUID | None


class ReportExportServiceKwargs(TypedDict):
    """Keyword arguments accepted by ``ReportService.export``.

    Attributes:
        report_type: Which report payload to serialize.
        export_format: Wire format (``csv`` or ``json`` only at the service layer).
        start_date: Inclusive UTC start of the report window.
        end_date: Inclusive UTC end of the report window.
        account_id: Optional account scope filter.
        group_by: Spending aggregation when ``report_type`` is ``spending``.
        period: Trends bucket when ``report_type`` is ``trends``.
    """

    report_type: Literal["spending", "cash-flow", "trends"]
    export_format: Literal["csv", "json"]
    start_date: datetime
    end_date: datetime
    account_id: uuid.UUID | None
    group_by: Literal["category", "account"]
    period: Literal["daily", "weekly", "monthly", "yearly"]


class ReportSpendingQuery(BaseModel):
    """Bundled query parameters for ``GET /reports/spending``.

    Validates that the date window is ordered and ``group_by`` is allowlisted,
    then expands dates to inclusive UTC datetimes for the service.

    Attributes:
        start_date: Report window start (calendar date).
        end_date: Report window end (calendar date).
        group_by: Aggregation dimension; default ``category``.
        account_id: Optional account filter.
    """

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
        """Map API query parameters to ``ReportService.spending`` kwargs.

        Returns:
            Typed keyword arguments with UTC-bounded ``start_date`` / ``end_date``.

        Note:
            Call after model validation; invalid windows or ``group_by`` values
            raise ``ValueError`` during construction, not here.
        """
        return ReportSpendingServiceKwargs(
            start_date=date_to_start_datetime(self.start_date),
            end_date=date_to_end_datetime(self.end_date),
            group_by=self.group_by,  # type: ignore[typeddict-item]
            account_id=self.account_id,
        )


class ReportCashFlowQuery(BaseModel):
    """Bundled query parameters for ``GET /reports/cash-flow``.

    Validates window ordering. ``refresh_balances`` defaults to ``False`` so
    cash-flow reads are not an authenticated DoS vector; pass ``true`` for G9 freshness.

    Attributes:
        start_date: Report window start (calendar date).
        end_date: Report window end (calendar date).
        account_id: Optional account filter.
        refresh_balances: Whether to refresh balance MVs before the query.
    """

    start_date: date = Field(description="Report start date")
    end_date: date = Field(description="Report end date")
    account_id: uuid.UUID | None = Field(default=None, description="Optional account filter")
    refresh_balances: bool = Field(default=False, description="Refresh account_balances MVs before query (G9)")

    @model_validator(mode="after")
    def _validate_window(self) -> ReportCashFlowQuery:
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self

    def service_kwargs(self) -> ReportCashFlowServiceKwargs:
        """Map API query parameters to ``ReportService.cash_flow`` kwargs.

        Returns:
            Typed keyword arguments with UTC-bounded dates and refresh flag.

        Note:
            Call after model validation; an inverted date window raises
            ``ValueError`` during construction, not here.
        """
        return ReportCashFlowServiceKwargs(
            start_date=date_to_start_datetime(self.start_date),
            end_date=date_to_end_datetime(self.end_date),
            account_id=self.account_id,
            refresh_balances=self.refresh_balances,
        )


class ReportTrendsQuery(BaseModel):
    """Bundled query parameters for ``GET /reports/trends``.

    Resolves the analysis window from explicit dates or from ``months`` ending at
    ``end_date`` (default today). Mutates ``start_date`` / ``end_date`` on the
    model during validation so later ``service_kwargs()`` always sees concrete dates.

    Attributes:
        months: Lookback length in months when dates are omitted (1–120; default 6).
        period: Series bucket size (``daily`` / ``weekly`` / ``monthly`` / ``yearly``).
        start_date: Explicit analysis start, or resolved during validation.
        end_date: Explicit analysis end, or resolved during validation.
        category_id: Optional category filter.
        account_id: Optional account filter.
    """

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
        explicit_window = self.start_date is not None and self.end_date is not None
        resolved_end = self.end_date or date.today()
        resolved_start = self.start_date or (resolved_end - timedelta(days=30 * self.months))
        if resolved_start > resolved_end:
            raise ValueError("start_date must be on or before end_date")
        # Window length is enforced in get_report_trends_query (settings-backed).
        del explicit_window
        self.start_date = resolved_start
        self.end_date = resolved_end
        return self

    def service_kwargs(self) -> ReportTrendsServiceKwargs:
        """Map API query parameters to ``ReportService.trends`` kwargs.

        Returns:
            Typed keyword arguments with UTC-bounded dates and allowlisted period.

        Raises:
            ValueError: If validation did not resolve ``start_date`` and ``end_date``
                (defensive; normal construction always resolves them).
        """
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
    """Bundled query parameters for ``GET /reports/export``.

    Validates window order, report type, group/period allowlists, and export
    format. Deferred formats (``xlsx``, ``pdf``) pass validation so the router can
    return HTTP 501; ``service_kwargs()`` refuses them.

    Attributes:
        report_type: Report to export (``spending``, ``cash-flow``, or ``trends``).
        export_format: Wire format (``csv`` / ``json``; ``xlsx`` / ``pdf`` deferred).
        start_date: Report window start (calendar date).
        end_date: Report window end (calendar date).
        account_id: Optional account filter.
        group_by: Spending ``group_by`` when ``report_type`` is ``spending``.
        period: Trends period when ``report_type`` is ``trends``.
    """

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
        """Return whether the requested export format is deferred (HTTP 501).

        Returns:
            ``True`` when ``export_format`` is in ``DEFERRED_EXPORT_FORMATS``.
        """
        return self.export_format in DEFERRED_EXPORT_FORMATS

    def service_kwargs(self) -> ReportExportServiceKwargs:
        """Map API query parameters to ``ReportService.export`` kwargs.

        Returns:
            Typed keyword arguments for an implemented export format.

        Raises:
            ValueError: When ``export_format`` is deferred (``xlsx`` / ``pdf``).
        """
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
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReportSpendingQuery:
    """Collect ``GET /reports/spending`` query parameters for FastAPI injection.

    Args:
        start_date: Report start date (required).
        end_date: Report end date (required).
        group_by: Aggregation dimension; default ``category``.
        account_id: Optional account filter.
        settings: Application settings (report window max days).

    Returns:
        Populated ``ReportSpendingQuery`` for the route handler.

    Raises:
        ValueError: When the date window is inverted, too large, or ``group_by`` is
            not allowlisted.
    """
    query = ReportSpendingQuery(
        start_date=start_date,
        end_date=end_date,
        group_by=group_by,
        account_id=account_id,
    )
    _enforce_report_window(query.start_date, query.end_date, settings)
    return query


def get_report_cash_flow_query(  # pylint: disable=too-many-arguments
    request: Request,
    *,
    start_date: Annotated[date, Query(description="Report start date")],
    end_date: Annotated[date, Query(description="Report end date")],
    account_id: Annotated[uuid.UUID | None, Query(description="Optional account filter")] = None,
    refresh_balances: Annotated[
        bool | None,
        Query(description="Refresh balance MVs before query (omit to use server default)"),
    ] = None,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReportCashFlowQuery:
    """Collect ``GET /reports/cash-flow`` query parameters for FastAPI injection.

    When ``refresh_balances`` is omitted, uses the secure default ``false`` unless
    ``API_COMPAT_LEGACY_REFRESH_BALANCES_DEFAULT_TRUE`` is enabled (temporary).

    Args:
        request: Incoming request (compat deprecation headers via ``request.state``).
        start_date: Report start date (required).
        end_date: Report end date (required).
        account_id: Optional account filter.
        refresh_balances: Optional explicit refresh flag.
        settings: Application settings.

    Returns:
        Populated ``ReportCashFlowQuery`` for the route handler.

    Raises:
        ValueError: When the date window is inverted or too large.
    """
    omitted = refresh_balances is None
    resolved_refresh = cash_flow_refresh_balances_default(settings) if omitted else bool(refresh_balances)
    if omitted and settings.API_COMPAT_LEGACY_REFRESH_BALANCES_DEFAULT_TRUE:
        extra = getattr(request.state, "extra_response_headers", None)
        if not isinstance(extra, dict):
            extra = {}
        extra[HEADER_DEPRECATION] = "true"
        extra[HEADER_SUNSET] = COMPAT_SUNSET_DATE
        request.state.extra_response_headers = extra

    query = ReportCashFlowQuery(
        start_date=start_date,
        end_date=end_date,
        account_id=account_id,
        refresh_balances=resolved_refresh,
    )
    _enforce_report_window(query.start_date, query.end_date, settings)
    return query


def get_report_trends_query(  # pylint: disable=too-many-arguments
    *,
    months: Annotated[int, Query(description="Number of months to analyze", ge=1, le=120)] = 6,
    period: Annotated[str, Query(description="Series bucket size")] = "monthly",
    start_date: Annotated[date | None, Query(description="Explicit analysis start date")] = None,
    end_date: Annotated[date | None, Query(description="Explicit analysis end date")] = None,
    category_id: Annotated[uuid.UUID | None, Query(description="Optional category filter")] = None,
    account_id: Annotated[uuid.UUID | None, Query(description="Optional account filter")] = None,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReportTrendsQuery:
    """Collect ``GET /reports/trends`` query parameters for FastAPI injection.

    Args:
        months: Lookback months when dates are omitted (1–120; default 6).
        period: Series bucket size (default ``monthly``).
        start_date: Optional explicit analysis start.
        end_date: Optional explicit analysis end.
        category_id: Optional category filter.
        account_id: Optional account filter.
        settings: Application settings (explicit window max days).

    Returns:
        Populated ``ReportTrendsQuery`` with resolved window after validation.

    Raises:
        ValueError: When ``period`` is not allowlisted, the resolved window is
            inverted, or the resolved window (including ``months`` lookback)
            exceeds the configured max days.
    """
    query = ReportTrendsQuery(
        months=months,
        period=period,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        account_id=account_id,
    )
    if query.start_date is not None and query.end_date is not None:
        _enforce_report_window(query.start_date, query.end_date, settings)
    return query


class UpcomingDuesServiceKwargs(TypedDict):
    """Keyword arguments for ``TransactionTemplatesService.list_upcoming_dues``."""

    as_of: date
    window_days: int
    include_paid: bool


class UpcomingDuesQuery(BaseModel):
    """Bundled query parameters for ``GET /transaction-templates/upcoming-dues``.

    Attributes:
        as_of: Window anchor date (defaults to UTC today when omitted at the
            dependency layer).
        window_days: Inclusive days after ``as_of`` to consider (default 14).
        include_paid: When False, omit dues that already have a linked posting.
    """

    as_of: date
    window_days: int = Field(default=14, ge=0)
    include_paid: bool = True

    def service_kwargs(self) -> UpcomingDuesServiceKwargs:
        """Map query fields to ``list_upcoming_dues`` kwargs."""
        return {
            "as_of": self.as_of,
            "window_days": self.window_days,
            "include_paid": self.include_paid,
        }


def get_upcoming_dues_query(
    *,
    as_of: Annotated[date | None, Query(description="Window anchor date (UTC today when omitted)")] = None,
    window_days: Annotated[int, Query(description="Inclusive days after as_of", ge=0)] = 14,
    include_paid: Annotated[bool, Query(description="Include dues already marked paid")] = True,
) -> UpcomingDuesQuery:
    """Collect upcoming-dues query parameters for FastAPI injection.

    Args:
        as_of: Optional anchor date; defaults to the current UTC calendar day.
        window_days: Inclusive days after ``as_of`` (must be ``>= 0``).
        include_paid: Whether paid dues remain in the response.

    Returns:
        Populated ``UpcomingDuesQuery``.
    """
    anchor = as_of if as_of is not None else datetime.now(timezone.utc).date()
    return UpcomingDuesQuery(as_of=anchor, window_days=window_days, include_paid=include_paid)


def get_report_export_query(  # pylint: disable=too-many-arguments
    *,
    report_type: Annotated[str, Query(description="Report to export")],
    export_format: Annotated[str, Query(alias="format", description="Export format (csv or json)")],
    start_date: Annotated[date, Query(description="Report start date")],
    end_date: Annotated[date, Query(description="Report end date")],
    account_id: Annotated[uuid.UUID | None, Query(description="Optional account filter")] = None,
    group_by: Annotated[str, Query(description="Spending group_by")] = "category",
    period: Annotated[str, Query(description="Trends period")] = "monthly",
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReportExportQuery:
    """Collect ``GET /reports/export`` query parameters for FastAPI injection.

    The OpenAPI query name for ``export_format`` is ``format`` (alias).

    Args:
        report_type: Report to export (``spending``, ``cash-flow``, or ``trends``).
        export_format: Export format from the ``format`` query parameter.
        start_date: Report start date (required).
        end_date: Report end date (required).
        account_id: Optional account filter.
        group_by: Spending aggregation when exporting spending.
        period: Trends bucket when exporting trends.
        settings: Application settings (report window max days).

    Returns:
        Populated ``ReportExportQuery``. Deferred formats remain constructible so
        the router can return HTTP 501.

    Raises:
        ValueError: When the window, report type, or non-deferred format fields
            fail allowlist validation.
    """
    query = ReportExportQuery(
        report_type=report_type,
        export_format=export_format,
        start_date=start_date,
        end_date=end_date,
        account_id=account_id,
        group_by=group_by,
        period=period,
    )
    _enforce_report_window(query.start_date, query.end_date, settings)
    return query


class ReportOperatingCashflowServiceKwargs(TypedDict):
    """Keyword arguments accepted by ``ReportService.operating_cashflow``."""

    start_date: datetime
    end_date: datetime
    currency: str | None
    account_id: uuid.UUID | None
    include_monthly_series: bool


class ReportOperatingCashflowQuery(BaseModel):
    """Bundled query parameters for ``GET /reports/operating-cashflow``."""

    start_date: date = Field(description="Report start date")
    end_date: date = Field(description="Report end date")
    currency: str | None = Field(default=None, min_length=3, max_length=3, description="ISO currency filter")
    account_id: uuid.UUID | None = Field(default=None, description="Optional account filter")
    include_monthly_series: bool = Field(default=False, description="Include month-by-month series")

    @model_validator(mode="after")
    def _validate_window(self) -> ReportOperatingCashflowQuery:
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        if self.currency is not None:
            self.currency = self.currency.strip().upper()
        return self

    def service_kwargs(self) -> ReportOperatingCashflowServiceKwargs:
        """Map API query parameters to ``ReportService.operating_cashflow`` kwargs."""
        return ReportOperatingCashflowServiceKwargs(
            start_date=date_to_start_datetime(self.start_date),
            end_date=date_to_end_datetime(self.end_date),
            currency=self.currency,
            account_id=self.account_id,
            include_monthly_series=self.include_monthly_series,
        )


def get_report_operating_cashflow_query(  # pylint: disable=too-many-arguments
    *,
    start_date: Annotated[date, Query(description="Report start date")],
    end_date: Annotated[date, Query(description="Report end date")],
    currency: Annotated[str | None, Query(description="Optional 3-letter currency filter")] = None,
    account_id: Annotated[uuid.UUID | None, Query(description="Optional account filter")] = None,
    include_monthly_series: Annotated[bool, Query(description="Include monthly breakdown")] = False,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReportOperatingCashflowQuery:
    """Collect ``GET /reports/operating-cashflow`` query parameters for FastAPI injection."""
    query = ReportOperatingCashflowQuery(
        start_date=start_date,
        end_date=end_date,
        currency=currency,
        account_id=account_id,
        include_monthly_series=include_monthly_series,
    )
    _enforce_report_window(query.start_date, query.end_date, settings)
    return query


class ReportPlannedVsActualServiceKwargs(TypedDict):
    """Keyword arguments accepted by ``ReportService.planned_vs_actual``."""

    start_date: datetime
    end_date: datetime
    currency: str | None
    account_id: uuid.UUID | None
    cashflow_bucket: CashflowBucket | None


class ReportPlannedVsActualQuery(BaseModel):
    """Bundled query parameters for ``GET /reports/planned-vs-actual``."""

    start_date: date = Field(description="Report start date")
    end_date: date = Field(description="Report end date")
    currency: str | None = Field(default=None, min_length=3, max_length=3, description="ISO currency filter")
    account_id: uuid.UUID | None = Field(default=None, description="Optional account filter")
    cashflow_bucket: str | None = Field(default=None, description="Optional cashflow bucket slug filter")
    _parsed_bucket: CashflowBucket | None = None

    @model_validator(mode="after")
    def _validate_window(self) -> ReportPlannedVsActualQuery:
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        if self.currency is not None:
            self.currency = self.currency.strip().upper()
        self._parsed_bucket = parse_cashflow_bucket(self.cashflow_bucket) if self.cashflow_bucket is not None else None
        if self._parsed_bucket is not None:
            self.cashflow_bucket = self._parsed_bucket.value.lower()
        return self

    def service_kwargs(self) -> ReportPlannedVsActualServiceKwargs:
        """Map API query parameters to ``ReportService.planned_vs_actual`` kwargs."""
        return ReportPlannedVsActualServiceKwargs(
            start_date=date_to_start_datetime(self.start_date),
            end_date=date_to_end_datetime(self.end_date),
            currency=self.currency,
            account_id=self.account_id,
            cashflow_bucket=self._parsed_bucket,
        )


def get_report_planned_vs_actual_query(  # pylint: disable=too-many-arguments
    *,
    start_date: Annotated[date, Query(description="Report start date")],
    end_date: Annotated[date, Query(description="Report end date")],
    currency: Annotated[str | None, Query(description="Optional 3-letter currency filter")] = None,
    account_id: Annotated[uuid.UUID | None, Query(description="Optional account filter")] = None,
    cashflow_bucket: Annotated[str | None, Query(description="Optional cashflow bucket filter")] = None,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReportPlannedVsActualQuery:
    """Collect ``GET /reports/planned-vs-actual`` query parameters for FastAPI injection."""
    query = ReportPlannedVsActualQuery(
        start_date=start_date,
        end_date=end_date,
        currency=currency,
        account_id=account_id,
        cashflow_bucket=cashflow_bucket,
    )
    _enforce_report_window(query.start_date, query.end_date, settings)
    return query


class ReportDebtPaydownServiceKwargs(TypedDict):
    """Keyword arguments accepted by ``ReportService.debt_paydown``."""

    currency: str | None
    include_excluded: bool
    target_liquidity_months: float


class ReportDebtPaydownQuery(BaseModel):
    """Bundled query parameters for ``GET /reports/debt-paydown``."""

    currency: str | None = Field(default=None, min_length=3, max_length=3, description="ISO currency filter")
    include_excluded: bool = Field(default=False, description="Include excluded/paid-off liabilities summary")
    target_liquidity_months: float = Field(default=4.0, ge=0, le=24, description="Target liquid runway months")

    @model_validator(mode="after")
    def _normalize(self) -> ReportDebtPaydownQuery:
        if self.currency is not None:
            self.currency = self.currency.strip().upper()
        return self

    def service_kwargs(self) -> ReportDebtPaydownServiceKwargs:
        """Map API query parameters to ``ReportService.debt_paydown`` kwargs."""
        return ReportDebtPaydownServiceKwargs(
            currency=self.currency,
            include_excluded=self.include_excluded,
            target_liquidity_months=self.target_liquidity_months,
        )


def get_report_debt_paydown_query(
    *,
    currency: Annotated[str | None, Query(description="Optional 3-letter currency filter")] = None,
    include_excluded: Annotated[bool, Query(description="Include excluded liabilities summary")] = False,
    target_liquidity_months: Annotated[float, Query(description="Target liquid cash runway months", ge=0, le=24)] = 4.0,
) -> ReportDebtPaydownQuery:
    """Collect ``GET /reports/debt-paydown`` query parameters for FastAPI injection."""
    return ReportDebtPaydownQuery(
        currency=currency,
        include_excluded=include_excluded,
        target_liquidity_months=target_liquidity_months,
    )


class ReportFinancialHealthServiceKwargs(TypedDict):
    """Keyword arguments accepted by ``ReportService.financial_health``."""

    currency: str | None
    target_liquidity_months: float


class ReportFinancialHealthQuery(BaseModel):
    """Bundled query parameters for ``GET /reports/financial-health``."""

    currency: str | None = Field(default=None, min_length=3, max_length=3, description="ISO currency filter")
    target_liquidity_months: float = Field(default=4.0, ge=0, le=24, description="Target liquid runway months")

    @model_validator(mode="after")
    def _normalize(self) -> ReportFinancialHealthQuery:
        if self.currency is not None:
            self.currency = self.currency.strip().upper()
        return self

    def service_kwargs(self) -> ReportFinancialHealthServiceKwargs:
        """Map API query parameters to ``ReportService.financial_health`` kwargs."""
        return ReportFinancialHealthServiceKwargs(
            currency=self.currency,
            target_liquidity_months=self.target_liquidity_months,
        )


def get_report_financial_health_query(
    *,
    currency: Annotated[str | None, Query(description="Optional 3-letter currency filter")] = None,
    target_liquidity_months: Annotated[float, Query(description="Target liquid cash runway months", ge=0, le=24)] = 4.0,
) -> ReportFinancialHealthQuery:
    """Collect ``GET /reports/financial-health`` query parameters for FastAPI injection."""
    return ReportFinancialHealthQuery(
        currency=currency,
        target_liquidity_months=target_liquidity_months,
    )
