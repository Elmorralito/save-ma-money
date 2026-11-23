"""Report request/response schemas for PPT-038 (FR-12).

Maps lean ``ReportService`` payloads to the API README response envelopes.
All report responses are produced for a single authenticated tenant (``owner=``);
schemas themselves carry no cross-tenant identifiers beyond filter values that
the service has already validated as owned by that tenant.

Category/account names and optional enrichment fields (insights, by_account,
trend series) are stubbed where the model layer does not yet provide them.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReportPeriod(BaseModel):
    """Inclusive report date window."""

    start_date: date
    end_date: date


class SpendingBreakdownItem(BaseModel):
    """One spending group in the breakdown list."""

    category: str
    amount: float
    percentage: float = 0.0
    transaction_count: int = 0


class SpendingTrendPoint(BaseModel):
    """Optional daily trend point (stubbed empty in MVP)."""

    date: date
    spending: float = 0.0
    income: float = 0.0


class SpendingReportResponse(BaseModel):
    """Response body for ``GET /reports/spending``."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    period: ReportPeriod
    total_spending: float = 0.0
    total_income: float = 0.0
    net_savings: float = 0.0
    group_by: str = "category"
    breakdown: list[SpendingBreakdownItem] = Field(default_factory=list)
    trend: list[SpendingTrendPoint] = Field(default_factory=list)

    @classmethod
    def from_service(
        cls,
        payload: dict[str, Any],
        *,
        start_date: date,
        end_date: date,
    ) -> SpendingReportResponse:
        """Map ``ReportService.spending`` output to the API envelope."""
        expense_total = float(payload.get("expense_total", 0.0) or 0.0)
        income_total = float(payload.get("income_total", 0.0) or 0.0)
        breakdown: list[SpendingBreakdownItem] = []
        for row in payload.get("expenses", []) or []:
            amount = float(row.get("total", 0.0) or 0.0)
            group_id = row.get("category_id") or row.get("from_account_id") or "unknown"
            percentage = (amount / expense_total * 100.0) if expense_total else 0.0
            breakdown.append(
                SpendingBreakdownItem(
                    category=str(group_id),
                    amount=amount,
                    percentage=round(percentage, 2),
                    transaction_count=0,
                )
            )
        return cls(
            period=ReportPeriod(start_date=start_date, end_date=end_date),
            total_spending=expense_total,
            total_income=income_total,
            net_savings=income_total - expense_total,
            group_by=str(payload.get("group_by", "category")),
            breakdown=breakdown,
            trend=[],
        )


class CashFlowByAccountItem(BaseModel):
    """Per-account cash-flow rollup (stubbed empty in MVP)."""

    account_id: str
    account_name: str = ""
    inflows: float = 0.0
    outflows: float = 0.0
    net: float = 0.0


class CashFlowReportResponse(BaseModel):
    """Response body for ``GET /reports/cash-flow``."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    period: ReportPeriod
    opening_balance: float = 0.0
    closing_balance: float = 0.0
    total_inflows: float = 0.0
    total_outflows: float = 0.0
    net_cash_flow: float = 0.0
    by_account: list[CashFlowByAccountItem] = Field(default_factory=list)

    @classmethod
    def from_service(
        cls,
        payload: dict[str, Any],
        *,
        start_date: date,
        end_date: date,
    ) -> CashFlowReportResponse:
        """Map ``ReportService.cash_flow`` output to the API envelope."""
        inflows = float(payload.get("inflows", 0.0) or 0.0)
        outflows = float(payload.get("outflows", 0.0) or 0.0)
        portfolio_total = float(payload.get("portfolio_total", 0.0) or 0.0)
        return cls(
            period=ReportPeriod(start_date=start_date, end_date=end_date),
            opening_balance=0.0,
            closing_balance=portfolio_total,
            total_inflows=inflows,
            total_outflows=outflows,
            net_cash_flow=float(payload.get("net", inflows - outflows) or 0.0),
            by_account=[],
        )


class MonthlyTrendItem(BaseModel):
    """One period bucket for trends."""

    month: str
    total_spending: float = 0.0
    total_income: float = 0.0
    savings_rate: float = 0.0


class CategoryTrendItem(BaseModel):
    """Category trend stub (empty in MVP)."""

    category: str
    average_monthly: float = 0.0
    trend: str = "stable"
    change_percentage: float = 0.0


class TrendInsight(BaseModel):
    """Narrative insight stub (empty in MVP)."""

    type: str
    message: str


class TrendsReportResponse(BaseModel):
    """Response body for ``GET /reports/trends``."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    analysis_period: ReportPeriod
    period: str = "monthly"
    monthly_trends: list[MonthlyTrendItem] = Field(default_factory=list)
    category_trends: list[CategoryTrendItem] = Field(default_factory=list)
    insights: list[TrendInsight] = Field(default_factory=list)

    @staticmethod
    def _period_bucket_key(period_start: Any) -> str | None:
        """Normalize a series period start to a ``YYYY-MM`` bucket key."""
        if period_start is None:
            return None
        if hasattr(period_start, "strftime"):
            return period_start.strftime("%Y-%m")
        return str(period_start)[:7]

    @classmethod
    def _series_to_monthly_buckets(cls, series: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
        """Roll service series rows into month → spending/income totals."""
        buckets: dict[str, dict[str, float]] = {}
        for row in series:
            key = cls._period_bucket_key(row.get("period_start"))
            if key is None:
                continue
            bucket = buckets.setdefault(key, {"spending": 0.0, "income": 0.0})
            kind = str(row.get("transaction_kind", "")).upper()
            total = float(row.get("total", 0.0) or 0.0)
            if kind == "EXPENSE":
                bucket["spending"] += total
            elif kind == "INCOME":
                bucket["income"] += total
        return buckets

    @staticmethod
    def _monthly_trends_from_buckets(buckets: dict[str, dict[str, float]]) -> list[MonthlyTrendItem]:
        """Build monthly trend items with savings rate from bucket totals."""
        monthly_trends: list[MonthlyTrendItem] = []
        for month, totals in sorted(buckets.items()):
            spending = totals["spending"]
            income = totals["income"]
            savings_rate = ((income - spending) / income * 100.0) if income else 0.0
            monthly_trends.append(
                MonthlyTrendItem(
                    month=month,
                    total_spending=spending,
                    total_income=income,
                    savings_rate=round(savings_rate, 2),
                )
            )
        return monthly_trends

    @classmethod
    def from_service(
        cls,
        payload: dict[str, Any],
        *,
        start_date: date,
        end_date: date,
    ) -> TrendsReportResponse:
        """Map ``ReportService.trends`` series into monthly trend rows."""
        buckets = cls._series_to_monthly_buckets(list(payload.get("series", []) or []))
        return cls(
            analysis_period=ReportPeriod(start_date=start_date, end_date=end_date),
            period=str(payload.get("period", "monthly")),
            monthly_trends=cls._monthly_trends_from_buckets(buckets),
            category_trends=[],
            insights=[],
        )


class BucketCategoryItem(BaseModel):
    """Top category rollup within a waterfall bucket."""

    category_id: str | None = None
    category_name: str
    amount: float = 0.0
    transaction_count: int = 0


class WaterfallBucketItem(BaseModel):
    """Single bucket row in the Operating Free Cashflow waterfall."""

    bucket: str
    label: str
    group: Literal["income", "operating_outflow", "allocation", "non_operating"]
    amount: float = 0.0
    share_of_income_pct: float = 0.0
    transaction_count: int = 0
    top_categories: list[BucketCategoryItem] = Field(default_factory=list)


class WaterfallSummary(BaseModel):
    """Headline Operating Free Cashflow metrics."""

    income_fixed: float = 0.0
    income_variable: float = 0.0
    total_external_income: float = 0.0
    loans: float = 0.0
    fixed_expenses: float = 0.0
    variable_expenses: float = 0.0
    unexpected_expenses: float = 0.0
    total_operating_outflows: float = 0.0
    operating_free_cashflow: float = 0.0
    organic_fcf_margin_pct: float = 0.0
    debt_service_to_income_pct: float = 0.0
    savings: float = 0.0
    capital_deployments: float = 0.0
    net_allocated_surplus: float = 0.0
    non_operating_inflows: float = 0.0
    net_ledger_cashflow: float = 0.0
    internal_sweeps_volume: float = 0.0
    status_tone: Literal["positive", "warning", "negative"] = "positive"


class InTransitSummary(BaseModel):
    """Summary of COMPLETED transactions still awaiting settlement."""

    count: int = 0
    inflows: float = 0.0
    outflows: float = 0.0
    total_volume: float = 0.0


class MonthlyWaterfallPoint(BaseModel):
    """Monthly breakdown point inside the waterfall report."""

    month: str
    total_external_income: float = 0.0
    total_operating_outflows: float = 0.0
    operating_free_cashflow: float = 0.0
    organic_fcf_margin_pct: float = 0.0
    savings: float = 0.0
    capital_deployments: float = 0.0
    non_operating_inflows: float = 0.0


class WaterfallDiagnostics(BaseModel):
    """Classification diagnostics for waterfall hygiene."""

    unbucketed_category_count: int = 0
    unbucketed_amount: float = 0.0
    cashflow_only_cc_excluded_count: int = 0
    cashflow_only_cc_excluded_amount: float = 0.0
    cashflow_only_cc_account_names: list[str] = Field(default_factory=list)


class OperatingCashflowReportResponse(BaseModel):
    """Response body for ``GET /reports/operating-cashflow``."""

    period: ReportPeriod
    currency: str
    available_currencies: list[str] = Field(default_factory=list)
    multi_currency_warning: bool = False
    waterfall: WaterfallSummary
    buckets: list[WaterfallBucketItem] = Field(default_factory=list)
    in_transit: InTransitSummary = Field(default_factory=InTransitSummary)
    monthly_series: list[MonthlyWaterfallPoint] = Field(default_factory=list)
    diagnostics: WaterfallDiagnostics = Field(default_factory=WaterfallDiagnostics)

    @classmethod
    def from_service(
        cls,
        payload: dict[str, Any],
        *,
        start_date: date,
        end_date: date,
    ) -> OperatingCashflowReportResponse:
        """Map ``ReportService.operating_cashflow`` payload to API response."""
        return cls.model_validate(
            {
                "period": {"start_date": start_date, "end_date": end_date},
                **payload,
            }
        )


class PlannedVsActualSummary(BaseModel):
    """Summary metrics for Planned vs. Actual comparison."""

    planned_income: float = 0.0
    actual_income: float = 0.0
    planned_outflows: float = 0.0
    actual_outflows: float = 0.0
    planned_operating_fcf: float = 0.0
    actual_operating_fcf: float = 0.0
    net_fcf_variance: float = 0.0
    adherence_pct: float = 0.0
    reconciliation_flag_count: int = 0
    status_tone: Literal["positive", "warning", "negative"] = "positive"


class BucketVarianceItem(BaseModel):
    """Per-bucket planned vs. actual variance rollup."""

    bucket: str
    label: str
    planned_amount: float = 0.0
    actual_amount: float = 0.0
    variance_amount: float = 0.0
    variance_pct: float = 0.0
    is_favorable: bool = True


class TemplateVarianceItem(BaseModel):
    """Planned template occurrence compared against linked settled postings."""

    template_id: str
    template_name: str
    category_id: str | None = None
    category_name: str
    bucket: str
    due_date: date
    planned_amount: float = 0.0
    actual_amount: float = 0.0
    variance_amount: float = 0.0
    variance_pct: float = 0.0
    is_favorable: bool = True
    status: Literal["paid", "partial", "over_budget", "exceeded", "overdue", "upcoming"]
    linked_transaction_count: int = 0


class UnplannedCategoryItem(BaseModel):
    """Settled actuals not matched to an expanded template occurrence."""

    category_id: str | None = None
    category_name: str
    bucket: str
    actual_amount: float = 0.0
    transaction_count: int = 0
    status: Literal["unplanned"] = "unplanned"


class ReconciliationFlagItem(BaseModel):
    """Automated reconciliation diagnostic alert."""

    code: Literal["unlinked_high_value", "potential_duplicate", "unbucketed_category"]
    severity: Literal["info", "warning"]
    message: str
    transaction_id: str | None = None
    template_id: str | None = None
    category_id: str | None = None
    amount: float | None = None


class PlannedVsActualReportResponse(BaseModel):
    """Response body for ``GET /reports/planned-vs-actual``."""

    period: ReportPeriod
    currency: str
    available_currencies: list[str] = Field(default_factory=list)
    multi_currency_warning: bool = False
    summary: PlannedVsActualSummary
    bucket_rollups: list[BucketVarianceItem] = Field(default_factory=list)
    template_items: list[TemplateVarianceItem] = Field(default_factory=list)
    unplanned_items: list[UnplannedCategoryItem] = Field(default_factory=list)
    reconciliation_flags: list[ReconciliationFlagItem] = Field(default_factory=list)

    @classmethod
    def from_service(
        cls,
        payload: dict[str, Any],
        *,
        start_date: date,
        end_date: date,
    ) -> PlannedVsActualReportResponse:
        """Map ``ReportService.planned_vs_actual`` payload to API response."""
        return cls.model_validate(
            {
                "period": {"start_date": start_date, "end_date": end_date},
                **payload,
            }
        )


class LinkedAssetCarry(BaseModel):
    """Asset financing context linked to a liability via ``AccountFinancing``."""

    asset_id: str
    asset_name: str
    asset_current_value: float = 0.0
    financing_share: float = 1.0
    asset_monthly_earnings: float = 0.0
    net_monthly_carry: float = 0.0


class DebtLiabilityItem(BaseModel):
    """Ranked active liability with normalized EA/MV rates and interest drag."""

    priority_rank: int
    account_id: str
    account_name: str
    account_kind: str
    currency: str
    balance: float = 0.0
    effective_annual_rate_pct: float = 0.0
    effective_monthly_rate_pct: float = 0.0
    monthly_interest_drag: float = 0.0
    annual_interest_drag: float = 0.0
    monthly_contractual_payment: float = 0.0
    monthly_extras_payment: float = 0.0
    monthly_principal_amortization: float = 0.0
    remaining_periods: int | None = None
    estimated_payoff_date: date | None = None
    negative_amortization: bool = False
    linked_asset: LinkedAssetCarry | None = None


class DebtPaydownSummary(BaseModel):
    """Aggregate debt drag metrics across active liabilities."""

    total_debt: float = 0.0
    active_liability_count: int = 0
    total_monthly_interest_drag: float = 0.0
    total_annual_interest_drag: float = 0.0
    total_monthly_contractual_payment: float = 0.0
    weighted_average_ea_pct: float = 0.0
    highest_rate_account_name: str | None = None
    highest_rate_payoff_date: date | None = None


class DebtLiquidityContext(BaseModel):
    """Liquid cash buffer & runway context for prepayment safety."""

    liquid_cash_total: float = 0.0
    baseline_monthly_burn: float = 0.0
    liquid_runway_months: float | None = None
    target_liquidity_months: float = 4.0
    safe_lump_sum_headroom: float = 0.0


class ExcludedLiabilitiesSummary(BaseModel):
    """Optional summary of paid-off or balance-excluded liabilities."""

    count: int = 0
    total_balance: float = 0.0
    account_names: list[str] = Field(default_factory=list)


class DebtPaydownReportResponse(BaseModel):
    """Response body for ``GET /reports/debt-paydown``."""

    currency: str
    available_currencies: list[str] = Field(default_factory=list)
    multi_currency_warning: bool = False
    summary: DebtPaydownSummary
    liabilities: list[DebtLiabilityItem] = Field(default_factory=list)
    liquidity_context: DebtLiquidityContext
    excluded_liabilities: ExcludedLiabilitiesSummary | None = None

    @classmethod
    def from_service(cls, payload: dict[str, Any]) -> DebtPaydownReportResponse:
        """Map ``ReportService.debt_paydown`` payload to API response."""
        return cls.model_validate(payload)


class PeriodicLumpSumInput(BaseModel):
    """Recurring annual calendar-month lump-sum prepayment input (e.g. bonus month)."""

    model_config = ConfigDict(extra="forbid")

    month_of_year: int = Field(ge=1, le=12)
    amount: float = Field(gt=0)


class DebtPaydownSimulationRequest(BaseModel):
    """Request body for ``POST /reports/debt-paydown/simulate``."""

    model_config = ConfigDict(extra="forbid")

    currency: str | None = Field(default=None, min_length=3, max_length=3)
    strategy: Literal["avalanche", "snowball"] = "avalanche"
    extra_monthly_prepayment: float = Field(default=0.0, ge=0)
    lump_sum_prepayment: float = Field(default=0.0, ge=0)
    lump_sum_month_offset: int = Field(default=1, ge=1, le=120)
    periodic_lump_sums: list[PeriodicLumpSumInput] = Field(default_factory=list, max_length=12)
    target_liquidity_months: float = Field(default=4.0, ge=0, le=24)
    horizon_months: int = Field(default=60, ge=1, le=360)

    @model_validator(mode="after")
    def _normalize_currency(self) -> DebtPaydownSimulationRequest:
        if self.currency is not None:
            self.currency = self.currency.strip().upper()
        return self


class LiabilitySimulationImpact(BaseModel):
    """Per-liability payoff impact comparing baseline vs. accelerated simulation."""

    account_id: str
    account_name: str
    effective_annual_rate_pct: float = 0.0
    starting_balance: float = 0.0
    baseline_payoff_date: date | None = None
    accelerated_payoff_date: date | None = None
    months_saved: int | None = None
    interest_saved: float = 0.0


class DebtTrajectoryPoint(BaseModel):
    """Monthly trajectory snapshot comparing baseline vs. accelerated debt."""

    month: str
    baseline_total_debt: float = 0.0
    accelerated_total_debt: float = 0.0
    priority_loan_balance: float = 0.0
    interest_paid: float = 0.0
    extra_applied: float = 0.0
    events: list[str] = Field(default_factory=list)


class LiquidityGuardrail(BaseModel):
    """Safety evaluation ensuring prepayments preserve emergency cash runway."""

    status: Literal["safe", "caution", "warning"]
    liquid_cash_total: float = 0.0
    post_lump_sum_cash: float = 0.0
    post_lump_sum_runway_months: float | None = None
    target_liquidity_months: float = 4.0
    safe_lump_sum_headroom: float = 0.0
    message: str


class DebtPaydownSimulationResponse(BaseModel):
    """Response body for ``POST /reports/debt-paydown/simulate``."""

    currency: str
    strategy: Literal["avalanche", "snowball"]
    baseline_months_to_payoff: int | None = None
    accelerated_months_to_payoff: int | None = None
    baseline_payoff_date: date | None = None
    accelerated_payoff_date: date | None = None
    months_saved: int | None = None
    baseline_total_interest: float = 0.0
    accelerated_total_interest: float = 0.0
    total_interest_saved: float = 0.0
    per_liability_impact: list[LiabilitySimulationImpact] = Field(default_factory=list)
    monthly_trajectory: list[DebtTrajectoryPoint] = Field(default_factory=list)
    liquidity_guardrail: LiquidityGuardrail

    @classmethod
    def from_service(cls, payload: dict[str, Any]) -> DebtPaydownSimulationResponse:
        """Map ``ReportService.simulate_debt_paydown`` payload to API response."""
        return cls.model_validate(payload)


__all__ = [
    "BucketCategoryItem",
    "BucketVarianceItem",
    "CashFlowByAccountItem",
    "CashFlowReportResponse",
    "CategoryTrendItem",
    "DebtLiabilityItem",
    "DebtLiquidityContext",
    "DebtPaydownReportResponse",
    "DebtPaydownSimulationRequest",
    "DebtPaydownSimulationResponse",
    "DebtPaydownSummary",
    "DebtTrajectoryPoint",
    "ExcludedLiabilitiesSummary",
    "InTransitSummary",
    "LiabilitySimulationImpact",
    "LinkedAssetCarry",
    "LiquidityGuardrail",
    "MonthlyTrendItem",
    "MonthlyWaterfallPoint",
    "OperatingCashflowReportResponse",
    "PeriodicLumpSumInput",
    "PlannedVsActualReportResponse",
    "PlannedVsActualSummary",
    "ReconciliationFlagItem",
    "ReportPeriod",
    "SpendingBreakdownItem",
    "SpendingReportResponse",
    "SpendingTrendPoint",
    "TemplateVarianceItem",
    "TrendInsight",
    "TrendsReportResponse",
    "UnplannedCategoryItem",
    "WaterfallBucketItem",
    "WaterfallDiagnostics",
    "WaterfallSummary",
]
