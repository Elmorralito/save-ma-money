"""Debt interest-drag ranking and backend avalanche/snowball simulator (PPT-091 / #184)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Literal

from papita_txnsmodel.access.account_details.dto import LoanAccountDetailsDTO
from papita_txnsmodel.access.account_financing.dto import AccountFinancingDTO
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.transactions.dto import TransactionTemplatesDTO
from papita_txnsmodel.config.transaction_partitions import add_months
from papita_txnsmodel.model.enums import CategoryKind, InterestRateBasis, LedgerSide
from papita_txnsmodel.services.report_common import LIQUID_ACCOUNT_KINDS, lookup_by_id, resolve_currency_scope


@dataclass
class _SimLoan:
    account_id: str
    name: str
    balance: float
    monthly_rate: float
    effective_annual_rate: float
    scheduled_pi: float
    paid_off_month: int | None = None
    total_interest: float = 0.0


def normalize_interest_rates(raw_rate: float | None, basis: InterestRateBasis | None) -> tuple[float, float]:
    """Normalize APY or NOMINAL_MONTHLY interest rates to ``(effective_annual, effective_monthly)`` decimals."""
    if raw_rate is None or raw_rate <= 0:
        return 0.0, 0.0
    rate_val = float(raw_rate)
    decimal_rate = rate_val / 100.0 if rate_val >= 1.0 else rate_val
    if basis == InterestRateBasis.NOMINAL_MONTHLY:
        monthly = decimal_rate
        annual = (1.0 + monthly) ** 12 - 1.0
        return annual, monthly
    annual = decimal_rate
    monthly = (1.0 + annual) ** (1.0 / 12.0) - 1.0
    return annual, monthly


def _estimate_remaining_periods(
    account: AccountsDTO,
    balance: float,
    monthly_rate: float,
    scheduled_pi: float,
) -> int | None:
    """Return remaining periods from metadata when present, else simulate amortization up to 360 months."""
    if balance <= 0.01:
        return 0
    if account.overall_periods is not None and account.overall_periods > 0:
        return max(0, int(account.overall_periods) - int(account.periods_paid or 0))
    if scheduled_pi <= 0 or scheduled_pi <= balance * monthly_rate:
        return None
    rem = balance
    months = 0
    while rem > 0.01 and months < 360:
        interest = rem * monthly_rate
        rem = rem + interest - min(rem + interest, scheduled_pi)
        months += 1
    return months if rem <= 0.01 else None


def _build_linked_asset_carry(
    account: AccountsDTO,
    monthly_contractual: float,
    accounts_by_id: dict[uuid.UUID, AccountsDTO],
    financing_by_loan: dict[uuid.UUID, AccountFinancingDTO],
    balance_by_account_id: dict[uuid.UUID, float],
) -> dict[str, Any] | None:
    if account.id is None:
        return None
    link = financing_by_loan.get(account.id)
    if link is None:
        return None
    asset = lookup_by_id(accounts_by_id, link.asset_account_id)
    if asset is None:
        return None
    asset_val = (
        float(asset.current_value)
        if asset.current_value is not None
        else float(balance_by_account_id.get(asset.id, asset.initial_value or 0.0) if asset.id else 0.0)
    )
    asset_months = int(asset.months_per_period or 1)
    monthly_earnings = float(asset.periodic_earnings or 0.0) / asset_months
    return {
        "asset_id": str(asset.id),
        "asset_name": asset.name,
        "asset_current_value": round(asset_val, 2),
        "financing_share": round(float(link.financing_share), 4),
        "asset_monthly_earnings": round(monthly_earnings, 2),
        "net_monthly_carry": round(monthly_earnings - monthly_contractual, 2),
    }


def _compute_liquid_context(  # pylint: disable=too-many-arguments
    *,
    accounts: list[AccountsDTO],
    accounts_by_id: dict[uuid.UUID, AccountsDTO],
    selected_currency: str,
    balance_by_account_id: dict[uuid.UUID, float],
    operating_outflows_90d: float,
    total_contractual_payment: float,
    templates: list[TransactionTemplatesDTO],
    categories_by_id: dict[uuid.UUID, CategoriesDTO],
    target_liquidity_months: float,
) -> dict[str, Any]:
    liquid_cash = 0.0
    for acct in accounts:
        if (
            not acct.active
            or acct.closed_at is not None
            or not acct.include_in_balance
            or acct.currency.strip().upper() != selected_currency
            or acct.account_kind not in LIQUID_ACCOUNT_KINDS
        ):
            continue
        if acct.id is not None and acct.id in balance_by_account_id:
            liquid_cash += max(0.0, float(balance_by_account_id[acct.id]))
        else:
            liquid_cash += max(0.0, float(acct.current_value or acct.initial_value or 0.0))

    if operating_outflows_90d > 0:
        baseline_burn = operating_outflows_90d / 3.0
    else:
        recurring_expenses = 0.0
        for tpl in templates:
            if not tpl.active or tpl.due_date is not None:
                continue
            tpl_acct = lookup_by_id(accounts_by_id, tpl.from_account_id)
            if tpl_acct is not None and tpl_acct.currency.strip().upper() != selected_currency:
                continue
            cat = lookup_by_id(categories_by_id, tpl.category_id)
            if cat is not None and cat.category_kind == CategoryKind.INCOME:
                continue
            recurring_expenses += float(tpl.planned_amount)
        baseline_burn = max(total_contractual_payment, recurring_expenses)

    runway = round(liquid_cash / baseline_burn, 2) if baseline_burn > 0 else None
    headroom = max(0.0, liquid_cash - target_liquidity_months * baseline_burn) if baseline_burn > 0 else liquid_cash
    return {
        "liquid_cash_total": round(liquid_cash, 2),
        "baseline_monthly_burn": round(baseline_burn, 2),
        "liquid_runway_months": runway,
        "target_liquidity_months": round(target_liquidity_months, 1),
        "safe_lump_sum_headroom": round(headroom, 2),
    }


def compute_debt_paydown(  # pylint: disable=too-many-arguments,too-many-locals
    *,
    accounts: list[AccountsDTO],
    loan_details_by_id: dict[uuid.UUID, LoanAccountDetailsDTO],
    financing_links: list[AccountFinancingDTO],
    balance_by_account_id: dict[uuid.UUID, float],
    templates: list[TransactionTemplatesDTO],
    categories: list[CategoriesDTO] | None = None,
    operating_outflows_90d: float = 0.0,
    requested_currency: str | None = None,
    include_excluded: bool = False,
    target_liquidity_months: float = 4.0,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Rank active liabilities by effective annual rate and monthly interest drag."""
    today = as_of or datetime.now(timezone.utc).date()
    accounts_by_id = {acct.id: acct for acct in accounts if acct.id is not None}
    categories_by_id = {cat.id: cat for cat in (categories or []) if cat.id is not None}

    active_currencies = [acct.currency for acct in accounts if acct.active and acct.closed_at is None]
    liab_currencies = [
        acct.currency
        for acct in accounts
        if acct.active and acct.closed_at is None and acct.ledger_side == LedgerSide.LIABILITY
    ]
    selected_currency, available_currencies, multi_currency_warning = resolve_currency_scope(
        liab_currencies,
        active_currencies,
        requested_currency,
    )

    financing_by_loan: dict[uuid.UUID, AccountFinancingDTO] = {}
    for link in financing_links:
        if not link.active:
            continue
        existing = financing_by_loan.get(link.loan_account_id)
        if existing is None or link.financing_share > existing.financing_share:
            financing_by_loan[link.loan_account_id] = link

    raw_items: list[dict[str, Any]] = []
    excluded_count = 0
    excluded_balance = 0.0
    excluded_names: list[str] = []

    for acct in accounts:
        if acct.id is None or acct.ledger_side != LedgerSide.LIABILITY:
            continue
        if acct.currency.strip().upper() != selected_currency:
            continue
        loan_detail = loan_details_by_id.get(acct.id)
        is_paid_off = bool(loan_detail and loan_detail.is_paid_off)
        is_excluded = (not acct.active) or (acct.closed_at is not None) or (not acct.include_in_balance) or is_paid_off

        bal = (
            abs(float(acct.current_value))
            if acct.current_value is not None
            else abs(float(balance_by_account_id.get(acct.id, 0.0)))
        )

        if is_excluded:
            if acct.active and acct.closed_at is None:
                excluded_count += 1
                excluded_balance += bal
                excluded_names.append(acct.name)
            continue

        ea, r_m = normalize_interest_rates(acct.interest_rate, acct.interest_rate_basis)
        months_per_period = int(acct.months_per_period or 1)
        monthly_contractual = (float(acct.periodic_payment) / months_per_period) if acct.periodic_payment else 0.0
        monthly_extras = float(loan_detail.insurance_payment + loan_detail.extras_payment) if loan_detail else 0.0
        scheduled_pi = max(0.0, monthly_contractual - monthly_extras)
        monthly_drag = bal * r_m
        annual_drag = bal * ea
        monthly_principal = max(0.0, scheduled_pi - monthly_drag)
        neg_amort = bal > 0.01 and monthly_contractual > 0 and scheduled_pi <= monthly_drag
        remaining = _estimate_remaining_periods(acct, bal, r_m, scheduled_pi)
        payoff_date = add_months(today.replace(day=1), remaining) if remaining is not None else None
        linked_asset = _build_linked_asset_carry(
            acct, monthly_contractual, accounts_by_id, financing_by_loan, balance_by_account_id
        )

        raw_items.append(
            {
                "account_id": str(acct.id),
                "account_name": acct.name,
                "account_kind": acct.account_kind.value.lower(),
                "currency": selected_currency,
                "balance": round(bal, 2),
                "effective_annual_rate_pct": round(ea * 100.0, 4),
                "effective_monthly_rate_pct": round(r_m * 100.0, 4),
                "monthly_interest_drag": round(monthly_drag, 2),
                "annual_interest_drag": round(annual_drag, 2),
                "monthly_contractual_payment": round(monthly_contractual, 2),
                "monthly_extras_payment": round(monthly_extras, 2),
                "monthly_principal_amortization": round(monthly_principal, 2),
                "remaining_periods": remaining,
                "estimated_payoff_date": payoff_date,
                "negative_amortization": neg_amort,
                "linked_asset": linked_asset,
                "_sort_ea": ea,
                "_sort_drag": monthly_drag,
                "_r_m": r_m,
                "_scheduled_pi": scheduled_pi,
            }
        )

    ranked = sorted(
        raw_items,
        key=lambda row: (-row["_sort_ea"], -row["_sort_drag"], -row["balance"], row["account_name"]),
    )
    for idx, row in enumerate(ranked, start=1):
        row["priority_rank"] = idx

    total_debt = sum(row["balance"] for row in ranked)
    total_monthly_drag = sum(row["monthly_interest_drag"] for row in ranked)
    total_annual_drag = sum(row["annual_interest_drag"] for row in ranked)
    total_contractual = sum(row["monthly_contractual_payment"] for row in ranked)
    weighted_ea = round((total_annual_drag / total_debt) * 100.0, 4) if total_debt > 0 else 0.0

    liquidity = _compute_liquid_context(
        accounts=accounts,
        accounts_by_id=accounts_by_id,
        selected_currency=selected_currency,
        balance_by_account_id=balance_by_account_id,
        operating_outflows_90d=operating_outflows_90d,
        total_contractual_payment=total_contractual,
        templates=templates,
        categories_by_id=categories_by_id,
        target_liquidity_months=target_liquidity_months,
    )

    clean_liabilities = [{k: v for k, v in row.items() if not k.startswith("_")} for row in ranked]
    return {
        "currency": selected_currency,
        "available_currencies": available_currencies,
        "multi_currency_warning": multi_currency_warning,
        "summary": {
            "total_debt": round(total_debt, 2),
            "active_liability_count": len(clean_liabilities),
            "total_monthly_interest_drag": round(total_monthly_drag, 2),
            "total_annual_interest_drag": round(total_annual_drag, 2),
            "total_monthly_contractual_payment": round(total_contractual, 2),
            "weighted_average_ea_pct": weighted_ea,
            "highest_rate_account_name": clean_liabilities[0]["account_name"] if clean_liabilities else None,
            "highest_rate_payoff_date": clean_liabilities[0]["estimated_payoff_date"] if clean_liabilities else None,
        },
        "liabilities": clean_liabilities,
        "liquidity_context": liquidity,
        "excluded_liabilities": (
            {
                "count": excluded_count,
                "total_balance": round(excluded_balance, 2),
                "account_names": sorted(excluded_names),
            }
            if include_excluded
            else None
        ),
        "_internal_ranked": ranked,
    }


def _loan_sort_key(loan: _SimLoan, strategy: Literal["avalanche", "snowball"]) -> tuple[float, float, str]:
    if strategy == "snowball":
        return (loan.balance, -loan.effective_annual_rate, loan.name)
    return (-loan.effective_annual_rate, -loan.balance, loan.name)


def _run_schedule(  # pylint: disable=too-many-arguments,too-many-locals
    loans: list[_SimLoan],
    *,
    start_month: date,
    strategy: Literal["avalanche", "snowball"],
    cascade_rollover: bool,
    extra_monthly_prepayment: float,
    lump_sum_prepayment: float,
    lump_sum_month_offset: int,
    periodic_lump_by_month: dict[int, float],
    max_months: int,
) -> tuple[list[dict[str, Any]], int | None, float]:
    """Simulate month-by-month debt amortization with optional extra prepayment rollover."""
    snapshots: list[dict[str, Any]] = []
    total_interest = 0.0
    payoff_month: int | None = 0 if all(loan.balance <= 0.01 for loan in loans) else None
    freed_rollover = 0.0

    for month_idx in range(1, max_months + 1):
        open_loans = [loan for loan in loans if loan.balance > 0.01]
        if not open_loans:
            break

        sim_date = add_months(start_month, month_idx)
        events: list[str] = []
        month_interest = 0.0
        unused_scheduled = 0.0
        prior_freed_rollover = freed_rollover

        for loan in open_loans:
            interest = loan.balance * loan.monthly_rate
            total_interest += interest
            loan.total_interest += interest
            month_interest += interest
            due = min(loan.balance + interest, loan.scheduled_pi)
            if loan.scheduled_pi > due:
                unused_scheduled += loan.scheduled_pi - due
            loan.balance = max(0.0, loan.balance + interest - due)
            if loan.balance <= 0.01:
                loan.balance = 0.0
                if loan.paid_off_month is None:
                    loan.paid_off_month = month_idx
                    freed_rollover += loan.scheduled_pi
                    events.append(f"Paid off: {loan.name}")

        extra_budget = 0.0
        if cascade_rollover:
            lump_here = lump_sum_prepayment if month_idx == lump_sum_month_offset else 0.0
            periodic_here = periodic_lump_by_month.get(sim_date.month, 0.0)
            if lump_here > 0 or periodic_here > 0:
                events.append("Lump sum applied")
            extra_budget = (
                extra_monthly_prepayment + prior_freed_rollover + unused_scheduled + lump_here + periodic_here
            )

        month_extra = 0.0
        if extra_budget > 0.01:
            open_sorted = sorted(
                (loan for loan in loans if loan.balance > 0.01),
                key=lambda loan: _loan_sort_key(loan, strategy),
            )
            for loan in open_sorted:
                if extra_budget <= 0.01:
                    break
                apply_amt = min(loan.balance, extra_budget)
                loan.balance = max(0.0, loan.balance - apply_amt)
                extra_budget -= apply_amt
                month_extra += apply_amt
                if loan.balance <= 0.01:
                    loan.balance = 0.0
                    if loan.paid_off_month is None:
                        loan.paid_off_month = month_idx
                        freed_rollover += loan.scheduled_pi
                        events.append(f"Paid off: {loan.name}")

        total_remaining = sum(loan.balance for loan in loans)
        open_after = sorted(
            (loan for loan in loans if loan.balance > 0.01),
            key=lambda loan: _loan_sort_key(loan, strategy),
        )
        priority_bal = open_after[0].balance if open_after else 0.0
        snapshots.append(
            {
                "month": sim_date.strftime("%Y-%m"),
                "month_offset": month_idx,
                "total_debt": round(total_remaining, 2),
                "priority_loan_balance": round(priority_bal, 2),
                "interest_paid": round(month_interest, 2),
                "extra_applied": round(month_extra, 2),
                "events": events,
            }
        )
        if total_remaining <= 0.01 and payoff_month is None:
            payoff_month = month_idx

    return snapshots, payoff_month, round(total_interest, 2)


def simulate_debt_paydown(  # pylint: disable=too-many-arguments,too-many-locals
    *,
    paydown_report: dict[str, Any],
    strategy: Literal["avalanche", "snowball"] = "avalanche",
    extra_monthly_prepayment: float = 0.0,
    lump_sum_prepayment: float = 0.0,
    lump_sum_month_offset: int = 1,
    periodic_lump_sums: list[dict[str, Any]] | None = None,
    target_liquidity_months: float = 4.0,
    horizon_months: int = 60,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Compare baseline amortization against accelerated avalanche/snowball paydown."""
    today = (as_of or datetime.now(timezone.utc).date()).replace(day=1)
    internal_ranked: list[dict[str, Any]] = paydown_report.get("_internal_ranked", [])

    def _clone_loans() -> list[_SimLoan]:
        return [
            _SimLoan(
                account_id=row["account_id"],
                name=row["account_name"],
                balance=float(row["balance"]),
                monthly_rate=float(row["_r_m"]),
                effective_annual_rate=float(row["_sort_ea"]),
                scheduled_pi=float(row["_scheduled_pi"]),
            )
            for row in internal_ranked
            if float(row["balance"]) > 0.01
        ]

    periodic_map: dict[int, float] = {}
    for entry in periodic_lump_sums or []:
        m = int(entry["month_of_year"])
        periodic_map[m] = periodic_map.get(m, 0.0) + float(entry["amount"])

    sim_cap = max(horizon_months, 360)
    base_loans = _clone_loans()
    accel_loans = _clone_loans()

    base_snaps, base_payoff_m, base_interest = _run_schedule(
        base_loans,
        start_month=today,
        strategy=strategy,
        cascade_rollover=False,
        extra_monthly_prepayment=0.0,
        lump_sum_prepayment=0.0,
        lump_sum_month_offset=1,
        periodic_lump_by_month={},
        max_months=sim_cap,
    )
    accel_snaps, accel_payoff_m, accel_interest = _run_schedule(
        accel_loans,
        start_month=today,
        strategy=strategy,
        cascade_rollover=True,
        extra_monthly_prepayment=extra_monthly_prepayment,
        lump_sum_prepayment=lump_sum_prepayment,
        lump_sum_month_offset=lump_sum_month_offset,
        periodic_lump_by_month=periodic_map,
        max_months=sim_cap,
    )

    months_saved = (
        max(0, base_payoff_m - accel_payoff_m) if base_payoff_m is not None and accel_payoff_m is not None else None
    )
    interest_saved = round(max(0.0, base_interest - accel_interest), 2)

    base_by_id = {loan.account_id: loan for loan in base_loans}
    accel_by_id = {loan.account_id: loan for loan in accel_loans}
    per_liability_impact: list[dict[str, Any]] = []
    for row in internal_ranked:
        aid = row["account_id"]
        if aid not in base_by_id:
            continue
        b_loan = base_by_id[aid]
        a_loan = accel_by_id[aid]
        b_date = add_months(today, b_loan.paid_off_month) if b_loan.paid_off_month is not None else None
        a_date = add_months(today, a_loan.paid_off_month) if a_loan.paid_off_month is not None else None
        per_liability_impact.append(
            {
                "account_id": aid,
                "account_name": row["account_name"],
                "effective_annual_rate_pct": row["effective_annual_rate_pct"],
                "starting_balance": row["balance"],
                "baseline_payoff_date": b_date,
                "accelerated_payoff_date": a_date,
                "months_saved": (
                    max(0, b_loan.paid_off_month - a_loan.paid_off_month)
                    if b_loan.paid_off_month is not None and a_loan.paid_off_month is not None
                    else None
                ),
                "interest_saved": round(max(0.0, b_loan.total_interest - a_loan.total_interest), 2),
            }
        )

    max_len = min(horizon_months, max(len(base_snaps), len(accel_snaps)))
    trajectory: list[dict[str, Any]] = []
    for idx in range(max_len):
        b_snap = base_snaps[idx] if idx < len(base_snaps) else None
        a_snap = accel_snaps[idx] if idx < len(accel_snaps) else None
        month_str = (a_snap or b_snap)["month"]  # type: ignore[index]
        trajectory.append(
            {
                "month": month_str,
                "baseline_total_debt": b_snap["total_debt"] if b_snap else 0.0,
                "accelerated_total_debt": a_snap["total_debt"] if a_snap else 0.0,
                "priority_loan_balance": a_snap["priority_loan_balance"] if a_snap else 0.0,
                "interest_paid": a_snap["interest_paid"] if a_snap else 0.0,
                "extra_applied": a_snap["extra_applied"] if a_snap else 0.0,
                "events": a_snap["events"] if a_snap else [],
            }
        )

    liq_ctx = paydown_report["liquidity_context"]
    liquid_cash = float(liq_ctx["liquid_cash_total"])
    burn = float(liq_ctx["baseline_monthly_burn"])
    post_cash = max(0.0, liquid_cash - lump_sum_prepayment)
    post_runway = round(post_cash / burn, 2) if burn > 0 else None
    safe_headroom = max(0.0, liquid_cash - target_liquidity_months * burn) if burn > 0 else liquid_cash

    if lump_sum_prepayment > liquid_cash:
        guardrail_status = "warning"
        guardrail_msg = (
            f"Lump-sum prepayment ({lump_sum_prepayment:.2f}) exceeds current liquid cash ({liquid_cash:.2f})."
        )
    elif post_runway is not None and post_runway < target_liquidity_months:
        guardrail_status = "warning" if post_runway < max(1.0, target_liquidity_months * 0.5) else "caution"
        guardrail_msg = (
            f"Post-prepayment liquid runway ({post_runway:.1f} mos) falls below your "
            f"{target_liquidity_months:.1f}-month safety target (safe headroom: {safe_headroom:.2f})."
        )
    else:
        guardrail_status = "safe"
        guardrail_msg = "Liquid cash remains above your target runway floor after planned prepayments."

    return {
        "currency": paydown_report["currency"],
        "strategy": strategy,
        "baseline_months_to_payoff": base_payoff_m,
        "accelerated_months_to_payoff": accel_payoff_m,
        "baseline_payoff_date": add_months(today, base_payoff_m) if base_payoff_m is not None else None,
        "accelerated_payoff_date": add_months(today, accel_payoff_m) if accel_payoff_m is not None else None,
        "months_saved": months_saved,
        "baseline_total_interest": base_interest,
        "accelerated_total_interest": accel_interest,
        "total_interest_saved": interest_saved,
        "per_liability_impact": per_liability_impact,
        "monthly_trajectory": trajectory,
        "liquidity_guardrail": {
            "status": guardrail_status,
            "liquid_cash_total": round(liquid_cash, 2),
            "post_lump_sum_cash": round(post_cash, 2),
            "post_lump_sum_runway_months": post_runway,
            "target_liquidity_months": round(target_liquidity_months, 1),
            "safe_lump_sum_headroom": round(safe_headroom, 2),
            "message": guardrail_msg,
        },
    }
