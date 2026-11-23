"""Unit tests for Operating Free Cashflow waterfall analytics (PPT-091 / #184)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from papita_txnsmodel.access.account_details.dto import CreditCardAccountDetailsDTO
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.model.enums import (
    AccountKind,
    CashflowBucket,
    CategoryKind,
    LedgerSide,
    SettlementStatus,
    TransactionKind,
    TransactionStatus,
)
from papita_txnsmodel.services.report_waterfall import compute_operating_cashflow


def _acct(
    name: str,
    kind: AccountKind,
    side: LedgerSide,
    *,
    currency: str = "USD",
) -> AccountsDTO:
    return AccountsDTO(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        name=name,
        account_kind=kind,
        ledger_side=side,
        currency=currency,
    )


def _cat(name: str, kind: CategoryKind, bucket: CashflowBucket | None = None) -> CategoriesDTO:
    return CategoriesDTO(
        id=uuid.uuid4(),
        name=name,
        category_kind=kind,
        cashflow_bucket=bucket,
    )


def test_waterfall_isolates_sweeps_debt_proceeds_and_principal_returns() -> None:
    """Verify Operating FCF isolates internal sweeps, loan disbursements, and principal returns."""
    checking = _acct("Checking", AccountKind.CHECKING, LedgerSide.ASSET)
    savings = _acct("HYSA", AccountKind.SAVINGS, LedgerSide.ASSET)
    brokerage = _acct("Brokerage", AccountKind.INVESTMENT_BROKERAGE, LedgerSide.ASSET)
    loan = _acct("Personal Loan", AccountKind.LOAN_MORTGAGE, LedgerSide.LIABILITY)
    receivable = _acct("Private Loan Receivable", AccountKind.OTHER_ASSET, LedgerSide.ASSET)

    cat_salary = _cat("Salary", CategoryKind.INCOME, CashflowBucket.INCOME_FIXED)
    cat_bonus = _cat("Bonus", CategoryKind.INCOME, CashflowBucket.INCOME_VARIABLE)
    cat_rent = _cat("Rent", CategoryKind.EXPENSE, CashflowBucket.FIXED_EXPENSE)
    cat_food = _cat("Food", CategoryKind.EXPENSE, CashflowBucket.VARIABLE_EXPENSE)
    cat_repair = _cat("Repair", CategoryKind.EXPENSE, CashflowBucket.UNEXPECTED_EXPENSE)

    ts = datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc)
    txns = [
        TransactionsDTO(
            owner_id=checking.owner_id,
            transaction_kind=TransactionKind.INCOME,
            amount=1000.0,
            currency="USD",
            transaction_ts=ts,
            to_account_id=checking.id,
            category_id=cat_salary.id,
        ),
        TransactionsDTO(
            owner_id=checking.owner_id,
            transaction_kind=TransactionKind.INCOME,
            amount=200.0,
            currency="USD",
            transaction_ts=ts,
            to_account_id=checking.id,
            category_id=cat_bonus.id,
        ),
        TransactionsDTO(
            owner_id=checking.owner_id,
            transaction_kind=TransactionKind.TRANSFER,
            amount=150.0,
            currency="USD",
            transaction_ts=ts,
            from_account_id=checking.id,
            to_account_id=loan.id,
        ),
        TransactionsDTO(
            owner_id=checking.owner_id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=350.0,
            currency="USD",
            transaction_ts=ts,
            from_account_id=checking.id,
            category_id=cat_rent.id,
        ),
        TransactionsDTO(
            owner_id=checking.owner_id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=100.0,
            currency="USD",
            transaction_ts=ts,
            from_account_id=checking.id,
            category_id=cat_food.id,
        ),
        TransactionsDTO(
            owner_id=checking.owner_id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=50.0,
            currency="USD",
            transaction_ts=ts,
            from_account_id=checking.id,
            category_id=cat_repair.id,
        ),
        # Allocations below Operating FCF:
        TransactionsDTO(
            owner_id=checking.owner_id,
            transaction_kind=TransactionKind.TRANSFER,
            amount=120.0,
            currency="USD",
            transaction_ts=ts,
            from_account_id=checking.id,
            to_account_id=savings.id,
        ),
        TransactionsDTO(
            owner_id=checking.owner_id,
            transaction_kind=TransactionKind.TRANSFER,
            amount=80.0,
            currency="USD",
            transaction_ts=ts,
            from_account_id=checking.id,
            to_account_id=brokerage.id,
        ),
        # Non-operating inflows (debt proceeds + principal return):
        TransactionsDTO(
            owner_id=checking.owner_id,
            transaction_kind=TransactionKind.TRANSFER,
            amount=500.0,
            currency="USD",
            transaction_ts=ts,
            from_account_id=loan.id,
            to_account_id=checking.id,
            category_id=cat_salary.id,  # even with income category, debt proceeds stay non-operating
        ),
        TransactionsDTO(
            owner_id=checking.owner_id,
            transaction_kind=TransactionKind.TRANSFER,
            amount=300.0,
            currency="USD",
            transaction_ts=ts,
            from_account_id=receivable.id,
            to_account_id=checking.id,
        ),
        # Internal sweep (Checking -> Checking):
        TransactionsDTO(
            owner_id=checking.owner_id,
            transaction_kind=TransactionKind.TRANSFER,
            amount=400.0,
            currency="USD",
            transaction_ts=ts,
            from_account_id=checking.id,
            to_account_id=checking.id,
        ),
    ]

    result = compute_operating_cashflow(
        transactions=txns,
        accounts=[checking, savings, brokerage, loan, receivable],
        categories=[cat_salary, cat_bonus, cat_rent, cat_food, cat_repair],
        cc_details_by_id={},
        include_monthly_series=True,
    )

    wf = result["waterfall"]
    assert wf["total_external_income"] == 1200.0
    assert wf["loans"] == 150.0
    assert wf["fixed_expenses"] == 350.0
    assert wf["variable_expenses"] == 100.0
    assert wf["unexpected_expenses"] == 50.0
    assert wf["total_operating_outflows"] == 650.0
    assert wf["operating_free_cashflow"] == 550.0
    assert wf["organic_fcf_margin_pct"] == 45.83
    assert wf["debt_service_to_income_pct"] == 12.5
    assert wf["savings"] == 120.0
    assert wf["capital_deployments"] == 80.0
    assert wf["net_allocated_surplus"] == 350.0
    assert wf["non_operating_inflows"] == 800.0
    assert wf["net_ledger_cashflow"] == 1150.0
    assert wf["internal_sweeps_volume"] == 400.0
    assert wf["status_tone"] == "positive"
    assert len(result["monthly_series"]) == 1
    assert result["monthly_series"][0]["month"] == "2026-02"


def test_credit_card_cashflow_only_vs_itemized_and_in_transit_isolation() -> None:
    """Verify cashflow_only CCs, itemized CCs, IN_TRANSIT exclusion, and multi-currency warnings."""
    checking = _acct("Checking", AccountKind.CHECKING, LedgerSide.ASSET, currency="USD")
    cc_cashflow = _acct("Card CF", AccountKind.CREDIT_CARD, LedgerSide.LIABILITY, currency="USD")
    cc_itemized = _acct("Card Itemized", AccountKind.CREDIT_CARD, LedgerSide.LIABILITY, currency="USD")
    cop_acct = _acct("COP Checking", AccountKind.CHECKING, LedgerSide.ASSET, currency="COP")

    cat_groceries = _cat("Groceries", CategoryKind.EXPENSE, None)
    ts = datetime(2026, 2, 15, 10, 0, tzinfo=timezone.utc)

    txns = [
        # Cashflow-only card lump-sum payment -> counts as VARIABLE_EXPENSE
        TransactionsDTO(
            owner_id=checking.owner_id,
            transaction_kind=TransactionKind.TRANSFER,
            amount=300.0,
            currency="USD",
            transaction_ts=ts,
            from_account_id=checking.id,
            to_account_id=cc_cashflow.id,
        ),
        # Itemized expense accidentally posted on cashflow-only card -> excluded + diagnostic
        TransactionsDTO(
            owner_id=checking.owner_id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=45.0,
            currency="USD",
            transaction_ts=ts,
            from_account_id=cc_cashflow.id,
            category_id=cat_groceries.id,
        ),
        # Itemized card payment -> internal transfer (not counted)
        TransactionsDTO(
            owner_id=checking.owner_id,
            transaction_kind=TransactionKind.TRANSFER,
            amount=200.0,
            currency="USD",
            transaction_ts=ts,
            from_account_id=checking.id,
            to_account_id=cc_itemized.id,
        ),
        # Itemized card purchase -> counts as operating expense
        TransactionsDTO(
            owner_id=checking.owner_id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=90.0,
            currency="USD",
            transaction_ts=ts,
            from_account_id=cc_itemized.id,
            category_id=cat_groceries.id,
        ),
        # IN_TRANSIT wire -> excluded from settled waterfall, summarized in in_transit
        TransactionsDTO(
            owner_id=checking.owner_id,
            transaction_kind=TransactionKind.TRANSFER,
            amount=590.40,
            currency="USD",
            transaction_ts=ts,
            from_account_id=checking.id,
            to_account_id=cc_itemized.id,
            settlement_status=SettlementStatus.IN_TRANSIT,
        ),
        # Different currency -> isolated out when USD is selected
        TransactionsDTO(
            owner_id=checking.owner_id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=500000.0,
            currency="COP",
            transaction_ts=ts,
            from_account_id=cop_acct.id,
            category_id=cat_groceries.id,
            status=TransactionStatus.COMPLETED,
        ),
    ]

    cc_details = {
        cc_cashflow.id: CreditCardAccountDetailsDTO(account_id=cc_cashflow.id, credit_limit=5000.0, cashflow_only=True),
        cc_itemized.id: CreditCardAccountDetailsDTO(
            account_id=cc_itemized.id, credit_limit=5000.0, cashflow_only=False
        ),
    }

    result = compute_operating_cashflow(
        transactions=txns,
        accounts=[checking, cc_cashflow, cc_itemized, cop_acct],
        categories=[cat_groceries],
        cc_details_by_id=cc_details,
        requested_currency="USD",
    )

    assert result["currency"] == "USD"
    assert result["multi_currency_warning"] is True
    assert result["available_currencies"] == ["COP", "USD"]
    assert result["waterfall"]["variable_expenses"] == 390.0
    assert result["in_transit"]["count"] == 1
    assert result["in_transit"]["total_volume"] == 590.4
    assert result["diagnostics"]["cashflow_only_cc_excluded_count"] == 1
    assert result["diagnostics"]["cashflow_only_cc_excluded_amount"] == 45.0
    assert result["diagnostics"]["cashflow_only_cc_account_names"] == ["Card CF"]
    assert result["diagnostics"]["unbucketed_category_count"] == 1
