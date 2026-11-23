"""Operating Free Cashflow waterfall aggregation (PPT-091 / #184)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from papita_txnsmodel.access.account_details.dto import CreditCardAccountDetailsDTO
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.model.enums import (
    CashflowBucket,
    LedgerSide,
    SettlementStatus,
    TransactionKind,
    TransactionStatus,
)
from papita_txnsmodel.services.report_common import (
    BUCKET_META,
    INCOME_BUCKETS,
    INTERNAL_BUCKET,
    OPERATING_OUTFLOW_BUCKETS,
    WATERFALL_BUCKET_ORDER,
    as_uuid,
    bucket_slug,
    classify_transaction_bucket,
    lookup_by_id,
    parse_timestamp,
    resolve_currency_scope,
)


@dataclass
class _CategoryRollup:
    category_id: str | None
    category_name: str
    amount: float = 0.0
    transaction_count: int = 0


@dataclass
class _WaterfallAccumulator:
    bucket_totals: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    bucket_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    category_rollups: dict[str, dict[str, _CategoryRollup]] = field(default_factory=lambda: defaultdict(dict))
    monthly: dict[str, dict[str, float]] = field(
        default_factory=lambda: defaultdict(
            lambda: {
                "income": 0.0,
                "outflows": 0.0,
                "savings": 0.0,
                "capital_deployments": 0.0,
                "non_operating_inflows": 0.0,
            }
        )
    )
    internal_sweeps_volume: float = 0.0
    unbucketed_category_ids: set[str] = field(default_factory=set)
    unbucketed_amount: float = 0.0
    cc_excluded_count: int = 0
    cc_excluded_amount: float = 0.0
    cc_excluded_accounts: set[str] = field(default_factory=set)


def _compute_in_transit_summary(
    in_transit_rows: list[TransactionsDTO],
    accounts_by_id: dict[uuid.UUID, AccountsDTO],
) -> dict[str, Any]:
    """Summarize active COMPLETED rows still in transit so settled totals stay clean."""
    inflows = 0.0
    outflows = 0.0
    total_volume = 0.0
    for txn in in_transit_rows:
        amount = float(txn.amount)
        total_volume += amount
        if txn.transaction_kind == TransactionKind.INCOME:
            inflows += amount
        elif txn.transaction_kind == TransactionKind.EXPENSE:
            outflows += amount
        else:
            src = lookup_by_id(accounts_by_id, txn.from_account_id)
            dst = lookup_by_id(accounts_by_id, txn.to_account_id)
            if dst and dst.ledger_side == LedgerSide.ASSET and (src is None or src.ledger_side != LedgerSide.ASSET):
                inflows += amount
            elif src and src.ledger_side == LedgerSide.ASSET and (dst is None or dst.ledger_side != LedgerSide.ASSET):
                outflows += amount
    return {
        "count": len(in_transit_rows),
        "inflows": round(inflows, 2),
        "outflows": round(outflows, 2),
        "total_volume": round(total_volume, 2),
    }


def _record_category_rollup(
    acc: _WaterfallAccumulator,
    bucket: str,
    txn: TransactionsDTO,
    categories_by_id: dict[uuid.UUID, CategoriesDTO],
) -> None:
    cat_id = as_uuid(txn.category_id)
    cat = categories_by_id.get(cat_id) if cat_id else None
    key = str(cat_id) if cat_id else "__uncategorized__"
    name = cat.name if cat else "Uncategorized"
    bucket_map = acc.category_rollups[bucket]
    entry = bucket_map.get(key)
    if entry is None:
        entry = _CategoryRollup(category_id=str(cat_id) if cat_id else None, category_name=name)
        bucket_map[key] = entry
    entry.amount += float(txn.amount)
    entry.transaction_count += 1


def _record_monthly_point(acc: _WaterfallAccumulator, bucket: str, txn: TransactionsDTO) -> None:
    month_key = parse_timestamp(txn.transaction_ts).strftime("%Y-%m")
    row = acc.monthly[month_key]
    amount = float(txn.amount)
    if bucket in INCOME_BUCKETS:
        row["income"] += amount
    elif bucket in OPERATING_OUTFLOW_BUCKETS:
        row["outflows"] += amount
    elif bucket == CashflowBucket.SAVINGS.value:
        row["savings"] += amount
    elif bucket == CashflowBucket.CAPITAL_DEPLOYMENT.value:
        row["capital_deployments"] += amount
    elif bucket == CashflowBucket.NON_OPERATING_INFLOW.value:
        row["non_operating_inflows"] += amount


def _build_buckets_payload(acc: _WaterfallAccumulator, total_external_income: float) -> list[dict[str, Any]]:
    buckets: list[dict[str, Any]] = []
    for bucket in WATERFALL_BUCKET_ORDER:
        label, group = BUCKET_META[bucket]
        amount = round(acc.bucket_totals.get(bucket, 0.0), 2)
        share_pct = round((amount / total_external_income) * 100.0, 2) if total_external_income > 0 else 0.0
        sorted_cats = sorted(
            acc.category_rollups.get(bucket, {}).values(),
            key=lambda item: (-item.amount, item.category_name),
        )[:5]
        buckets.append(
            {
                "bucket": bucket_slug(bucket),
                "label": label,
                "group": group,
                "amount": amount,
                "share_of_income_pct": share_pct,
                "transaction_count": acc.bucket_counts.get(bucket, 0),
                "top_categories": [
                    {
                        "category_id": c.category_id,
                        "category_name": c.category_name,
                        "amount": round(c.amount, 2),
                        "transaction_count": c.transaction_count,
                    }
                    for c in sorted_cats
                ],
            }
        )
    return buckets


def _build_monthly_series(acc: _WaterfallAccumulator) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for month_key in sorted(acc.monthly.keys()):
        row = acc.monthly[month_key]
        income = row["income"]
        outflows = row["outflows"]
        fcf = income - outflows
        margin = round((fcf / income) * 100.0, 2) if income > 0 else 0.0
        series.append(
            {
                "month": month_key,
                "total_external_income": round(income, 2),
                "total_operating_outflows": round(outflows, 2),
                "operating_free_cashflow": round(fcf, 2),
                "organic_fcf_margin_pct": margin,
                "savings": round(row["savings"], 2),
                "capital_deployments": round(row["capital_deployments"], 2),
                "non_operating_inflows": round(row["non_operating_inflows"], 2),
            }
        )
    return series


def compute_operating_cashflow(  # pylint: disable=too-many-arguments,too-many-locals
    *,
    transactions: list[TransactionsDTO],
    accounts: list[AccountsDTO],
    categories: list[CategoriesDTO],
    cc_details_by_id: dict[uuid.UUID, CreditCardAccountDetailsDTO],
    requested_currency: str | None = None,
    include_monthly_series: bool = False,
) -> dict[str, Any]:
    """Compute the Operating Free Cashflow waterfall payload from owner-scoped entities."""
    accounts_by_id = {acct.id: acct for acct in accounts if acct.id is not None}
    categories_by_id = {cat.id: cat for cat in categories if cat.id is not None}

    completed = [txn for txn in transactions if txn.active and txn.status == TransactionStatus.COMPLETED]
    settled_all = [txn for txn in completed if txn.settlement_status != SettlementStatus.IN_TRANSIT]
    in_transit_all = [txn for txn in completed if txn.settlement_status == SettlementStatus.IN_TRANSIT]

    active_acct_currencies = [acct.currency for acct in accounts if acct.active and acct.closed_at is None]
    selected_currency, available_currencies, multi_currency_warning = resolve_currency_scope(
        [txn.currency for txn in settled_all],
        active_acct_currencies,
        requested_currency,
    )

    settled = [txn for txn in settled_all if txn.currency.strip().upper() == selected_currency]
    in_transit = [txn for txn in in_transit_all if txn.currency.strip().upper() == selected_currency]

    acc = _WaterfallAccumulator()
    for txn in settled:
        result = classify_transaction_bucket(txn, accounts_by_id, categories_by_id, cc_details_by_id)
        amount = float(txn.amount)
        if result.diagnostic == "unbucketed_category":
            cat_uuid = as_uuid(txn.category_id)
            acc.unbucketed_category_ids.add(str(cat_uuid) if cat_uuid else "__uncategorized__")
            acc.unbucketed_amount += amount
        elif result.diagnostic == "cashflow_only_cc_itemized_expense":
            acc.cc_excluded_count += 1
            acc.cc_excluded_amount += amount
            src = lookup_by_id(accounts_by_id, txn.from_account_id)
            if src:
                acc.cc_excluded_accounts.add(src.name)

        if result.bucket == INTERNAL_BUCKET:
            if txn.transaction_kind == TransactionKind.TRANSFER:
                acc.internal_sweeps_volume += amount
            continue

        acc.bucket_totals[result.bucket] += amount
        acc.bucket_counts[result.bucket] += 1
        _record_category_rollup(acc, result.bucket, txn, categories_by_id)
        if include_monthly_series:
            _record_monthly_point(acc, result.bucket, txn)

    income_fixed = acc.bucket_totals[CashflowBucket.INCOME_FIXED.value]
    income_variable = acc.bucket_totals[CashflowBucket.INCOME_VARIABLE.value]
    total_external_income = income_fixed + income_variable

    loans = acc.bucket_totals[CashflowBucket.LOAN_PAYMENT.value]
    fixed_expenses = acc.bucket_totals[CashflowBucket.FIXED_EXPENSE.value]
    variable_expenses = acc.bucket_totals[CashflowBucket.VARIABLE_EXPENSE.value]
    unexpected_expenses = acc.bucket_totals[CashflowBucket.UNEXPECTED_EXPENSE.value]
    total_operating_outflows = loans + fixed_expenses + variable_expenses + unexpected_expenses

    operating_fcf = total_external_income - total_operating_outflows
    margin_pct = round((operating_fcf / total_external_income) * 100.0, 2) if total_external_income > 0 else 0.0
    debt_ratio_pct = round((loans / total_external_income) * 100.0, 2) if total_external_income > 0 else 0.0

    savings = acc.bucket_totals[CashflowBucket.SAVINGS.value]
    capital_deployments = acc.bucket_totals[CashflowBucket.CAPITAL_DEPLOYMENT.value]
    non_operating_inflows = acc.bucket_totals[CashflowBucket.NON_OPERATING_INFLOW.value]
    net_allocated_surplus = operating_fcf - savings - capital_deployments
    net_ledger_cashflow = net_allocated_surplus + non_operating_inflows

    if operating_fcf > 0 and margin_pct >= 15.0:
        status_tone = "positive"
    elif operating_fcf >= 0:
        status_tone = "warning"
    else:
        status_tone = "negative"

    return {
        "currency": selected_currency,
        "available_currencies": available_currencies,
        "multi_currency_warning": multi_currency_warning,
        "waterfall": {
            "income_fixed": round(income_fixed, 2),
            "income_variable": round(income_variable, 2),
            "total_external_income": round(total_external_income, 2),
            "loans": round(loans, 2),
            "fixed_expenses": round(fixed_expenses, 2),
            "variable_expenses": round(variable_expenses, 2),
            "unexpected_expenses": round(unexpected_expenses, 2),
            "total_operating_outflows": round(total_operating_outflows, 2),
            "operating_free_cashflow": round(operating_fcf, 2),
            "organic_fcf_margin_pct": margin_pct,
            "debt_service_to_income_pct": debt_ratio_pct,
            "savings": round(savings, 2),
            "capital_deployments": round(capital_deployments, 2),
            "net_allocated_surplus": round(net_allocated_surplus, 2),
            "non_operating_inflows": round(non_operating_inflows, 2),
            "net_ledger_cashflow": round(net_ledger_cashflow, 2),
            "internal_sweeps_volume": round(acc.internal_sweeps_volume, 2),
            "status_tone": status_tone,
        },
        "buckets": _build_buckets_payload(acc, total_external_income),
        "in_transit": _compute_in_transit_summary(in_transit, accounts_by_id),
        "monthly_series": _build_monthly_series(acc) if include_monthly_series else [],
        "diagnostics": {
            "unbucketed_category_count": len(acc.unbucketed_category_ids),
            "unbucketed_amount": round(acc.unbucketed_amount, 2),
            "cashflow_only_cc_excluded_count": acc.cc_excluded_count,
            "cashflow_only_cc_excluded_amount": round(acc.cc_excluded_amount, 2),
            "cashflow_only_cc_account_names": sorted(acc.cc_excluded_accounts),
        },
    }
