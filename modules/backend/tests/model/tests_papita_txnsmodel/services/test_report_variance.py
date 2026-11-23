"""Unit tests for Planned-vs-Actual variance and reconciliation flags (PPT-091 / #184)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO, TransactionTemplatesDTO
from papita_txnsmodel.model.enums import AccountKind, CashflowBucket, CategoryKind, LedgerSide, TransactionKind
from papita_txnsmodel.services.report_variance import compute_planned_vs_actual


def test_planned_vs_actual_expansion_partial_sums_and_reconciliation_flags() -> None:
    """Verify template expansion, multi-posting aggregation, unplanned rollups, and all 3 flags."""
    owner_id = uuid.uuid4()
    checking = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Checking",
        account_kind=AccountKind.CHECKING,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
    )
    cat_salary = CategoriesDTO(
        id=uuid.uuid4(),
        name="Salary",
        category_kind=CategoryKind.INCOME,
        cashflow_bucket=CashflowBucket.INCOME_FIXED,
    )
    cat_rent = CategoriesDTO(
        id=uuid.uuid4(),
        name="Rent",
        category_kind=CategoryKind.EXPENSE,
        cashflow_bucket=CashflowBucket.FIXED_EXPENSE,
    )
    cat_utilities = CategoriesDTO(
        id=uuid.uuid4(),
        name="Utilities",
        category_kind=CategoryKind.EXPENSE,
        cashflow_bucket=None,  # triggers unbucketed_category flag
    )

    tpl_salary = TransactionTemplatesDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        category_id=cat_salary.id,
        name="Monthly Paycheck",
        planned_amount=2000.0,
        planned_day=15,
        from_account_id=checking.id,
    )
    tpl_rent = TransactionTemplatesDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        category_id=cat_rent.id,
        name="Apartment Rent",
        planned_amount=1000.0,
        planned_day=5,
        from_account_id=checking.id,
    )
    tpl_oneoff = TransactionTemplatesDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        category_id=cat_utilities.id,
        name="Water Bill",
        planned_amount=100.0,
        planned_day=20,
        due_date=date(2026, 2, 20),
        from_account_id=checking.id,
    )

    txns = [
        # Two linked partial postings for Rent in Feb -> 1000 total (paid)
        TransactionsDTO(
            owner_id=owner_id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=600.0,
            currency="USD",
            transaction_ts=datetime(2026, 2, 4, 12, 0, tzinfo=timezone.utc),
            from_account_id=checking.id,
            category_id=cat_rent.id,
            template_id=tpl_rent.id,
        ),
        TransactionsDTO(
            owner_id=owner_id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=400.0,
            currency="USD",
            transaction_ts=datetime(2026, 2, 6, 12, 0, tzinfo=timezone.utc),
            from_account_id=checking.id,
            category_id=cat_rent.id,
            template_id=tpl_rent.id,
        ),
        # Unlinked posting matching Water Bill within 5% and 5 days -> unlinked_high_value flag
        TransactionsDTO(
            owner_id=owner_id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=98.0,
            currency="USD",
            transaction_ts=datetime(2026, 2, 19, 12, 0, tzinfo=timezone.utc),
            from_account_id=checking.id,
            category_id=cat_utilities.id,
            template_id=None,
        ),
        # Duplicate postings within 2 days -> potential_duplicate flag
        TransactionsDTO(
            owner_id=owner_id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=42.5,
            currency="USD",
            transaction_ts=datetime(2026, 2, 10, 10, 0, tzinfo=timezone.utc),
            from_account_id=checking.id,
            category_id=cat_utilities.id,
            template_id=None,
        ),
        TransactionsDTO(
            owner_id=owner_id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=42.5,
            currency="USD",
            transaction_ts=datetime(2026, 2, 12, 10, 0, tzinfo=timezone.utc),
            from_account_id=checking.id,
            category_id=cat_utilities.id,
            template_id=None,
        ),
    ]

    report = compute_planned_vs_actual(
        templates=[tpl_salary, tpl_rent, tpl_oneoff],
        transactions=txns,
        accounts=[checking],
        categories=[cat_salary, cat_rent, cat_utilities],
        cc_details_by_id={},
        start_day=date(2026, 2, 1),
        end_day=date(2026, 2, 28),
        as_of=date(2026, 2, 25),
    )

    by_tpl = {item["template_name"]: item for item in report["template_items"]}
    assert by_tpl["Apartment Rent"]["actual_amount"] == 1000.0
    assert by_tpl["Apartment Rent"]["status"] == "paid"
    assert by_tpl["Apartment Rent"]["linked_transaction_count"] == 2
    assert by_tpl["Monthly Paycheck"]["status"] == "overdue"
    assert by_tpl["Water Bill"]["status"] == "overdue"

    assert len(report["unplanned_items"]) == 1
    assert report["unplanned_items"][0]["actual_amount"] == 183.0

    flag_codes = {flag["code"] for flag in report["reconciliation_flags"]}
    assert {"unlinked_high_value", "potential_duplicate", "unbucketed_category"}.issubset(flag_codes)
    assert report["summary"]["planned_income"] == 2000.0
    assert report["summary"]["planned_outflows"] == 1100.0
    assert report["summary"]["actual_outflows"] == 1183.0


def test_planned_vs_actual_filters_statuses_and_zero_planned_branches() -> None:
    """Cover template/txn filters, variance status variants, and mild-shortfall/zero-planned summaries."""
    owner_id = uuid.uuid4()
    checking = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Checking",
        account_kind=AccountKind.CHECKING,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
    )
    other_acct = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Euro Checking",
        account_kind=AccountKind.CHECKING,
        ledger_side=LedgerSide.ASSET,
        currency="EUR",
    )
    savings = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Savings",
        account_kind=AccountKind.SAVINGS,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
    )
    cat_salary = CategoriesDTO(
        id=uuid.uuid4(),
        name="Salary",
        category_kind=CategoryKind.INCOME,
        cashflow_bucket=CashflowBucket.INCOME_FIXED,
    )
    cat_fixed = CategoriesDTO(
        id=uuid.uuid4(),
        name="Internet",
        category_kind=CategoryKind.EXPENSE,
        cashflow_bucket=CashflowBucket.FIXED_EXPENSE,
    )
    cat_var = CategoriesDTO(
        id=uuid.uuid4(),
        name="Dining",
        category_kind=CategoryKind.EXPENSE,
        cashflow_bucket=CashflowBucket.VARIABLE_EXPENSE,
    )

    tpl_inactive = TransactionTemplatesDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        category_id=cat_fixed.id,
        name="Cancelled Plan",
        planned_amount=50.0,
        planned_day=1,
        from_account_id=checking.id,
        active=False,
    )
    tpl_eur = TransactionTemplatesDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        category_id=cat_fixed.id,
        name="Euro Hosting",
        planned_amount=40.0,
        planned_day=2,
        from_account_id=other_acct.id,
    )
    tpl_salary = TransactionTemplatesDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        category_id=cat_salary.id,
        name="Salary",
        planned_amount=1000.0,
        planned_day=5,
        from_account_id=checking.id,
    )
    tpl_internet = TransactionTemplatesDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        category_id=cat_fixed.id,
        name="Internet",
        planned_amount=100.0,
        planned_day=10,
        from_account_id=checking.id,
    )
    tpl_dining = TransactionTemplatesDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        category_id=cat_var.id,
        name="Dining Plan",
        planned_amount=200.0,
        planned_day=25,
        from_account_id=checking.id,
    )

    txns = [
        # Income > 105% -> status "exceeded"
        TransactionsDTO(
            owner_id=owner_id,
            transaction_kind=TransactionKind.INCOME,
            amount=1100.0,
            currency="USD",
            transaction_ts=datetime(2026, 3, 5, 12, 0, tzinfo=timezone.utc),
            to_account_id=checking.id,
            category_id=cat_salary.id,
            template_id=tpl_salary.id,
        ),
        # Partial expense (< 99%) -> status "partial"
        TransactionsDTO(
            owner_id=owner_id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=60.0,
            currency="USD",
            transaction_ts=datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc),
            from_account_id=checking.id,
            category_id=cat_fixed.id,
            template_id=tpl_internet.id,
        ),
        # Over-budget expense (> 105%) -> status "over_budget"
        TransactionsDTO(
            owner_id=owner_id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=250.0,
            currency="USD",
            transaction_ts=datetime(2026, 3, 25, 12, 0, tzinfo=timezone.utc),
            from_account_id=checking.id,
            category_id=cat_var.id,
            template_id=tpl_dining.id,
        ),
        # Internal transfer between two checking accounts -> skipped via INTERNAL_BUCKET
        TransactionsDTO(
            owner_id=owner_id,
            transaction_kind=TransactionKind.TRANSFER,
            amount=50.0,
            currency="USD",
            transaction_ts=datetime(2026, 3, 12, 12, 0, tzinfo=timezone.utc),
            from_account_id=checking.id,
            to_account_id=savings.id,
        ),
    ]

    full_report = compute_planned_vs_actual(
        templates=[tpl_inactive, tpl_eur, tpl_salary, tpl_internet, tpl_dining],
        transactions=txns,
        accounts=[checking, other_acct, savings],
        categories=[cat_salary, cat_fixed, cat_var],
        cc_details_by_id={},
        start_day=date(2026, 3, 1),
        end_day=date(2026, 3, 31),
        requested_currency="USD",
        as_of=date(2026, 3, 15),
    )
    by_name = {item["template_name"]: item for item in full_report["template_items"]}
    assert set(by_name) == {"Salary", "Internet", "Dining Plan"}
    assert by_name["Salary"]["status"] == "exceeded"
    assert by_name["Internet"]["status"] == "partial"
    assert by_name["Dining Plan"]["status"] == "over_budget"
    assert full_report["summary"]["status_tone"] == "positive"

    # Bucket + account filters exclude non-matching templates/transactions cleanly
    bucket_only = compute_planned_vs_actual(
        templates=[tpl_salary, tpl_internet, tpl_dining],
        transactions=txns,
        accounts=[checking, savings],
        categories=[cat_salary, cat_fixed, cat_var],
        cc_details_by_id={},
        start_day=date(2026, 3, 1),
        end_day=date(2026, 3, 31),
        requested_currency="USD",
        account_id=checking.id,
        cashflow_bucket=CashflowBucket.FIXED_EXPENSE,
        as_of=date(2026, 3, 15),
    )
    assert [row["template_name"] for row in bucket_only["template_items"]] == ["Internet"]

    # Zero planned outflows -> adherence_pct 100.0 (when actual == 0) and 0.0 (when unplanned expense > 0)
    empty_report = compute_planned_vs_actual(
        templates=[],
        transactions=[],
        accounts=[checking],
        categories=[],
        cc_details_by_id={},
        start_day=date(2026, 3, 1),
        end_day=date(2026, 3, 31),
        requested_currency="USD",
        as_of=date(2026, 3, 15),
    )
    assert empty_report["summary"]["adherence_pct"] == 100.0

    # Mild shortfall within 10% -> status_tone "warning" + actual > 0 with planned_outflows == 0 -> adherence_pct 0.0
    mild_tpl = TransactionTemplatesDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        category_id=cat_salary.id,
        name="Pay",
        planned_amount=1000.0,
        planned_day=10,
        from_account_id=checking.id,
    )
    mild_report = compute_planned_vs_actual(
        templates=[mild_tpl],
        transactions=[
            TransactionsDTO(
                owner_id=owner_id,
                transaction_kind=TransactionKind.INCOME,
                amount=1000.0,
                currency="USD",
                transaction_ts=datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc),
                to_account_id=checking.id,
                category_id=cat_salary.id,
                template_id=mild_tpl.id,
            ),
            TransactionsDTO(
                owner_id=owner_id,
                transaction_kind=TransactionKind.EXPENSE,
                amount=50.0,
                currency="USD",
                transaction_ts=datetime(2026, 3, 11, 12, 0, tzinfo=timezone.utc),
                from_account_id=checking.id,
                category_id=cat_fixed.id,
            ),
        ],
        accounts=[checking],
        categories=[cat_salary, cat_fixed],
        cc_details_by_id={},
        start_day=date(2026, 3, 1),
        end_day=date(2026, 3, 31),
        requested_currency="USD",
        as_of=date(2026, 3, 15),
    )
    assert mild_report["summary"]["adherence_pct"] == 0.0
    assert mild_report["summary"]["status_tone"] == "warning"
