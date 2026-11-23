"""Report read-model routes — PPT-038 (FR-12).

Exposes **tenant-scoped** aggregations under ``/reports``. Every route resolves
the JWT subject via ``get_current_owner`` and passes ``owner=`` into
:class:`~papita_txnsmodel.services.reports.ReportService`. Business logic stays
in the model layer; this router maps query params and response envelopes only.
Optional ``account_id`` filters are validated as owned by that tenant inside
``ReportService`` before aggregation.

Routes:
    ``GET /reports/spending`` — expense/income totals and breakdown.
    ``GET /reports/cash-flow`` — inflows/outflows plus portfolio closing balance (G9).
    ``GET /reports/trends`` — time-series income/expense buckets.
    ``GET /reports/export`` — CSV/JSON export of the above; xlsx/pdf → 501.
    ``GET /reports/budget-performance`` — deferred 501 (FR-09 / v4.1).
    ``GET /reports/operating-cashflow`` — Operating Free Cashflow waterfall.
    ``GET /reports/planned-vs-actual`` — Planned vs. Actual template variance.
    ``GET /reports/debt-paydown`` — active liability interest-drag ranking.
    ``POST /reports/debt-paydown/simulate`` — what-if avalanche/snowball simulator.

Tenant scoping:
    All handlers depend on ``get_current_owner``. Ledger and balance reads never
    run without an authenticated owner, including deferred stubs.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated, Any, TypeVar

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis import Redis

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.cache import (
    CacheNamespace,
    get_versioned_cached_json,
    set_versioned_cached_json,
    ttl_for_namespace,
)
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.rate_limit import enforce_tenant_api_rate_limit
from papita_txnsapi.dependencies.redis import get_optional_redis
from papita_txnsapi.dependencies.services import get_report_service
from papita_txnsapi.schemas.common import DeferredResponse
from papita_txnsapi.schemas.query_params import (
    ReportCashFlowQuery,
    ReportDebtPaydownQuery,
    ReportExportQuery,
    ReportFinancialHealthQuery,
    ReportOperatingCashflowQuery,
    ReportPlannedVsActualQuery,
    ReportSpendingQuery,
    ReportTrendsQuery,
    get_report_cash_flow_query,
    get_report_debt_paydown_query,
    get_report_export_query,
    get_report_financial_health_query,
    get_report_operating_cashflow_query,
    get_report_planned_vs_actual_query,
    get_report_spending_query,
    get_report_trends_query,
)
from papita_txnsapi.schemas.reports import (
    CashFlowReportResponse,
    DebtPaydownReportResponse,
    DebtPaydownSimulationRequest,
    DebtPaydownSimulationResponse,
    FinancialHealthReportResponse,
    OperatingCashflowReportResponse,
    PlannedVsActualReportResponse,
    SpendingReportResponse,
    TrendsReportResponse,
)
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.reports import ReportService

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
    dependencies=[Depends(enforce_tenant_api_rate_limit)],
)

_DEFERRED_EXPORT = DeferredResponse(deferred_reason="Export formats xlsx/pdf deferred — use csv or json")


ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


def _report_cache_params(
    route: str,
    filters: (
        ReportSpendingQuery
        | ReportCashFlowQuery
        | ReportTrendsQuery
        | ReportOperatingCashflowQuery
        | ReportPlannedVsActualQuery
        | ReportDebtPaydownQuery
        | ReportFinancialHealthQuery
    ),
) -> dict:
    """Build a JSON-safe cache param map from report query models."""
    return {"route": route, **filters.model_dump(mode="json")}


def _cached_report_call(  # pylint: disable=too-many-arguments
    *,
    owner_id: uuid.UUID | None,
    cache_key: str,
    cache_params: dict[str, Any],
    settings: Settings,
    redis: Redis | None,
    response: Response,
    response_type: type[ResponseModelT],
    builder: Callable[[], ResponseModelT],
) -> ResponseModelT:
    """Serve a tenant-scoped report response through Redis versioned caching."""
    if owner_id is not None:
        cached, cache_status, cache_version = get_versioned_cached_json(
            redis, owner_id, CacheNamespace.REPORTS, cache_key, cache_params
        )
        response.headers["X-Cache"] = cache_status
        if cached is not None:
            return response_type.model_validate(cached)
    else:
        response.headers["X-Cache"] = "BYPASS"
        cache_version = 0

    result = builder()
    if owner_id is not None:
        set_versioned_cached_json(
            redis,
            owner_id,
            CacheNamespace.REPORTS,
            cache_key,
            cache_params,
            value=result.model_dump(mode="json"),
            ttl_seconds=ttl_for_namespace(settings, CacheNamespace.REPORTS),
            version=cache_version,
        )
    return result


@router.get("/spending", response_model=SpendingReportResponse)
def get_spending_report(  # pylint: disable=too-many-positional-arguments
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    filters: Annotated[ReportSpendingQuery, Depends(get_report_spending_query)],
    settings: Annotated[Settings, Depends(get_settings)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    response: Response,
) -> SpendingReportResponse:
    """Return spending and income totals for the authenticated tenant only.

    Aggregates COMPLETED EXPENSE rows (plus separate INCOME totals) via
    ``ReportService.spending``. Response shaping and stub enrichment fields are
    applied in ``SpendingReportResponse.from_service``. Cached in Redis when enabled.

    Args:
        owner: Authenticated tenant from JWT; required for all ledger reads.
        report_service: Injected report aggregation service.
        filters: Date window, optional ``account_id``, and ``group_by`` parameters.
        settings: Application settings (cache TTL).
        redis: Optional Redis client when ``REDIS_ENABLED``.
        response: FastAPI response used to set ``X-Cache`` status.

    Returns:
        SpendingReportResponse mapped from the lean service payload.

    Raises:
        HTTPException: 401 without JWT; 404 when ``account_id`` is not owned by
            the tenant; 400 when date/group validation fails in query models.
    """
    cache_params = _report_cache_params("spending", filters)
    owner_id = owner.id
    if owner_id is not None:
        cached, cache_status, cache_version = get_versioned_cached_json(
            redis, owner_id, CacheNamespace.REPORTS, "reports:spending", cache_params
        )
        response.headers["X-Cache"] = cache_status
        if cached is not None:
            return SpendingReportResponse.model_validate(cached)
    else:
        response.headers["X-Cache"] = "BYPASS"
        cache_version = 0

    payload = report_service.spending(owner=owner, **filters.service_kwargs())
    result = SpendingReportResponse.from_service(
        payload,
        start_date=filters.start_date,
        end_date=filters.end_date,
    )
    if owner_id is not None:
        set_versioned_cached_json(
            redis,
            owner_id,
            CacheNamespace.REPORTS,
            "reports:spending",
            cache_params,
            value=result.model_dump(mode="json"),
            ttl_seconds=ttl_for_namespace(settings, CacheNamespace.REPORTS),
            version=cache_version,
        )
    return result


@router.get("/cash-flow", response_model=CashFlowReportResponse)
def get_cash_flow_report(  # pylint: disable=too-many-positional-arguments
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    filters: Annotated[ReportCashFlowQuery, Depends(get_report_cash_flow_query)],
    settings: Annotated[Settings, Depends(get_settings)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    response: Response,
) -> CashFlowReportResponse:
    """Return cash-flow summary for the authenticated tenant.

    Inflows/outflows include TRANSFER legs. Balance freshness uses
    ``refresh_balance_materialized_views`` when ``refresh_balances`` is true
    (defaults to false to avoid authenticated DoS; pass ``true`` for G9 freshness).
    ``closing_balance`` maps from service ``portfolio_total``; opening/by-account
    fields may be stubbed in MVP. Cached in Redis when enabled.

    Args:
        owner: Authenticated tenant from JWT.
        report_service: Injected report aggregation service.
        filters: Date window, optional ``account_id``, and refresh flag.
        settings: Application settings (cache TTL).
        redis: Optional Redis client when ``REDIS_ENABLED``.
        response: FastAPI response used to set ``X-Cache`` status.

    Returns:
        CashFlowReportResponse for the tenant (and optional account filter).

    Raises:
        HTTPException: 401 without JWT; 400 when tenant account validation fails.
    """
    cache_params = _report_cache_params("cash-flow", filters)
    owner_id = owner.id
    if owner_id is not None:
        cached, cache_status, cache_version = get_versioned_cached_json(
            redis, owner_id, CacheNamespace.REPORTS, "reports:cash-flow", cache_params
        )
        response.headers["X-Cache"] = cache_status
        if cached is not None:
            return CashFlowReportResponse.model_validate(cached)
    else:
        response.headers["X-Cache"] = "BYPASS"
        cache_version = 0

    payload = report_service.cash_flow(owner=owner, **filters.service_kwargs())
    result = CashFlowReportResponse.from_service(
        payload,
        start_date=filters.start_date,
        end_date=filters.end_date,
    )
    if owner_id is not None:
        set_versioned_cached_json(
            redis,
            owner_id,
            CacheNamespace.REPORTS,
            "reports:cash-flow",
            cache_params,
            value=result.model_dump(mode="json"),
            ttl_seconds=ttl_for_namespace(settings, CacheNamespace.REPORTS),
            version=cache_version,
        )
    return result


@router.get("/trends", response_model=TrendsReportResponse)
def get_trends_report(  # pylint: disable=too-many-positional-arguments
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    filters: Annotated[ReportTrendsQuery, Depends(get_report_trends_query)],
    settings: Annotated[Settings, Depends(get_settings)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    response: Response,
) -> TrendsReportResponse:
    """Return income/expense time-series trends for the authenticated tenant only.

    ``months`` (or explicit dates) define the analysis window; series buckets use
    the requested ``period``. Category insights remain stubbed empty in MVP.
    Cached in Redis when enabled.

    Args:
        owner: Authenticated tenant from JWT.
        report_service: Injected report aggregation service.
        filters: Period, date window (or months), optional account/category filters.
        settings: Application settings (cache TTL).
        redis: Optional Redis client when ``REDIS_ENABLED``.
        response: FastAPI response used to set ``X-Cache`` status.

    Returns:
        TrendsReportResponse with ``monthly_trends`` derived from the service series.

    Raises:
        HTTPException: 401 without JWT; 400 when filters or ownership checks fail.
    """
    cache_params = _report_cache_params("trends", filters)
    owner_id = owner.id
    if owner_id is not None:
        cached, cache_status, cache_version = get_versioned_cached_json(
            redis, owner_id, CacheNamespace.REPORTS, "reports:trends", cache_params
        )
        response.headers["X-Cache"] = cache_status
        if cached is not None:
            return TrendsReportResponse.model_validate(cached)
    else:
        response.headers["X-Cache"] = "BYPASS"
        cache_version = 0

    payload = report_service.trends(owner=owner, **filters.service_kwargs())
    assert filters.start_date is not None and filters.end_date is not None
    result = TrendsReportResponse.from_service(
        payload,
        start_date=filters.start_date,
        end_date=filters.end_date,
    )
    if owner_id is not None:
        set_versioned_cached_json(
            redis,
            owner_id,
            CacheNamespace.REPORTS,
            "reports:trends",
            cache_params,
            value=result.model_dump(mode="json"),
            ttl_seconds=ttl_for_namespace(settings, CacheNamespace.REPORTS),
            version=cache_version,
        )
    return result


@router.get("/export")
def export_report(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    filters: Annotated[ReportExportQuery, Depends(get_report_export_query)],
) -> Any:
    """Export a tenant-scoped report as CSV or JSON; deferred formats return 501.

    Delegates to ``ReportService.export`` for spending, cash-flow, or trends.
    ``xlsx`` and ``pdf`` return HTTP 501 with ``DeferredResponse`` and do not
    call the service. Export is not cached (streaming / large payloads).

    Args:
        owner: Authenticated tenant from JWT.
        report_service: Injected report aggregation service.
        filters: Report type, format, date window, and optional filters.

    Returns:
        JSONResponse for JSON payloads, raw CSV ``Response`` for ``format=csv``,
        or 501 JSON for deferred export formats.

    Raises:
        HTTPException: 401 without JWT; 400 when query validation or ownership fails.
    """
    if filters.is_deferred_format:
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content=_DEFERRED_EXPORT.model_dump(),
        )

    payload = report_service.export(owner=owner, **filters.service_kwargs())
    if filters.export_format == "json":
        return JSONResponse(content=payload)

    filename = f"{filters.report_type}-report.csv"
    return Response(
        content=payload if isinstance(payload, str) else str(payload),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/operating-cashflow", response_model=OperatingCashflowReportResponse)
def get_operating_cashflow_report(  # pylint: disable=too-many-positional-arguments
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    filters: Annotated[ReportOperatingCashflowQuery, Depends(get_report_operating_cashflow_query)],
    settings: Annotated[Settings, Depends(get_settings)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    response: Response,
) -> OperatingCashflowReportResponse:
    """Return the Operating Free Cashflow waterfall for the authenticated tenant."""
    return _cached_report_call(
        owner_id=owner.id,
        cache_key="reports:operating-cashflow",
        cache_params=_report_cache_params("operating-cashflow", filters),
        settings=settings,
        redis=redis,
        response=response,
        response_type=OperatingCashflowReportResponse,
        builder=lambda: OperatingCashflowReportResponse.from_service(
            report_service.operating_cashflow(owner=owner, **filters.service_kwargs()),
            start_date=filters.start_date,
            end_date=filters.end_date,
        ),
    )


@router.get("/planned-vs-actual", response_model=PlannedVsActualReportResponse)
def get_planned_vs_actual_report(  # pylint: disable=too-many-positional-arguments
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    filters: Annotated[ReportPlannedVsActualQuery, Depends(get_report_planned_vs_actual_query)],
    settings: Annotated[Settings, Depends(get_settings)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    response: Response,
) -> PlannedVsActualReportResponse:
    """Return Planned vs. Actual template variance and reconciliation alerts for ``owner``."""
    return _cached_report_call(
        owner_id=owner.id,
        cache_key="reports:planned-vs-actual",
        cache_params=_report_cache_params("planned-vs-actual", filters),
        settings=settings,
        redis=redis,
        response=response,
        response_type=PlannedVsActualReportResponse,
        builder=lambda: PlannedVsActualReportResponse.from_service(
            report_service.planned_vs_actual(owner=owner, **filters.service_kwargs()),
            start_date=filters.start_date,
            end_date=filters.end_date,
        ),
    )


@router.get("/debt-paydown", response_model=DebtPaydownReportResponse)
def get_debt_paydown_report(  # pylint: disable=too-many-positional-arguments
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    filters: Annotated[ReportDebtPaydownQuery, Depends(get_report_debt_paydown_query)],
    settings: Annotated[Settings, Depends(get_settings)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    response: Response,
) -> DebtPaydownReportResponse:
    """Return active liabilities ranked by effective annual rate and monthly interest drag."""
    return _cached_report_call(
        owner_id=owner.id,
        cache_key="reports:debt-paydown",
        cache_params=_report_cache_params("debt-paydown", filters),
        settings=settings,
        redis=redis,
        response=response,
        response_type=DebtPaydownReportResponse,
        builder=lambda: DebtPaydownReportResponse.from_service(
            report_service.debt_paydown(owner=owner, **filters.service_kwargs()),
        ),
    )


@router.post("/debt-paydown/simulate", response_model=DebtPaydownSimulationResponse)
def simulate_debt_paydown_report(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    body: DebtPaydownSimulationRequest,
) -> DebtPaydownSimulationResponse:
    """Simulate accelerated debt paydown and return trajectory plus liquidity guardrail.

    Args:
        owner: Authenticated tenant from JWT.
        report_service: Injected report aggregation service.
        body: Prepayment strategy, recurring/lump-sum inputs, and runway floor.

    Returns:
        DebtPaydownSimulationResponse comparing baseline vs. accelerated schedules.
    """
    payload = report_service.simulate_debt_paydown(
        owner=owner,
        currency=body.currency,
        strategy=body.strategy,
        extra_monthly_prepayment=body.extra_monthly_prepayment,
        lump_sum_prepayment=body.lump_sum_prepayment,
        lump_sum_month_offset=body.lump_sum_month_offset,
        periodic_lump_sums=[item.model_dump(mode="python") for item in body.periodic_lump_sums],
        target_liquidity_months=body.target_liquidity_months,
        horizon_months=body.horizon_months,
    )
    return DebtPaydownSimulationResponse.from_service(payload)


@router.get("/financial-health", response_model=FinancialHealthReportResponse)
def get_financial_health_report(  # pylint: disable=too-many-positional-arguments
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    filters: Annotated[ReportFinancialHealthQuery, Depends(get_report_financial_health_query)],
    settings: Annotated[Settings, Depends(get_settings)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    response: Response,
) -> FinancialHealthReportResponse:
    """Return API-computed Financial Health Scorecard (Net Worth, Runway, Debt Service, LTV)."""
    return _cached_report_call(
        owner_id=owner.id,
        cache_key="reports:financial-health",
        cache_params=_report_cache_params("financial-health", filters),
        settings=settings,
        redis=redis,
        response=response,
        response_type=FinancialHealthReportResponse,
        builder=lambda: FinancialHealthReportResponse.from_service(
            report_service.financial_health(owner=owner, **filters.service_kwargs()),
        ),
    )
