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
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


__all__ = [
    "CashFlowByAccountItem",
    "CashFlowReportResponse",
    "CategoryTrendItem",
    "MonthlyTrendItem",
    "ReportPeriod",
    "SpendingBreakdownItem",
    "SpendingReportResponse",
    "SpendingTrendPoint",
    "TrendInsight",
    "TrendsReportResponse",
]
