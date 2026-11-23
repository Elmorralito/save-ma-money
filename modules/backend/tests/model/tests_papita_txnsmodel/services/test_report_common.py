"""Unit tests for shared report classification, hydration, and currency scoping helpers."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pandas as pd

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO, TransactionTemplatesDTO
from papita_txnsmodel.model.categories import Categories
from papita_txnsmodel.model.enums import AccountKind, CashflowBucket, CategoryKind, LedgerSide, TransactionKind
from papita_txnsmodel.services.report_common import (
    INTERNAL_BUCKET,
    as_uuid,
    classify_template_bucket,
    classify_transaction_bucket,
    dtos_from_frame,
    parse_timestamp,
    resolve_currency_scope,
)


def test_as_uuid_variants() -> None:
    """Accept UUID, TableDTO, padded UUID str, and reject invalid/empty values."""
    uid = uuid.uuid4()
    dto = AccountsDTO(
        id=uid,
        owner_id=uuid.uuid4(),
        name="Checking",
        account_kind=AccountKind.CHECKING,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
    )
    assert as_uuid(None) is None
    assert as_uuid(uid) == uid
    assert as_uuid(dto) == uid
    assert as_uuid(f"  {uid}  ") == uid
    assert as_uuid("   ") is None
    assert as_uuid("not-a-uuid") is None
    assert as_uuid(42) is None


def test_dtos_from_frame_and_parse_timestamp() -> None:
    """Hydrate empty frames, DAO single-column frames, dicts, and normalize timestamps."""
    assert dtos_from_frame(None, CategoriesDTO) == []
    assert dtos_from_frame(pd.DataFrame(), CategoriesDTO) == []

    cat_id = uuid.uuid4()
    cat_dao = Categories(
        id=cat_id,
        name="Salary",
        category_kind=CategoryKind.INCOME,
        cashflow_bucket=CashflowBucket.INCOME_FIXED,
        description="",
        tags=[],
    )
    from_dao_frame = dtos_from_frame(pd.DataFrame({"dao": [cat_dao]}), CategoriesDTO)
    assert len(from_dao_frame) == 1
    assert from_dao_frame[0].id == cat_id

    dict_frame = pd.DataFrame([from_dao_frame[0].model_dump(mode="python")])
    from_dict_frame = dtos_from_frame(dict_frame, CategoriesDTO)
    assert len(from_dict_frame) == 1
    assert from_dict_frame[0].cashflow_bucket == CashflowBucket.INCOME_FIXED

    aware = datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc)
    naive = datetime(2026, 4, 1, 8, 0)
    assert parse_timestamp(aware) == aware
    assert parse_timestamp(naive) == aware
    assert parse_timestamp(date(2026, 4, 1)) == datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc)
    assert parse_timestamp("2026-04-01T08:00:00Z") == aware


def test_resolve_currency_scope_branches() -> None:
    """Cover account-currency fallback, empty default USD, and requested currency warnings."""
    assert resolve_currency_scope([], ["EUR", "EUR", "USD"], None) == ("EUR", ["EUR", "USD"], True)
    assert resolve_currency_scope([], [], None) == ("USD", [], False)
    assert resolve_currency_scope(["USD"], ["USD"], "usd") == ("USD", ["USD"], False)
    assert resolve_currency_scope(["USD"], ["USD"], "COP") == ("COP", ["USD"], True)


def test_transaction_and_template_classification_fallbacks() -> None:
    """Exercise transfer category override, missing legs, unbucketed defaults, and templates."""
    owner_id = uuid.uuid4()
    checking = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Checking",
        account_kind=AccountKind.CHECKING,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
    )
    savings = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Savings",
        account_kind=AccountKind.SAVINGS,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
    )
    loan_acct = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Car Loan",
        account_kind=AccountKind.LOAN_MORTGAGE,
        ledger_side=LedgerSide.LIABILITY,
        currency="USD",
    )
    accounts_by_id = {checking.id: checking, savings.id: savings, loan_acct.id: loan_acct}

    cat_override = CategoriesDTO(
        id=uuid.uuid4(),
        name="Override",
        category_kind=CategoryKind.EXPENSE,
        cashflow_bucket=CashflowBucket.CAPITAL_DEPLOYMENT,
    )
    cat_unbucketed_exp = CategoriesDTO(
        id=uuid.uuid4(),
        name="Misc",
        category_kind=CategoryKind.EXPENSE,
        cashflow_bucket=None,
    )
    cat_unbucketed_inc = CategoriesDTO(
        id=uuid.uuid4(),
        name="Bonus",
        category_kind=CategoryKind.INCOME,
        cashflow_bucket=None,
    )
    cats_by_id = {
        cat_override.id: cat_override,
        cat_unbucketed_exp.id: cat_unbucketed_exp,
        cat_unbucketed_inc.id: cat_unbucketed_inc,
    }
    ts = datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc)

    # Transfer with explicit category bucket override
    xfer_cat = TransactionsDTO(
        owner_id=owner_id,
        transaction_kind=TransactionKind.TRANSFER,
        amount=300.0,
        currency="USD",
        transaction_ts=ts,
        from_account_id=checking.id,
        to_account_id=savings.id,
        category_id=cat_override.id,
    )
    assert classify_transaction_bucket(xfer_cat, accounts_by_id, cats_by_id, {}).bucket == "CAPITAL_DEPLOYMENT"

    # Transfer missing legs falls back to INTERNAL_BUCKET
    xfer_orphan = TransactionsDTO(
        owner_id=owner_id,
        transaction_kind=TransactionKind.TRANSFER,
        amount=50.0,
        currency="USD",
        transaction_ts=ts,
        from_account_id=checking.id,
        to_account_id=None,
    )
    assert classify_transaction_bucket(xfer_orphan, accounts_by_id, cats_by_id, {}).bucket == INTERNAL_BUCKET

    # Templated unbucketed expense -> FIXED_EXPENSE with diagnostic
    exp_templated = TransactionsDTO(
        owner_id=owner_id,
        transaction_kind=TransactionKind.EXPENSE,
        amount=100.0,
        currency="USD",
        transaction_ts=ts,
        from_account_id=checking.id,
        category_id=cat_unbucketed_exp.id,
        template_id=uuid.uuid4(),
    )
    res_fixed = classify_transaction_bucket(exp_templated, accounts_by_id, cats_by_id, {})
    assert res_fixed.bucket == CashflowBucket.FIXED_EXPENSE.value
    assert res_fixed.diagnostic == "unbucketed_category"

    # Unexpected tag unbucketed expense -> UNEXPECTED_EXPENSE
    exp_unexpected = TransactionsDTO(
        owner_id=owner_id,
        transaction_kind=TransactionKind.EXPENSE,
        amount=75.0,
        currency="USD",
        transaction_ts=ts,
        from_account_id=checking.id,
        category_id=cat_unbucketed_exp.id,
        tags=["Unexpected"],
    )
    res_unexp = classify_transaction_bucket(exp_unexpected, accounts_by_id, cats_by_id, {})
    assert res_unexp.bucket == CashflowBucket.UNEXPECTED_EXPENSE.value
    assert res_unexp.diagnostic == "unbucketed_category"

    # Unbucketed income (templated -> INCOME_FIXED, untemplated -> INCOME_VARIABLE)
    inc_templated = TransactionsDTO(
        owner_id=owner_id,
        transaction_kind=TransactionKind.INCOME,
        amount=1000.0,
        currency="USD",
        transaction_ts=ts,
        to_account_id=checking.id,
        category_id=cat_unbucketed_inc.id,
        template_id=uuid.uuid4(),
    )
    inc_adhoc = TransactionsDTO(
        owner_id=owner_id,
        transaction_kind=TransactionKind.INCOME,
        amount=200.0,
        currency="USD",
        transaction_ts=ts,
        to_account_id=checking.id,
        category_id=cat_unbucketed_inc.id,
    )
    assert (
        classify_transaction_bucket(inc_templated, accounts_by_id, cats_by_id, {}).bucket
        == CashflowBucket.INCOME_FIXED.value
    )
    assert (
        classify_transaction_bucket(inc_adhoc, accounts_by_id, cats_by_id, {}).bucket
        == CashflowBucket.INCOME_VARIABLE.value
    )

    # classify_template_bucket: unbucketed income and liability-account fallback
    tpl_inc = TransactionTemplatesDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        category_id=cat_unbucketed_inc.id,
        name="Paycheck",
        planned_amount=1000.0,
        planned_day=15,
        from_account_id=checking.id,
    )
    tpl_loan = TransactionTemplatesDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        category_id=cat_unbucketed_exp.id,
        name="Auto Loan Due",
        planned_amount=400.0,
        planned_day=10,
        from_account_id=loan_acct.id,
    )
    assert classify_template_bucket(tpl_inc, accounts_by_id, cats_by_id) == CashflowBucket.INCOME_FIXED.value
    assert classify_template_bucket(tpl_loan, accounts_by_id, cats_by_id) == CashflowBucket.LOAN_PAYMENT.value
