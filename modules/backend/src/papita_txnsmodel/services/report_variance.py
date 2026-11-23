"""Planned-vs-Actual variance and reconciliation alerts (PPT-091 / #184)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

from papita_txnsmodel.access.account_details.dto import CreditCardAccountDetailsDTO
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO, TransactionTemplatesDTO
from papita_txnsmodel.config.transaction_partitions import add_months, month_start
from papita_txnsmodel.model.enums import CashflowBucket, SettlementStatus, TransactionKind, TransactionStatus
from papita_txnsmodel.services.dues import due_in_month
from papita_txnsmodel.services.report_common import (
    BUCKET_META,
    INCOME_BUCKETS,
    INTERNAL_BUCKET,
    OPERATING_OUTFLOW_BUCKETS,
    WATERFALL_BUCKET_ORDER,
    as_uuid,
    bucket_slug,
    classify_template_bucket,
    classify_transaction_bucket,
    parse_timestamp,
    resolve_currency_scope,
)


@dataclass
class _ExpandedOccurrence:
    template_id: uuid.UUID
    template_name: str
    category_id: uuid.UUID | None
    category_name: str
    bucket: str
    due_date: date
    planned_amount: float
    actual_amount: float = 0.0
    linked_count: int = 0


def _iter_months(start_day: date, end_day: date) -> list[tuple[int, int]]:
    """Return inclusive ``(year, month)`` tuples spanning ``[start_day, end_day]``."""
    cursor = month_start(start_day)
    end_anchor = month_start(end_day)
    months: list[tuple[int, int]] = []
    while cursor <= end_anchor:
        months.append((cursor.year, cursor.month))
        cursor = add_months(cursor, 1)
    return months


def _expand_templates(  # pylint: disable=too-many-arguments,too-many-locals
    *,
    templates: list[TransactionTemplatesDTO],
    start_day: date,
    end_day: date,
    selected_currency: str,
    account_id: uuid.UUID | None,
    bucket_filter: str | None,
    accounts_by_id: dict[uuid.UUID, AccountsDTO],
    categories_by_id: dict[uuid.UUID, CategoriesDTO],
) -> list[_ExpandedOccurrence]:
    """Expand active templates into dated occurrences inside ``[start_day, end_day]``."""
    months = _iter_months(start_day, end_day)
    occurrences: list[_ExpandedOccurrence] = []

    for tpl in templates:
        if not tpl.active or tpl.id is None:
            continue
        tpl_acct_id = as_uuid(tpl.from_account_id)
        if account_id is not None and tpl_acct_id != account_id:
            continue
        acct = accounts_by_id.get(tpl_acct_id) if tpl_acct_id else None
        tpl_currency = acct.currency.strip().upper() if acct else selected_currency
        if tpl_currency != selected_currency:
            continue

        bucket = classify_template_bucket(tpl, accounts_by_id, categories_by_id)
        if bucket_filter is not None and bucket != bucket_filter:
            continue

        cat_id = as_uuid(tpl.category_id)
        cat = categories_by_id.get(cat_id) if cat_id else None
        cat_name = cat.name if cat else "Uncategorized"

        if tpl.due_date is not None:
            if start_day <= tpl.due_date <= end_day:
                occurrences.append(
                    _ExpandedOccurrence(
                        template_id=tpl.id,
                        template_name=tpl.name,
                        category_id=cat_id,
                        category_name=cat_name,
                        bucket=bucket,
                        due_date=tpl.due_date,
                        planned_amount=float(tpl.planned_amount),
                    )
                )
            continue

        for year, month in months:
            occ_day = due_in_month(tpl, year=year, month=month)
            if start_day <= occ_day <= end_day:
                occurrences.append(
                    _ExpandedOccurrence(
                        template_id=tpl.id,
                        template_name=tpl.name,
                        category_id=cat_id,
                        category_name=cat_name,
                        bucket=bucket,
                        due_date=occ_day,
                        planned_amount=float(tpl.planned_amount),
                    )
                )
    return occurrences


def _variance_status(planned: float, actual: float, occ_date: date, as_of: date, is_income: bool) -> str:
    if actual <= 0.0:
        return "overdue" if occ_date < as_of else "upcoming"
    if actual < planned * 0.99:
        return "partial"
    if actual <= planned * 1.05:
        return "paid"
    return "exceeded" if is_income else "over_budget"


def _detect_reconciliation_flags(
    *,
    settled: list[TransactionsDTO],
    unlinked_txns: list[tuple[TransactionsDTO, str]],
    occurrences: list[_ExpandedOccurrence],
    categories_by_id: dict[uuid.UUID, CategoriesDTO],
) -> list[dict[str, Any]]:
    """Surface actionable audit alerts (unlinked matches, duplicates, unbucketed categories)."""
    flags: list[dict[str, Any]] = []
    open_occurrences = [occ for occ in occurrences if occ.actual_amount < occ.planned_amount * 0.99]

    for txn, bucket in unlinked_txns:
        txn_day = parse_timestamp(txn.transaction_ts).date()
        txn_cat = as_uuid(txn.category_id)
        amount = float(txn.amount)
        txn_is_income = txn.transaction_kind == TransactionKind.INCOME
        for occ in open_occurrences:
            occ_is_income = occ.bucket in INCOME_BUCKETS
            same_cat = txn_cat is not None and txn_cat == occ.category_id
            if not (same_cat or txn_is_income == occ_is_income):
                continue
            if (
                abs(amount - occ.planned_amount) <= occ.planned_amount * 0.05
                and abs((txn_day - occ.due_date).days) <= 5
            ):
                flags.append(
                    {
                        "code": "unlinked_high_value",
                        "severity": "warning",
                        "message": (
                            f"Unlinked {bucket_slug(bucket)} posting of {amount:.2f} on {txn_day.isoformat()} "
                            f"matches unpaid template '{occ.template_name}' ({occ.planned_amount:.2f})."
                        ),
                        "transaction_id": str(txn.id) if txn.id else None,
                        "template_id": str(occ.template_id),
                        "category_id": str(txn_cat) if txn_cat else None,
                        "amount": round(amount, 2),
                    }
                )
                break

    seen_groups: dict[tuple[float, str, str, str, int, int], list[tuple[TransactionsDTO, date]]] = defaultdict(list)
    for txn in settled:
        txn_day = parse_timestamp(txn.transaction_ts).date()
        key = (
            round(float(txn.amount), 2),
            str(as_uuid(txn.category_id) or ""),
            str(as_uuid(txn.from_account_id) or ""),
            str(as_uuid(txn.to_account_id) or ""),
            txn_day.year,
            txn_day.month,
        )
        seen_groups[key].append((txn, txn_day))

    for group_rows in seen_groups.values():
        if len(group_rows) < 2:
            continue
        ordered = sorted(group_rows, key=lambda pair: pair[1])
        for idx in range(1, len(ordered)):
            prev_txn, prev_day = ordered[idx - 1]
            curr_txn, curr_day = ordered[idx]
            if (curr_day - prev_day).days <= 3:
                flags.append(
                    {
                        "code": "potential_duplicate",
                        "severity": "warning",
                        "message": (
                            f"Potential duplicate posting of {float(curr_txn.amount):.2f} within "
                            f"{(curr_day - prev_day).days} day(s) ({prev_day.isoformat()} & {curr_day.isoformat()})."
                        ),
                        "transaction_id": str(curr_txn.id) if curr_txn.id else None,
                        "template_id": None,
                        "category_id": str(as_uuid(curr_txn.category_id)) if curr_txn.category_id else None,
                        "amount": round(float(curr_txn.amount), 2),
                    }
                )
                break

    seen_unbucketed: set[uuid.UUID] = set()
    for txn in settled:
        cat_id = as_uuid(txn.category_id)
        if cat_id and cat_id not in seen_unbucketed:
            cat = categories_by_id.get(cat_id)
            if cat is not None and cat.cashflow_bucket is None:
                seen_unbucketed.add(cat_id)
                flags.append(
                    {
                        "code": "unbucketed_category",
                        "severity": "info",
                        "message": f"Category '{cat.name}' has no cashflow_bucket assigned; fallback rules applied.",
                        "transaction_id": None,
                        "template_id": None,
                        "category_id": str(cat_id),
                        "amount": None,
                    }
                )

    return flags[:50]


def compute_planned_vs_actual(  # pylint: disable=too-many-arguments,too-many-locals
    *,
    templates: list[TransactionTemplatesDTO],
    transactions: list[TransactionsDTO],
    accounts: list[AccountsDTO],
    categories: list[CategoriesDTO],
    cc_details_by_id: dict[uuid.UUID, CreditCardAccountDetailsDTO],
    start_day: date,
    end_day: date,
    requested_currency: str | None = None,
    account_id: uuid.UUID | None = None,
    cashflow_bucket: CashflowBucket | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Compare expanded planned templates against settled ledger postings."""
    today = as_of or date.today()
    accounts_by_id = {acct.id: acct for acct in accounts if acct.id is not None}
    categories_by_id = {cat.id: cat for cat in categories if cat.id is not None}
    bucket_filter = cashflow_bucket.value if cashflow_bucket is not None else None

    settled_all = [
        txn
        for txn in transactions
        if txn.active
        and txn.status == TransactionStatus.COMPLETED
        and txn.settlement_status != SettlementStatus.IN_TRANSIT
    ]
    active_acct_currencies = [acct.currency for acct in accounts if acct.active and acct.closed_at is None]
    selected_currency, available_currencies, multi_currency_warning = resolve_currency_scope(
        [txn.currency for txn in settled_all],
        active_acct_currencies,
        requested_currency,
    )
    settled = [txn for txn in settled_all if txn.currency.strip().upper() == selected_currency]

    occurrences = _expand_templates(
        templates=templates,
        start_day=start_day,
        end_day=end_day,
        selected_currency=selected_currency,
        account_id=account_id,
        bucket_filter=bucket_filter,
        accounts_by_id=accounts_by_id,
        categories_by_id=categories_by_id,
    )
    occurrence_index: dict[tuple[uuid.UUID, int, int], _ExpandedOccurrence] = {
        (occ.template_id, occ.due_date.year, occ.due_date.month): occ for occ in occurrences
    }

    unlinked_txns: list[tuple[TransactionsDTO, str]] = []
    unplanned_groups: dict[tuple[uuid.UUID | None, str], dict[str, Any]] = {}

    for txn in settled:
        res = classify_transaction_bucket(txn, accounts_by_id, categories_by_id, cc_details_by_id)
        if res.bucket == INTERNAL_BUCKET:
            continue
        if bucket_filter is not None and res.bucket != bucket_filter:
            continue

        txn_day = parse_timestamp(txn.transaction_ts).date()
        tpl_id = as_uuid(txn.template_id)
        matched_occ = occurrence_index.get((tpl_id, txn_day.year, txn_day.month)) if tpl_id else None
        if matched_occ is not None:
            matched_occ.actual_amount += float(txn.amount)
            matched_occ.linked_count += 1
            continue

        if tpl_id is None:
            unlinked_txns.append((txn, res.bucket))

        cat_id = as_uuid(txn.category_id)
        cat = categories_by_id.get(cat_id) if cat_id else None
        cat_name = cat.name if cat else "Uncategorized"
        key = (cat_id, res.bucket)
        entry = unplanned_groups.get(key)
        if entry is None:
            entry = {
                "category_id": str(cat_id) if cat_id else None,
                "category_name": cat_name,
                "bucket": bucket_slug(res.bucket),
                "actual_amount": 0.0,
                "transaction_count": 0,
                "_raw_bucket": res.bucket,
            }
            unplanned_groups[key] = entry
        entry["actual_amount"] += float(txn.amount)
        entry["transaction_count"] += 1

    bucket_planned: dict[str, float] = defaultdict(float)
    bucket_actual: dict[str, float] = defaultdict(float)
    template_items: list[dict[str, Any]] = []

    for occ in sorted(occurrences, key=lambda item: (item.due_date, item.template_name)):
        is_income = occ.bucket in INCOME_BUCKETS
        variance_amt = occ.actual_amount - occ.planned_amount
        variance_pct = round((variance_amt / occ.planned_amount) * 100.0, 2) if occ.planned_amount > 0 else 0.0
        is_favorable = (
            (occ.actual_amount >= occ.planned_amount) if is_income else (occ.actual_amount <= occ.planned_amount)
        )
        status = _variance_status(occ.planned_amount, occ.actual_amount, occ.due_date, today, is_income)

        bucket_planned[occ.bucket] += occ.planned_amount
        bucket_actual[occ.bucket] += occ.actual_amount

        template_items.append(
            {
                "template_id": str(occ.template_id),
                "template_name": occ.template_name,
                "category_id": str(occ.category_id) if occ.category_id else None,
                "category_name": occ.category_name,
                "bucket": bucket_slug(occ.bucket),
                "due_date": occ.due_date,
                "planned_amount": round(occ.planned_amount, 2),
                "actual_amount": round(occ.actual_amount, 2),
                "variance_amount": round(variance_amt, 2),
                "variance_pct": variance_pct,
                "is_favorable": is_favorable,
                "status": status,
                "linked_transaction_count": occ.linked_count,
            }
        )

    unplanned_items: list[dict[str, Any]] = []
    for entry in sorted(unplanned_groups.values(), key=lambda row: (-row["actual_amount"], row["category_name"])):
        raw_bucket = entry.pop("_raw_bucket")
        bucket_actual[raw_bucket] += entry["actual_amount"]
        entry["actual_amount"] = round(entry["actual_amount"], 2)
        entry["status"] = "unplanned"
        unplanned_items.append(entry)

    bucket_rollups: list[dict[str, Any]] = []
    for bucket in WATERFALL_BUCKET_ORDER:
        planned_val = bucket_planned.get(bucket, 0.0)
        actual_val = bucket_actual.get(bucket, 0.0)
        if planned_val == 0.0 and actual_val == 0.0:
            continue
        label, _ = BUCKET_META[bucket]
        is_income = bucket in INCOME_BUCKETS
        var_amt = actual_val - planned_val
        var_pct = round((var_amt / planned_val) * 100.0, 2) if planned_val > 0 else 0.0
        bucket_rollups.append(
            {
                "bucket": bucket_slug(bucket),
                "label": label,
                "planned_amount": round(planned_val, 2),
                "actual_amount": round(actual_val, 2),
                "variance_amount": round(var_amt, 2),
                "variance_pct": var_pct,
                "is_favorable": (actual_val >= planned_val) if is_income else (actual_val <= planned_val),
            }
        )

    planned_income = sum(bucket_planned.get(b, 0.0) for b in INCOME_BUCKETS)
    actual_income = sum(bucket_actual.get(b, 0.0) for b in INCOME_BUCKETS)
    planned_outflows = sum(bucket_planned.get(b, 0.0) for b in OPERATING_OUTFLOW_BUCKETS)
    actual_outflows = sum(bucket_actual.get(b, 0.0) for b in OPERATING_OUTFLOW_BUCKETS)
    planned_fcf = planned_income - planned_outflows
    actual_fcf = actual_income - actual_outflows
    net_fcf_variance = actual_fcf - planned_fcf

    if planned_outflows > 0:
        adherence_pct = round(max(0.0, 100.0 - (abs(actual_outflows - planned_outflows) / planned_outflows * 100.0)), 2)
    else:
        adherence_pct = 100.0 if actual_outflows == 0 else 0.0

    if net_fcf_variance >= 0:
        status_tone = "positive"
    elif abs(net_fcf_variance) <= max(1.0, abs(planned_fcf) * 0.10):
        status_tone = "warning"
    else:
        status_tone = "negative"

    flags = _detect_reconciliation_flags(
        settled=settled,
        unlinked_txns=unlinked_txns,
        occurrences=occurrences,
        categories_by_id=categories_by_id,
    )

    return {
        "currency": selected_currency,
        "available_currencies": available_currencies,
        "multi_currency_warning": multi_currency_warning,
        "summary": {
            "planned_income": round(planned_income, 2),
            "actual_income": round(actual_income, 2),
            "planned_outflows": round(planned_outflows, 2),
            "actual_outflows": round(actual_outflows, 2),
            "planned_operating_fcf": round(planned_fcf, 2),
            "actual_operating_fcf": round(actual_fcf, 2),
            "net_fcf_variance": round(net_fcf_variance, 2),
            "adherence_pct": adherence_pct,
            "reconciliation_flag_count": len(flags),
            "status_tone": status_tone,
        },
        "bucket_rollups": bucket_rollups,
        "template_items": template_items,
        "unplanned_items": unplanned_items,
        "reconciliation_flags": flags,
    }
