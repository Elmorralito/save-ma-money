"""Financial health scorecard calculation (PPT-088 / #181)."""

from __future__ import annotations

import uuid
from typing import Any

from papita_txnsmodel.access.account_details.dto import LoanAccountDetailsDTO
from papita_txnsmodel.access.account_financing.dto import AccountFinancingDTO
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.model.enums import LedgerSide
from papita_txnsmodel.services.report_common import LIQUID_ACCOUNT_KINDS, lookup_by_id, resolve_currency_scope


def _resolve_asset_value(account: AccountsDTO, balance_by_account_id: dict[uuid.UUID, float]) -> float:
    """Resolve balance-sheet value for an active included asset account."""
    if account.account_kind in LIQUID_ACCOUNT_KINDS:
        if account.id is not None and account.id in balance_by_account_id:
            return float(balance_by_account_id[account.id])
        if account.current_value is not None:
            return float(account.current_value)
        return float(account.initial_value or 0.0)

    if account.current_value is not None:
        return float(account.current_value)
    if account.id is not None and account.id in balance_by_account_id:
        return float(balance_by_account_id[account.id])
    return float(account.initial_value or 0.0)


def _resolve_liability_value(account: AccountsDTO, balance_by_account_id: dict[uuid.UUID, float]) -> float:
    """Resolve positive balance-sheet principal for an active included liability account."""
    if account.current_value is not None:
        return abs(float(account.current_value))
    if account.id is not None and account.id in balance_by_account_id:
        return abs(float(balance_by_account_id[account.id]))
    return abs(float(account.initial_value or 0.0))


def _compute_margin_ltv(
    *,
    financing_links: list[AccountFinancingDTO],
    accounts_by_id: dict[uuid.UUID, AccountsDTO],
    asset_values_by_id: dict[uuid.UUID, float],
    liability_values_by_id: dict[uuid.UUID, float],
) -> float | None:
    """Compute collateralized Margin LTV percentage across active financing links."""
    linked_asset_ids: set[uuid.UUID] = set()
    linked_loan_ids: set[uuid.UUID] = set()
    for link in financing_links:
        if not link.active:
            continue
        asset_acct = lookup_by_id(accounts_by_id, link.asset_account_id)
        loan_acct = lookup_by_id(accounts_by_id, link.loan_account_id)
        if asset_acct is None or loan_acct is None or asset_acct.id is None or loan_acct.id is None:
            continue
        if asset_acct.id not in asset_values_by_id or loan_acct.id not in liability_values_by_id:
            continue
        linked_asset_ids.add(asset_acct.id)
        linked_loan_ids.add(loan_acct.id)

    collateral_value = sum(asset_values_by_id[aid] for aid in linked_asset_ids)
    collateralized_debt = sum(liability_values_by_id[lid] for lid in linked_loan_ids)
    return round((collateralized_debt / collateral_value) * 100.0, 2) if collateral_value > 0 else None


def compute_financial_health(  # pylint: disable=too-many-arguments,too-many-locals
    *,
    accounts: list[AccountsDTO],
    loan_details_by_id: dict[uuid.UUID, LoanAccountDetailsDTO],
    financing_links: list[AccountFinancingDTO],
    balance_by_account_id: dict[uuid.UUID, float],
    debt_payload: dict[str, Any],
    requested_currency: str | None = None,
) -> dict[str, Any]:
    """Compute API-driven Financial Health Scorecard metrics from active included accounts.

    Args:
        accounts: Owner-scoped accounts (active and inactive).
        loan_details_by_id: Loan metadata keyed by account UUID.
        financing_links: Active/inactive collateral financing links between assets and liabilities.
        balance_by_account_id: Reconciled ledger balances keyed by account UUID.
        debt_payload: Output of ``compute_debt_paydown`` for the same currency scope.
        requested_currency: Optional ISO currency code filter.

    Returns:
        Dictionary matching ``FinancialHealthReportResponse``.
    """
    active_included = [acct for acct in accounts if acct.active and acct.closed_at is None and acct.include_in_balance]
    active_all = [acct for acct in accounts if acct.active and acct.closed_at is None]
    selected_currency, available_currencies, multi_currency_warning = resolve_currency_scope(
        [acct.currency for acct in active_included],
        [acct.currency for acct in active_all],
        requested_currency,
    )

    accounts_by_id: dict[uuid.UUID, AccountsDTO] = {acct.id: acct for acct in accounts if acct.id is not None}
    asset_values_by_id: dict[uuid.UUID, float] = {}
    liability_values_by_id: dict[uuid.UUID, float] = {}
    total_assets = 0.0
    total_liabilities = 0.0
    included_asset_count = 0
    included_liability_count = 0
    excluded_account_count = 0

    for acct in accounts:
        if acct.id is None or not acct.active or acct.closed_at is not None:
            continue
        if acct.currency.strip().upper() != selected_currency:
            continue
        if not acct.include_in_balance:
            excluded_account_count += 1
            continue

        if acct.ledger_side == LedgerSide.ASSET:
            val = _resolve_asset_value(acct, balance_by_account_id)
            asset_values_by_id[acct.id] = val
            total_assets += val
            included_asset_count += 1
        elif acct.ledger_side == LedgerSide.LIABILITY:
            loan_detail = loan_details_by_id.get(acct.id)
            if loan_detail and loan_detail.is_paid_off:
                excluded_account_count += 1
                continue
            val = _resolve_liability_value(acct, balance_by_account_id)
            liability_values_by_id[acct.id] = val
            total_liabilities += val
            included_liability_count += 1

    reconciled_net_worth = round(total_assets - total_liabilities, 2)
    debt_to_asset_ratio_pct = round((total_liabilities / total_assets) * 100.0, 2) if total_assets > 0 else None
    margin_ltv_pct = _compute_margin_ltv(
        financing_links=financing_links,
        accounts_by_id=accounts_by_id,
        asset_values_by_id=asset_values_by_id,
        liability_values_by_id=liability_values_by_id,
    )

    debt_summary = debt_payload.get("summary", {})
    liquidity = debt_payload.get("liquidity_context", {})

    return {
        "currency": selected_currency,
        "available_currencies": available_currencies,
        "multi_currency_warning": multi_currency_warning,
        "scorecard": {
            "total_assets": round(total_assets, 2),
            "total_liabilities": round(total_liabilities, 2),
            "reconciled_net_worth": reconciled_net_worth,
            "liquid_cash_total": float(liquidity.get("liquid_cash_total", 0.0)),
            "baseline_monthly_burn": float(liquidity.get("baseline_monthly_burn", 0.0)),
            "liquid_runway_months": liquidity.get("liquid_runway_months"),
            "target_liquidity_months": float(liquidity.get("target_liquidity_months", 4.0)),
            "monthly_debt_service": float(debt_summary.get("total_monthly_contractual_payment", 0.0)),
            "total_monthly_interest_drag": float(debt_summary.get("total_monthly_interest_drag", 0.0)),
            "debt_to_asset_ratio_pct": debt_to_asset_ratio_pct,
            "margin_ltv_pct": margin_ltv_pct,
            "included_asset_count": included_asset_count,
            "included_liability_count": included_liability_count,
            "excluded_account_count": excluded_account_count,
        },
    }
