"""Financial projection and amortization engine (Colombia EA & USA APR/APY).

All financial calculations live in Python so the web SPA remains presentation-only.
Supports:
- Colombian Effective Annual (``CO_EA``: ``(1 + EA)^(1/12) - 1``)
- US Nominal APR (``US_APR``: ``APR / 12``)
- US Annual Percentage Yield (``US_APY``: ``(1 + APY)^(1/12) - 1``)
- Direct Monthly Effective (``MONTHLY_MV``: ``r_m``)
"""

from __future__ import annotations

import math
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RateConvention = Literal["CO_EA", "US_APR", "US_APY", "MONTHLY_MV"]
AmortizationMethod = Literal["french_fixed", "german_constant_principal"]
InvestmentType = Literal[
    "hysa_co",
    "fiduciary_co",
    "cdt_co",
    "voluntary_pension",
    "us_equity_etf",
    "crypto",
    "private_equity",
    "real_estate_fund",
]


def annual_to_monthly_rate(rate_pct: float, convention: RateConvention) -> float:
    """Convert an annual (or monthly) percentage rate to a decimal monthly rate."""
    if rate_pct <= 0:
        return 0.0
    r = rate_pct / 100.0
    if convention in {"CO_EA", "US_APY"}:
        return (1.0 + r) ** (1.0 / 12.0) - 1.0
    if convention == "US_APR":
        return r / 12.0
    return r  # MONTHLY_MV


def monthly_to_effective_annual_pct(monthly_rate: float) -> float:
    """Convert a decimal monthly rate to an Effective Annual (EA / APY) percentage."""
    if monthly_rate <= 0:
        return 0.0
    return ((1.0 + monthly_rate) ** 12 - 1.0) * 100.0


def _add_months(start: date, months: int) -> date:
    month_idx = (start.month - 1) + months
    year = start.year + month_idx // 12
    month = (month_idx % 12) + 1
    # Clamp day to end of target month
    for day in (min(start.day, 31), 30, 29, 28):
        try:
            return date(year, month, day)
        except ValueError:
            continue
    return date(year, month, 1)


# ---------------------------------------------------------------------------
# 1. Loan / Debt Amortization
# ---------------------------------------------------------------------------


class LoanAmortizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    principal: float = Field(gt=0)
    annual_rate_pct: float = Field(ge=0, le=200)
    rate_convention: RateConvention = "CO_EA"
    remaining_months: int = Field(ge=1, le=480)
    monthly_insurance: float = Field(default=0.0, ge=0)
    extra_monthly_payment: float = Field(default=0.0, ge=0)
    extra_lump_sum: float = Field(default=0.0, ge=0)
    lump_sum_month: int = Field(default=1, ge=1, le=480)
    method: AmortizationMethod = "french_fixed"
    currency: str = Field(default="COP", min_length=3, max_length=3)
    start_date: date | None = None


class LoanAmortizationRow(BaseModel):
    month: int
    payment_date: str
    opening_balance: float
    scheduled_payment: float
    principal_paid: float
    interest_paid: float
    insurance_paid: float
    extra_paid: float
    total_outflow: float
    closing_balance: float
    cumulative_interest: float


class LoanAmortizationResponse(BaseModel):
    currency: str
    rate_convention: RateConvention
    annual_rate_pct: float
    monthly_rate_pct: float
    effective_annual_rate_pct: float
    scheduled_monthly_payment: float
    total_monthly_outflow: float
    payoff_months: int
    total_interest: float
    total_insurance: float
    total_paid: float
    interest_saved_vs_baseline: float
    months_saved_vs_baseline: int
    schedule: list[LoanAmortizationRow]


def _simulate_loan(
    *,
    principal: float,
    monthly_rate: float,
    remaining_months: int,
    monthly_insurance: float,
    extra_monthly: float,
    extra_lump_sum: float,
    lump_sum_month: int,
    method: AmortizationMethod,
    anchor: date,
) -> tuple[float, list[LoanAmortizationRow]]:
    if method == "french_fixed":
        if monthly_rate == 0:
            base_payment = principal / remaining_months
        else:
            factor = (1.0 + monthly_rate) ** remaining_months
            base_payment = principal * (monthly_rate * factor) / (factor - 1.0)
    else:
        base_payment = principal / remaining_months

    balance = principal
    cum_interest = 0.0
    rows: list[LoanAmortizationRow] = []

    for m in range(1, remaining_months + 1):
        if balance <= 0.01:
            break
        opening = balance
        interest = opening * monthly_rate
        if method == "french_fixed":
            sched_principal = max(0.0, base_payment - interest)
            sched_payment = base_payment
        else:
            sched_principal = base_payment
            sched_payment = sched_principal + interest

        if sched_principal > opening:
            sched_principal = opening
            sched_payment = sched_principal + interest

        remaining_after_sched = max(0.0, opening - sched_principal)
        extra = extra_monthly + (extra_lump_sum if m == lump_sum_month else 0.0)
        extra_applied = min(extra, remaining_after_sched)

        principal_paid = sched_principal + extra_applied
        closing = max(0.0, opening - principal_paid)
        cum_interest += interest
        total_outflow = sched_payment + extra_applied + monthly_insurance

        rows.append(
            LoanAmortizationRow(
                month=m,
                payment_date=_add_months(anchor, m).isoformat(),
                opening_balance=round(opening, 2),
                scheduled_payment=round(sched_payment, 2),
                principal_paid=round(principal_paid, 2),
                interest_paid=round(interest, 2),
                insurance_paid=round(monthly_insurance, 2),
                extra_paid=round(extra_applied, 2),
                total_outflow=round(total_outflow, 2),
                closing_balance=round(closing, 2),
                cumulative_interest=round(cum_interest, 2),
            )
        )
        balance = closing

    first_sched = rows[0].scheduled_payment if rows else round(base_payment, 2)
    return first_sched, rows


def build_loan_amortization(req: LoanAmortizationRequest) -> LoanAmortizationResponse:
    """Compute a full loan amortization schedule with extra-payment savings comparison."""
    anchor = req.start_date or date.today()
    monthly_rate = annual_to_monthly_rate(req.annual_rate_pct, req.rate_convention)
    eff_ea = monthly_to_effective_annual_pct(monthly_rate)

    first_sched, rows = _simulate_loan(
        principal=req.principal,
        monthly_rate=monthly_rate,
        remaining_months=req.remaining_months,
        monthly_insurance=req.monthly_insurance,
        extra_monthly=req.extra_monthly_payment,
        extra_lump_sum=req.extra_lump_sum,
        lump_sum_month=req.lump_sum_month,
        method=req.method,
        anchor=anchor,
    )

    if req.extra_monthly_payment > 0 or req.extra_lump_sum > 0:
        _, base_rows = _simulate_loan(
            principal=req.principal,
            monthly_rate=monthly_rate,
            remaining_months=req.remaining_months,
            monthly_insurance=req.monthly_insurance,
            extra_monthly=0.0,
            extra_lump_sum=0.0,
            lump_sum_month=1,
            method=req.method,
            anchor=anchor,
        )
        base_interest = sum(r.interest_paid for r in base_rows)
        base_months = len(base_rows)
    else:
        base_interest = sum(r.interest_paid for r in rows)
        base_months = len(rows)

    total_interest = round(sum(r.interest_paid for r in rows), 2)
    total_insurance = round(sum(r.insurance_paid for r in rows), 2)
    total_paid = round(sum(r.total_outflow for r in rows), 2)

    return LoanAmortizationResponse(
        currency=req.currency.upper(),
        rate_convention=req.rate_convention,
        annual_rate_pct=round(req.annual_rate_pct, 4),
        monthly_rate_pct=round(monthly_rate * 100.0, 4),
        effective_annual_rate_pct=round(eff_ea, 4),
        scheduled_monthly_payment=round(first_sched, 2),
        total_monthly_outflow=round(first_sched + req.monthly_insurance + req.extra_monthly_payment, 2),
        payoff_months=len(rows),
        total_interest=total_interest,
        total_insurance=total_insurance,
        total_paid=total_paid,
        interest_saved_vs_baseline=round(max(0.0, base_interest - total_interest), 2),
        months_saved_vs_baseline=max(0, base_months - len(rows)),
        schedule=rows,
    )


# ---------------------------------------------------------------------------
# 2. Credit Card Payoff Projection (Colombian Cuotas / Revolving vs US APR)
# ---------------------------------------------------------------------------


class CreditCardProjectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    balance: float = Field(ge=0)
    annual_rate_pct: float = Field(default=25.0, ge=0, le=200)
    rate_convention: RateConvention = "CO_EA"
    monthly_payment: float = Field(gt=0)
    monthly_new_spend: float = Field(default=0.0, ge=0)
    handling_fee: float = Field(default=0.0, ge=0)
    pay_in_one_installment: bool = False
    max_months: int = Field(default=120, ge=1, le=360)
    currency: str = Field(default="COP", min_length=3, max_length=3)
    start_date: date | None = None


class CreditCardProjectionRow(BaseModel):
    month: int
    payment_date: str
    opening_balance: float
    new_spend: float
    interest_charged: float
    fee_charged: float
    payment: float
    closing_balance: float


class CreditCardProjectionResponse(BaseModel):
    currency: str
    rate_convention: RateConvention
    monthly_rate_pct: float
    effective_annual_rate_pct: float
    months_to_payoff: int | None
    total_interest: float
    total_fees: float
    total_paid: float
    warning: str | None = None
    schedule: list[CreditCardProjectionRow]


def build_credit_card_projection(req: CreditCardProjectionRequest) -> CreditCardProjectionResponse:
    """Project credit card payoff under Colombian EA (or 1-cuota 0%) or US APR."""
    anchor = req.start_date or date.today()
    effective_rate_pct = 0.0 if req.pay_in_one_installment else req.annual_rate_pct
    monthly_rate = annual_to_monthly_rate(effective_rate_pct, req.rate_convention)
    eff_ea = monthly_to_effective_annual_pct(monthly_rate)

    balance = req.balance
    rows: list[CreditCardProjectionRow] = []
    warning: str | None = None

    for m in range(1, req.max_months + 1):
        if balance <= 0.01 and req.monthly_new_spend == 0:
            break
        opening = balance
        interest = 0.0 if req.pay_in_one_installment else opening * monthly_rate
        fee = req.handling_fee
        due_total = opening + req.monthly_new_spend + interest + fee
        payment = min(req.monthly_payment, due_total)
        closing = max(0.0, due_total - payment)

        rows.append(
            CreditCardProjectionRow(
                month=m,
                payment_date=_add_months(anchor, m).isoformat(),
                opening_balance=round(opening, 2),
                new_spend=round(req.monthly_new_spend, 2),
                interest_charged=round(interest, 2),
                fee_charged=round(fee, 2),
                payment=round(payment, 2),
                closing_balance=round(closing, 2),
            )
        )
        balance = closing
        if m == 1 and closing >= opening and req.balance > 0:
            warning = "Monthly payment does not cover interest, fees, and new spend — balance will not decrease."

    paid_off = balance <= 0.01
    if not paid_off and warning is None:
        warning = f"Balance not paid off within {req.max_months} months."

    return CreditCardProjectionResponse(
        currency=req.currency.upper(),
        rate_convention=req.rate_convention,
        monthly_rate_pct=round(monthly_rate * 100.0, 4),
        effective_annual_rate_pct=round(eff_ea, 4),
        months_to_payoff=len(rows) if paid_off else None,
        total_interest=round(sum(r.interest_charged for r in rows), 2),
        total_fees=round(sum(r.fee_charged for r in rows), 2),
        total_paid=round(sum(r.payment for r in rows), 2),
        warning=warning,
        schedule=rows,
    )


# ---------------------------------------------------------------------------
# 3. Real Estate Valuation, Equity & Rental Cashflow Projection
# ---------------------------------------------------------------------------


class RealEstateProjectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_value: float = Field(gt=0)
    annual_appreciation_pct: float = Field(default=8.0, ge=-30, le=50)
    horizon_years: int = Field(default=10, ge=1, le=30)
    monthly_rent_income: float = Field(default=0.0, ge=0)
    occupancy_pct: float = Field(default=85.0, ge=0, le=100)
    annual_rent_growth_pct: float = Field(default=5.0, ge=-10, le=30)
    monthly_hoa_and_maintenance: float = Field(default=0.0, ge=0)
    annual_property_tax_pct: float = Field(default=0.6, ge=0, le=10)
    mortgage_balance: float = Field(default=0.0, ge=0)
    mortgage_annual_rate_pct: float = Field(default=17.1, ge=0, le=100)
    mortgage_rate_convention: RateConvention = "CO_EA"
    mortgage_remaining_months: int = Field(default=0, ge=0, le=480)
    mortgage_monthly_insurance: float = Field(default=0.0, ge=0)
    currency: str = Field(default="COP", min_length=3, max_length=3)


class RealEstateProjectionYear(BaseModel):
    year: int
    property_value: float
    mortgage_balance: float
    net_equity: float
    annual_gross_rent: float
    annual_operating_costs: float
    annual_mortgage_service: float
    annual_net_cashflow: float
    cumulative_net_cashflow: float


class RealEstateProjectionResponse(BaseModel):
    currency: str
    current_net_equity: float
    projected_property_value: float
    projected_mortgage_balance: float
    projected_net_equity: float
    cumulative_net_cashflow: float
    gross_rental_yield_pct: float
    cap_rate_pct: float
    schedule: list[RealEstateProjectionYear]


def build_real_estate_projection(req: RealEstateProjectionRequest) -> RealEstateProjectionResponse:
    """Project property value, linked mortgage amortization, net equity, and rental cashflow."""
    mortgage_rows: list[LoanAmortizationRow] = []
    if req.mortgage_balance > 0 and req.mortgage_remaining_months > 0:
        mort = build_loan_amortization(
            LoanAmortizationRequest(
                principal=req.mortgage_balance,
                annual_rate_pct=req.mortgage_annual_rate_pct,
                rate_convention=req.mortgage_rate_convention,
                remaining_months=req.mortgage_remaining_months,
                monthly_insurance=req.mortgage_monthly_insurance,
                currency=req.currency,
            )
        )
        mortgage_rows = mort.schedule

    rows: list[RealEstateProjectionYear] = []
    cum_cf = 0.0
    prop_val = req.current_value
    monthly_rent = req.monthly_rent_income
    monthly_hoa = req.monthly_hoa_and_maintenance

    for yr in range(1, req.horizon_years + 1):
        prop_val = prop_val * (1.0 + req.annual_appreciation_pct / 100.0)
        if yr > 1:
            monthly_rent = monthly_rent * (1.0 + req.annual_rent_growth_pct / 100.0)
            monthly_hoa = monthly_hoa * (1.0 + req.annual_rent_growth_pct / 100.0)

        gross_rent = monthly_rent * 12.0 * (req.occupancy_pct / 100.0)
        prop_tax = prop_val * (req.annual_property_tax_pct / 100.0)
        op_costs = monthly_hoa * 12.0 + prop_tax

        start_m = (yr - 1) * 12
        end_m = yr * 12
        yr_mort_rows = mortgage_rows[start_m:end_m]
        mort_service = sum(r.total_outflow for r in yr_mort_rows)
        if yr_mort_rows:
            mort_bal = yr_mort_rows[-1].closing_balance
        elif req.mortgage_balance > 0 and req.mortgage_remaining_months == 0:
            mort_bal = req.mortgage_balance
        else:
            mort_bal = 0.0

        net_cf = gross_rent - op_costs - mort_service
        cum_cf += net_cf
        rows.append(
            RealEstateProjectionYear(
                year=yr,
                property_value=round(prop_val, 2),
                mortgage_balance=round(mort_bal, 2),
                net_equity=round(prop_val - mort_bal, 2),
                annual_gross_rent=round(gross_rent, 2),
                annual_operating_costs=round(op_costs, 2),
                annual_mortgage_service=round(mort_service, 2),
                annual_net_cashflow=round(net_cf, 2),
                cumulative_net_cashflow=round(cum_cf, 2),
            )
        )

    yr1_rent = req.monthly_rent_income * 12.0 * (req.occupancy_pct / 100.0)
    yr1_noi = yr1_rent - (
        req.monthly_hoa_and_maintenance * 12.0 + req.current_value * req.annual_property_tax_pct / 100.0
    )
    gross_yield = (yr1_rent / req.current_value * 100.0) if req.current_value > 0 else 0.0
    cap_rate = (yr1_noi / req.current_value * 100.0) if req.current_value > 0 else 0.0
    last = rows[-1]

    return RealEstateProjectionResponse(
        currency=req.currency.upper(),
        current_net_equity=round(req.current_value - req.mortgage_balance, 2),
        projected_property_value=last.property_value,
        projected_mortgage_balance=last.mortgage_balance,
        projected_net_equity=last.net_equity,
        cumulative_net_cashflow=last.cumulative_net_cashflow,
        gross_rental_yield_pct=round(gross_yield, 2),
        cap_rate_pct=round(cap_rate, 2),
        schedule=rows,
    )


# ---------------------------------------------------------------------------
# 4. Investment Compound Growth Projection (Colombia EA & US APY/APR + FX/Tax)
# ---------------------------------------------------------------------------


class InvestmentProjectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    initial_amount: float = Field(ge=0)
    investment_type: InvestmentType = "us_equity_etf"
    expected_annual_return_pct: float = Field(default=8.0, ge=-50, le=150)
    rate_convention: RateConvention = "US_APY"
    horizon_years: int = Field(default=10, ge=1, le=40)
    monthly_contribution: float = Field(default=0.0, ge=0)
    annual_fee_pct: float = Field(default=0.1, ge=0, le=10)
    annual_inflation_pct: float = Field(default=5.0, ge=0, le=30)
    tax_on_gains_pct: float = Field(default=15.0, ge=0, le=50)
    annual_fx_drift_pct: float = Field(default=0.0, ge=-30, le=30)
    currency: str = Field(default="COP", min_length=3, max_length=3)


class InvestmentProjectionYear(BaseModel):
    year: int
    contributed: float
    gross_value: float
    cumulative_gain: float
    real_value: float
    after_tax_value: float


class InvestmentProjectionResponse(BaseModel):
    currency: str
    investment_type: InvestmentType
    rate_convention: RateConvention
    effective_net_annual_pct: float
    total_contributed: float
    final_gross_value: float
    final_real_value: float
    estimated_tax: float
    final_after_tax_value: float
    total_net_gain: float
    schedule: list[InvestmentProjectionYear]


def build_investment_projection(req: InvestmentProjectionRequest) -> InvestmentProjectionResponse:
    """Project compound investment growth net of fees, inflation, FX drift, and capital-gains tax."""
    gross_monthly = annual_to_monthly_rate(req.expected_annual_return_pct, req.rate_convention)
    fee_monthly = annual_to_monthly_rate(req.annual_fee_pct, "US_APR")
    fx_monthly = (
        annual_to_monthly_rate(req.annual_fx_drift_pct, "US_APY")
        if req.annual_fx_drift_pct >= 0
        else -(annual_to_monthly_rate(abs(req.annual_fx_drift_pct), "US_APY"))
    )
    net_monthly = (1.0 + gross_monthly) * (1.0 + fx_monthly) - 1.0 - fee_monthly
    eff_net_annual = ((1.0 + net_monthly) ** 12 - 1.0) * 100.0 if net_monthly > -1.0 else -100.0

    balance = req.initial_amount
    contributed = req.initial_amount
    rows: list[InvestmentProjectionYear] = []

    for yr in range(1, req.horizon_years + 1):
        for _ in range(12):
            balance = max(0.0, balance * (1.0 + net_monthly) + req.monthly_contribution)
            contributed += req.monthly_contribution
        gain = max(0.0, balance - contributed)
        tax = gain * (req.tax_on_gains_pct / 100.0)
        after_tax = balance - tax
        inflation_divisor = math.pow(1.0 + req.annual_inflation_pct / 100.0, yr)
        real_val = balance / inflation_divisor if inflation_divisor > 0 else balance
        rows.append(
            InvestmentProjectionYear(
                year=yr,
                contributed=round(contributed, 2),
                gross_value=round(balance, 2),
                cumulative_gain=round(balance - contributed, 2),
                real_value=round(real_val, 2),
                after_tax_value=round(after_tax, 2),
            )
        )

    last = rows[-1]
    est_tax = round(max(0.0, last.gross_value - last.contributed) * (req.tax_on_gains_pct / 100.0), 2)
    return InvestmentProjectionResponse(
        currency=req.currency.upper(),
        investment_type=req.investment_type,
        rate_convention=req.rate_convention,
        effective_net_annual_pct=round(eff_net_annual, 2),
        total_contributed=last.contributed,
        final_gross_value=last.gross_value,
        final_real_value=last.real_value,
        estimated_tax=est_tax,
        final_after_tax_value=last.after_tax_value,
        total_net_gain=round(last.after_tax_value - last.contributed, 2),
        schedule=rows,
    )


__all__ = [
    "AmortizationMethod",
    "CreditCardProjectionRequest",
    "CreditCardProjectionResponse",
    "InvestmentProjectionRequest",
    "InvestmentProjectionResponse",
    "InvestmentType",
    "LoanAmortizationRequest",
    "LoanAmortizationResponse",
    "RateConvention",
    "RealEstateProjectionRequest",
    "RealEstateProjectionResponse",
    "annual_to_monthly_rate",
    "build_credit_card_projection",
    "build_investment_projection",
    "build_loan_amortization",
    "build_real_estate_projection",
    "monthly_to_effective_annual_pct",
]
