"""Shared classification, DTO hydration, and currency scoping helpers for reports."""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, TypeVar

import pandas as pd

from papita_txnsmodel.access.account_details.dto import CreditCardAccountDetailsDTO
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO, TransactionTemplatesDTO
from papita_txnsmodel.model.enums import AccountKind, CashflowBucket, CategoryKind, LedgerSide, TransactionKind
from papita_txnsmodel.utils.datautils import mapping_without_missing

DTOT = TypeVar("DTOT", bound=TableDTO)
MappedT = TypeVar("MappedT")

INTERNAL_BUCKET = "NON_OPERATING_INTERNAL"

INCOME_BUCKETS: frozenset[str] = frozenset(
    {
        CashflowBucket.INCOME_FIXED.value,
        CashflowBucket.INCOME_VARIABLE.value,
    }
)
OPERATING_OUTFLOW_BUCKETS: frozenset[str] = frozenset(
    {
        CashflowBucket.LOAN_PAYMENT.value,
        CashflowBucket.FIXED_EXPENSE.value,
        CashflowBucket.VARIABLE_EXPENSE.value,
        CashflowBucket.UNEXPECTED_EXPENSE.value,
    }
)
ALLOCATION_BUCKETS: frozenset[str] = frozenset(
    {
        CashflowBucket.SAVINGS.value,
        CashflowBucket.CAPITAL_DEPLOYMENT.value,
    }
)
WATERFALL_BUCKET_ORDER: tuple[str, ...] = (
    CashflowBucket.INCOME_FIXED.value,
    CashflowBucket.INCOME_VARIABLE.value,
    CashflowBucket.LOAN_PAYMENT.value,
    CashflowBucket.FIXED_EXPENSE.value,
    CashflowBucket.VARIABLE_EXPENSE.value,
    CashflowBucket.UNEXPECTED_EXPENSE.value,
    CashflowBucket.SAVINGS.value,
    CashflowBucket.CAPITAL_DEPLOYMENT.value,
    CashflowBucket.NON_OPERATING_INFLOW.value,
)
BUCKET_META: dict[str, tuple[str, str]] = {
    CashflowBucket.INCOME_FIXED.value: ("Fixed Income", "income"),
    CashflowBucket.INCOME_VARIABLE.value: ("Variable Income", "income"),
    CashflowBucket.LOAN_PAYMENT.value: ("Loans & Debt Service", "operating_outflow"),
    CashflowBucket.FIXED_EXPENSE.value: ("Fixed Expenses", "operating_outflow"),
    CashflowBucket.VARIABLE_EXPENSE.value: ("Variable Expenses", "operating_outflow"),
    CashflowBucket.UNEXPECTED_EXPENSE.value: ("Unexpected Expenses", "operating_outflow"),
    CashflowBucket.SAVINGS.value: ("Savings", "allocation"),
    CashflowBucket.CAPITAL_DEPLOYMENT.value: ("Capital Deployments", "allocation"),
    CashflowBucket.NON_OPERATING_INFLOW.value: ("Non-Operating Inflows", "non_operating"),
}
LIQUID_ACCOUNT_KINDS: frozenset[AccountKind] = frozenset({AccountKind.CASH, AccountKind.CHECKING, AccountKind.SAVINGS})


@dataclass(frozen=True)
class ClassificationResult:
    """Result of mapping a ledger transaction into a waterfall bucket."""

    bucket: str
    diagnostic: str | None = None


def as_uuid(value: Any) -> uuid.UUID | None:
    """Coerce a UUID, DTO, or string into a ``uuid.UUID`` when valid."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, TableDTO):
        return value.id
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return uuid.UUID(stripped)
        except ValueError:
            return None
    return None


def lookup_by_id(mapping: dict[uuid.UUID, MappedT], raw_id: Any) -> MappedT | None:
    """Safely coerce a UUID/DTO/string reference and look it up in a UUID-keyed map."""
    uid = as_uuid(raw_id)
    return mapping.get(uid) if uid is not None else None


def dtos_from_frame(frame: pd.DataFrame | None, dto_type: type[DTOT]) -> list[DTOT]:
    """Hydrate DTO instances from DAO-shaped, standardized, or empty DataFrames."""
    if frame is None or getattr(frame, "empty", True):
        return []
    dao_type = dto_type.__dao_type__
    if len(frame.columns) == 1 and isinstance(frame.iloc[0, 0], dao_type):
        return [dto_type.from_dao(row) for row in frame.iloc[:, 0].tolist()]
    results: list[DTOT] = []
    for raw_row in frame.to_dict(orient="records"):
        clean = mapping_without_missing(raw_row)
        results.append(dto_type.model_validate(clean))
    return results


def parse_timestamp(value: Any) -> datetime:
    """Normalize a transaction timestamp into a timezone-aware UTC datetime."""
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
    parsed = pd.to_datetime(value, utc=True)
    return parsed.to_pydatetime()


def resolve_currency_scope(
    tx_currencies: Sequence[str],
    account_currencies: Sequence[str],
    requested_currency: str | None,
) -> tuple[str, list[str], bool]:
    """Choose a single reporting currency and signal when multiple currencies exist.

    Never silently sums mixed currencies prior to FX conversion (#262).
    """
    norm_tx = [c.strip().upper() for c in tx_currencies if c and c.strip()]
    norm_acct = [c.strip().upper() for c in account_currencies if c and c.strip()]
    available = sorted(set(norm_tx) | set(norm_acct))

    if requested_currency is not None and requested_currency.strip():
        selected = requested_currency.strip().upper()
        warning = len(available) > 1 or (len(available) == 1 and selected not in available)
        return selected, available, warning

    if norm_tx:
        counts = Counter(norm_tx)
        selected = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    elif norm_acct:
        counts = Counter(norm_acct)
        selected = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    else:
        selected = "USD"

    return selected, available, len(available) > 1


def _classify_transfer(
    txn: TransactionsDTO,
    accounts_by_id: dict[uuid.UUID, AccountsDTO],
    category: CategoriesDTO | None,
    cc_details_by_id: dict[uuid.UUID, CreditCardAccountDetailsDTO],
) -> ClassificationResult:
    """Classify a TRANSFER transaction using account ledger sides and explicit flags."""
    src = lookup_by_id(accounts_by_id, txn.from_account_id)
    dst = lookup_by_id(accounts_by_id, txn.to_account_id)

    if src and dst and src.ledger_side == LedgerSide.LIABILITY and dst.ledger_side == LedgerSide.ASSET:
        return ClassificationResult(bucket=CashflowBucket.NON_OPERATING_INFLOW.value)

    if category is not None and category.cashflow_bucket is not None:
        return ClassificationResult(bucket=category.cashflow_bucket.value)

    if src and dst and src.ledger_side == LedgerSide.ASSET and dst.ledger_side == LedgerSide.LIABILITY:
        if dst.account_kind == AccountKind.CREDIT_CARD:
            cc_detail = cc_details_by_id.get(dst.id) if dst.id else None
            if cc_detail is not None and bool(cc_detail.cashflow_only):
                return ClassificationResult(bucket=CashflowBucket.VARIABLE_EXPENSE.value)
            return ClassificationResult(bucket=INTERNAL_BUCKET)
        return ClassificationResult(bucket=CashflowBucket.LOAN_PAYMENT.value)

    if src and dst and src.ledger_side == LedgerSide.ASSET and dst.ledger_side == LedgerSide.ASSET:
        if dst.account_kind == AccountKind.SAVINGS and src.account_kind != AccountKind.SAVINGS:
            return ClassificationResult(bucket=CashflowBucket.SAVINGS.value)
        if dst.account_kind in {AccountKind.INVESTMENT_BROKERAGE, AccountKind.REAL_ESTATE}:
            return ClassificationResult(bucket=CashflowBucket.CAPITAL_DEPLOYMENT.value)
        if src.account_kind == AccountKind.OTHER_ASSET and dst.account_kind in LIQUID_ACCOUNT_KINDS:
            return ClassificationResult(bucket=CashflowBucket.NON_OPERATING_INFLOW.value)
        return ClassificationResult(bucket=INTERNAL_BUCKET)

    return ClassificationResult(bucket=INTERNAL_BUCKET)


def classify_transaction_bucket(
    txn: TransactionsDTO,
    accounts_by_id: dict[uuid.UUID, AccountsDTO],
    categories_by_id: dict[uuid.UUID, CategoriesDTO],
    cc_details_by_id: dict[uuid.UUID, CreditCardAccountDetailsDTO],
) -> ClassificationResult:
    """Classify a settled ledger transaction into a waterfall bucket deterministically."""
    cat_id = as_uuid(txn.category_id)
    category = categories_by_id.get(cat_id) if cat_id else None

    if txn.transaction_kind == TransactionKind.TRANSFER:
        return _classify_transfer(txn, accounts_by_id, category, cc_details_by_id)

    if txn.transaction_kind == TransactionKind.EXPENSE:
        src_id = as_uuid(txn.from_account_id)
        src = accounts_by_id.get(src_id) if src_id else None
        if src and src.account_kind == AccountKind.CREDIT_CARD and src.id:
            cc_detail = cc_details_by_id.get(src.id)
            if cc_detail is not None and bool(cc_detail.cashflow_only):
                return ClassificationResult(
                    bucket=INTERNAL_BUCKET,
                    diagnostic="cashflow_only_cc_itemized_expense",
                )
        if category is not None and category.cashflow_bucket is not None:
            return ClassificationResult(bucket=category.cashflow_bucket.value)
        lower_tags = {tag.strip().lower() for tag in (txn.tags or []) if isinstance(tag, str)}
        if txn.template_id is not None:
            return ClassificationResult(bucket=CashflowBucket.FIXED_EXPENSE.value, diagnostic="unbucketed_category")
        if "unexpected" in lower_tags:
            return ClassificationResult(
                bucket=CashflowBucket.UNEXPECTED_EXPENSE.value,
                diagnostic="unbucketed_category",
            )
        return ClassificationResult(bucket=CashflowBucket.VARIABLE_EXPENSE.value, diagnostic="unbucketed_category")

    # INCOME
    if category is not None and category.cashflow_bucket is not None:
        return ClassificationResult(bucket=category.cashflow_bucket.value)
    default_income = (
        CashflowBucket.INCOME_FIXED.value if txn.template_id is not None else CashflowBucket.INCOME_VARIABLE.value
    )
    return ClassificationResult(bucket=default_income, diagnostic="unbucketed_category")


def classify_template_bucket(
    template: TransactionTemplatesDTO,
    accounts_by_id: dict[uuid.UUID, AccountsDTO],
    categories_by_id: dict[uuid.UUID, CategoriesDTO],
) -> str:
    """Determine the waterfall bucket slug for a planned transaction template."""
    cat_id = as_uuid(template.category_id)
    category = categories_by_id.get(cat_id) if cat_id else None
    if category is not None and category.cashflow_bucket is not None:
        return category.cashflow_bucket.value
    if category is not None and category.category_kind == CategoryKind.INCOME:
        return CashflowBucket.INCOME_FIXED.value
    acct_id = as_uuid(template.from_account_id)
    acct = accounts_by_id.get(acct_id) if acct_id else None
    if acct and acct.ledger_side == LedgerSide.LIABILITY and acct.account_kind != AccountKind.CREDIT_CARD:
        return CashflowBucket.LOAN_PAYMENT.value
    return CashflowBucket.FIXED_EXPENSE.value


def bucket_slug(bucket_value: str) -> str:
    """Convert an internal bucket enum value to a lowercase API slug."""
    return bucket_value.lower()
