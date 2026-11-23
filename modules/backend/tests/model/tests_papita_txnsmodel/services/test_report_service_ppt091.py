"""Unit tests for ReportService PPT-091 orchestration and loaders."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest

from papita_txnsmodel.access.account_details.dto import CreditCardAccountDetailsDTO, LoanAccountDetailsDTO
from papita_txnsmodel.access.account_financing.dto import AccountFinancingDTO
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO, TransactionTemplatesDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import (
    AccountKind,
    CashflowBucket,
    CategoryKind,
    InterestRateBasis,
    LedgerSide,
    TransactionKind,
    TransactionStatus,
)
from papita_txnsmodel.services.reports import ReportService

_START = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)
_END = datetime(2026, 2, 28, 23, 59, tzinfo=timezone.utc)


def _make_owner() -> UsersDTO:
    return UsersDTO(
        id=uuid.uuid4(),
        username="ppt091_owner",
        email="ppt091@example.local",
        password="Password1!",
        auth_provider="local",
    )


def _wire_mock_subservices(svc: ReportService) -> dict[str, MagicMock]:
    mocks: dict[str, MagicMock] = {
        "accounts": MagicMock(),
        "categories": MagicMock(),
        "templates": MagicMock(),
        "cc_details": MagicMock(),
        "loan_details": MagicMock(),
        "balances": MagicMock(),
        "financing": MagicMock(),
        "transactions": MagicMock(),
    }
    mocks["transactions"].dto_type = TransactionsDTO
    svc.accounts_service = mocks["accounts"]
    svc.categories_service = mocks["categories"]
    svc.templates_service = mocks["templates"]
    svc.cc_details_service = mocks["cc_details"]
    svc.loan_details_service = mocks["loan_details"]
    svc.account_balances_service = mocks["balances"]
    svc.financing_service = mocks["financing"]
    svc.transactions_service = mocks["transactions"]
    return mocks


def test_report_service_wires_defaults_and_closes_connector() -> None:
    """Default model_validate wires all 8 services and close delegates cleanly."""
    connector = MagicMock()
    svc = ReportService.model_validate({"connector": connector})
    assert svc.transactions_service is not None
    assert svc.accounts_service is not None
    assert svc.categories_service is not None
    assert svc.templates_service is not None
    assert svc.cc_details_service is not None
    assert svc.loan_details_service is not None
    assert svc.account_balances_service is not None
    assert svc.financing_service is not None

    svc.close()
    connector.close.assert_called_once()


def test_operating_cashflow_and_planned_vs_actual_orchestration() -> None:
    """Verify operating_cashflow and planned_vs_actual load, filter, and delegate."""
    owner = _make_owner()
    assert owner.id is not None

    checking = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner.id,
        name="Checking",
        account_kind=AccountKind.CHECKING,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
        current_value=4000.0,
    )
    cc_acct = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner.id,
        name="Card",
        account_kind=AccountKind.CREDIT_CARD,
        ledger_side=LedgerSide.LIABILITY,
        currency="USD",
        current_value=500.0,
    )
    cat_income = CategoriesDTO(
        id=uuid.uuid4(),
        owner_id=owner.id,
        name="Salary",
        category_kind=CategoryKind.INCOME,
        cashflow_bucket=CashflowBucket.INCOME_FIXED,
    )
    cat_rent = CategoriesDTO(
        id=uuid.uuid4(),
        owner_id=owner.id,
        name="Rent",
        category_kind=CategoryKind.EXPENSE,
        cashflow_bucket=CashflowBucket.FIXED_EXPENSE,
    )
    tpl_rent = TransactionTemplatesDTO(
        id=uuid.uuid4(),
        owner_id=owner.id,
        category_id=cat_rent.id,
        name="Monthly Rent",
        planned_amount=1000.0,
        planned_day=5,
        from_account_id=checking.id,
    )
    txn_income = TransactionsDTO(
        id=uuid.uuid4(),
        owner_id=owner.id,
        transaction_kind=TransactionKind.INCOME,
        status=TransactionStatus.COMPLETED,
        amount=3000.0,
        currency="USD",
        transaction_ts=datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc),
        to_account_id=checking.id,
        category_id=cat_income.id,
    )
    txn_rent = TransactionsDTO(
        id=uuid.uuid4(),
        owner_id=owner.id,
        transaction_kind=TransactionKind.EXPENSE,
        status=TransactionStatus.COMPLETED,
        amount=1000.0,
        currency="USD",
        transaction_ts=datetime(2026, 2, 5, 12, 0, tzinfo=timezone.utc),
        from_account_id=checking.id,
        category_id=cat_rent.id,
        template_id=tpl_rent.id,
    )

    svc = ReportService.model_validate({"connector": MagicMock()})
    mocks = _wire_mock_subservices(svc)
    mocks["accounts"].get.return_value = checking
    mocks["accounts"].get_records.return_value = pd.DataFrame(
        [checking.model_dump(mode="python"), cc_acct.model_dump(mode="python")]
    )
    mocks["categories"].get_records.return_value = pd.DataFrame(
        [cat_income.model_dump(mode="python"), cat_rent.model_dump(mode="python")]
    )
    mocks["templates"].get_records.return_value = pd.DataFrame([tpl_rent.model_dump(mode="python")])
    mocks["cc_details"].get_map_by_account_ids.return_value = {
        cc_acct.id: CreditCardAccountDetailsDTO(account_id=cc_acct.id, credit_limit=2000.0, cashflow_only=False)
    }
    mocks["transactions"].get_transactions_frame.return_value = pd.DataFrame(
        [txn_income.model_dump(mode="python"), txn_rent.model_dump(mode="python")]
    )

    waterfall = svc.operating_cashflow(
        owner=owner,
        start_date=_START,
        end_date=_END,
        currency="USD",
        account_id=checking.id,
        include_monthly_series=True,
    )
    assert waterfall["currency"] == "USD"
    assert waterfall["waterfall"]["operating_free_cashflow"] == 2000.0
    assert len(waterfall["monthly_series"]) == 1
    mocks["accounts"].get.assert_called_once_with(obj=checking.id, owner=owner)

    variance = svc.planned_vs_actual(
        owner=owner,
        start_date=_START,
        end_date=_END,
        currency="USD",
        cashflow_bucket=CashflowBucket.FIXED_EXPENSE,
        as_of=date(2026, 2, 20),
    )
    assert variance["summary"]["planned_outflows"] == 1000.0
    assert variance["summary"]["actual_outflows"] == 1000.0
    assert len(variance["template_items"]) == 1

    # Also cover DAO single-column flattening and unknown frame fallback in _load_transactions
    txn_dao = txn_rent.to_dao()
    mocks["transactions"].get_transactions_frame.return_value = pd.DataFrame({"dao": [txn_dao]})
    flattened = svc._load_transactions(owner=owner, start_date=_START, end_date=_END)
    assert len(flattened) == 1
    assert flattened.iloc[0]["amount"] == 1000.0

    mocks["transactions"].get_transactions_frame.return_value = pd.DataFrame({"unexpected": [123]})
    assert svc._load_transactions(owner=owner).empty


def test_debt_paydown_and_simulation_orchestration() -> None:
    """Verify debt_paydown and simulate_debt_paydown with 90d burn and empty-txns fallback."""
    owner = _make_owner()
    assert owner.id is not None

    checking = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner.id,
        name="Checking",
        account_kind=AccountKind.CHECKING,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
        current_value=8000.0,
    )
    rental = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner.id,
        name="Rental Condo",
        account_kind=AccountKind.REAL_ESTATE,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
        current_value=150000.0,
        periodic_earnings=1100.0,
    )
    loan = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner.id,
        name="Mortgage",
        account_kind=AccountKind.LOAN_MORTGAGE,
        ledger_side=LedgerSide.LIABILITY,
        currency="USD",
        current_value=6000.0,
        interest_rate=18.0,
        interest_rate_basis=InterestRateBasis.APY,
        periodic_payment=500.0,
        overall_periods=14,
        periods_paid=0,
    )
    cat_exp = CategoriesDTO(
        id=uuid.uuid4(),
        owner_id=owner.id,
        name="Living",
        category_kind=CategoryKind.EXPENSE,
        cashflow_bucket=CashflowBucket.FIXED_EXPENSE,
    )
    txn_90d = TransactionsDTO(
        id=uuid.uuid4(),
        owner_id=owner.id,
        transaction_kind=TransactionKind.EXPENSE,
        status=TransactionStatus.COMPLETED,
        amount=1500.0,
        currency="USD",
        transaction_ts=datetime.now(timezone.utc),
        from_account_id=checking.id,
        category_id=cat_exp.id,
    )
    loan_detail = LoanAccountDetailsDTO(
        account_id=loan.id, is_paid_off=False, insurance_payment=20.0, extras_payment=0.0
    )
    financing = AccountFinancingDTO(
        owner_id=owner.id,
        asset_account_id=rental.id,
        loan_account_id=loan.id,
        financing_share=1.0,
    )

    svc = ReportService.model_validate({"connector": MagicMock()})
    mocks = _wire_mock_subservices(svc)
    mocks["accounts"].get_records.return_value = pd.DataFrame(
        [
            checking.model_dump(mode="python"),
            rental.model_dump(mode="python"),
            loan.model_dump(mode="python"),
        ]
    )
    mocks["categories"].get_records.return_value = pd.DataFrame([cat_exp.model_dump(mode="python")])
    mocks["templates"].get_records.return_value = pd.DataFrame()
    mocks["cc_details"].get_map_by_account_ids.return_value = {}
    mocks["loan_details"].get_map_by_account_ids.return_value = {loan.id: loan_detail}
    mocks["financing"].get_records.return_value = pd.DataFrame([financing.model_dump(mode="python")])
    mocks["balances"].get_balances.return_value = pd.DataFrame(
        [
            {"account_id": str(checking.id), "balance": 8000.0},
            {"account_id": None, "balance": 999.0},
        ]
    )
    mocks["transactions"].get_transactions_frame.return_value = pd.DataFrame([txn_90d.model_dump(mode="python")])

    paydown = svc.debt_paydown(
        owner=owner,
        currency="USD",
        include_excluded=True,
        target_liquidity_months=4.0,
        as_of=date(2026, 2, 1),
    )
    assert "_internal_ranked" not in paydown
    assert paydown["liquidity_context"]["baseline_monthly_burn"] == 500.0
    assert paydown["liabilities"][0]["linked_asset"]["asset_name"] == "Rental Condo"

    # Empty 90d transactions path
    mocks["transactions"].get_transactions_frame.return_value = pd.DataFrame()
    sim = svc.simulate_debt_paydown(
        owner=owner,
        currency="USD",
        strategy="snowball",
        extra_monthly_prepayment=200.0,
        lump_sum_prepayment=500.0,
        periodic_lump_sums=[{"month_of_year": 6, "amount": 300.0}],
        as_of=date(2026, 2, 1),
    )
    assert sim["strategy"] == "snowball"
    assert sim["months_saved"] > 0
    assert sim["total_interest_saved"] > 0


def test_report_service_none_guards_and_ownership_errors() -> None:
    """Verify None sub-service guards, empty account ID shortcuts, and foreign account rejection."""
    owner = _make_owner()
    svc = ReportService.model_validate({"connector": MagicMock()})
    svc.accounts_service = None
    svc.categories_service = None
    svc.templates_service = None
    svc.cc_details_service = None
    svc.loan_details_service = None
    svc.account_balances_service = None
    svc.financing_service = None
    svc.transactions_service = None

    assert svc._load_accounts(owner=owner) == []
    assert svc._load_categories(owner=owner) == []
    assert svc._load_templates(owner=owner) == []
    assert svc._load_cc_details([]) == {}
    assert svc._load_loan_details([]) == {}
    assert svc._load_balance_map(owner=owner) == {}
    assert svc._load_financing_links(owner=owner) == []

    with pytest.raises(RuntimeError, match="accounts_service"):
        svc._ensure_account_owned(owner=owner, account_id=uuid.uuid4())
    with pytest.raises(RuntimeError, match="transactions_service"):
        svc._load_transactions(owner=owner)

    # Configured services returning empty / foreign account
    mocks = _wire_mock_subservices(svc)
    mocks["accounts"].get.return_value = None
    with pytest.raises(ValueError, match="Account not found"):
        svc._ensure_account_owned(owner=owner, account_id=uuid.uuid4())

    checking_only = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner.id,
        name="Checking",
        account_kind=AccountKind.CHECKING,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
    )
    assert svc._load_cc_details([checking_only]) == {}
    assert svc._load_loan_details([checking_only]) == {}
    mocks["cc_details"].get_map_by_account_ids.assert_not_called()
    mocks["loan_details"].get_map_by_account_ids.assert_not_called()

    mocks["balances"].get_balances.return_value = pd.DataFrame()
    assert svc._load_balance_map(owner=owner) == {}


def test_financial_health_orchestration() -> None:
    """Verify ReportService.financial_health loads accounts, 90d txns, and delegates."""
    owner = _make_owner()
    assert owner.id is not None

    checking = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner.id,
        name="Checking",
        account_kind=AccountKind.CHECKING,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
        current_value=15_000.0,
    )
    loan = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner.id,
        name="Loan",
        account_kind=AccountKind.LOAN_MORTGAGE,
        ledger_side=LedgerSide.LIABILITY,
        currency="USD",
        current_value=5_000.0,
    )
    cat_rent = CategoriesDTO(
        id=uuid.uuid4(),
        owner_id=owner.id,
        name="Rent",
        category_kind=CategoryKind.EXPENSE,
        cashflow_bucket=CashflowBucket.FIXED_EXPENSE,
    )
    txn_rent = TransactionsDTO(
        id=uuid.uuid4(),
        owner_id=owner.id,
        transaction_kind=TransactionKind.EXPENSE,
        status=TransactionStatus.COMPLETED,
        from_account_id=checking.id,
        category_id=cat_rent.id,
        amount=3000.0,
        transaction_ts=datetime.now(timezone.utc),
    )

    svc = ReportService.model_validate({"connector": MagicMock()})
    mocks = _wire_mock_subservices(svc)
    mocks["accounts"].get_records.return_value = pd.DataFrame([checking.model_dump(), loan.model_dump()])
    mocks["categories"].get_records.return_value = pd.DataFrame([cat_rent.model_dump()])
    mocks["templates"].get_records.return_value = pd.DataFrame()
    mocks["cc_details"].get_map_by_account_ids.return_value = {}
    mocks["loan_details"].get_map_by_account_ids.return_value = {}
    mocks["financing"].get_records.return_value = pd.DataFrame()
    mocks["balances"].get_balances.return_value = pd.DataFrame(
        [{"account_id": checking.id, "balance": 15_000.0}, {"account_id": loan.id, "balance": -5_000.0}]
    )
    mocks["transactions"].get_transactions_frame.return_value = pd.DataFrame([txn_rent.model_dump()])

    res = svc.financial_health(owner=owner, currency="USD", target_liquidity_months=4.0)
    assert res["currency"] == "USD"
    assert res["scorecard"]["reconciled_net_worth"] == 10_000.0
    assert res["scorecard"]["baseline_monthly_burn"] == 1_000.0
    assert res["scorecard"]["liquid_runway_months"] == 15.0

    # Empty 90d transactions branch
    mocks["transactions"].get_transactions_frame.return_value = pd.DataFrame()
    res_empty = svc.financial_health(owner=owner)
    assert res_empty["scorecard"]["reconciled_net_worth"] == 10_000.0
    assert res_empty["scorecard"]["liquid_runway_months"] is None
