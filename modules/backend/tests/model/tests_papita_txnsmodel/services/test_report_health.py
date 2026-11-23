"""Unit tests for Financial Health Scorecard calculation (PPT-088 / #181)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from papita_txnsmodel.access.account_details.dto import LoanAccountDetailsDTO
from papita_txnsmodel.access.account_financing.dto import AccountFinancingDTO
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.model.enums import AccountKind, LedgerSide
from papita_txnsmodel.services.report_health import compute_financial_health


def _acct(
    *,
    name: str,
    kind: AccountKind,
    side: LedgerSide,
    currency: str = "USD",
    active: bool = True,
    include_in_balance: bool = True,
    closed_at: datetime | None = None,
    current_value: float | None = None,
    initial_value: float = 0.0,
) -> AccountsDTO:
    return AccountsDTO(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        name=name,
        account_kind=kind,
        ledger_side=side,
        currency=currency,
        active=active,
        include_in_balance=include_in_balance,
        closed_at=closed_at,
        current_value=current_value,
        initial_value=initial_value,
    )


def _debt_payload(
    *,
    liquid_cash: float = 12_000.0,
    burn: float = 3_000.0,
    runway: float | None = 4.0,
    monthly_payment: float = 1_500.0,
    monthly_interest: float = 250.0,
) -> dict:
    return {
        "summary": {
            "total_monthly_contractual_payment": monthly_payment,
            "total_monthly_interest_drag": monthly_interest,
        },
        "liquidity_context": {
            "liquid_cash_total": liquid_cash,
            "baseline_monthly_burn": burn,
            "liquid_runway_months": runway,
            "target_liquidity_months": 4.0,
        },
    }


def test_compute_financial_health_reconciles_assets_liabilities_and_ltv() -> None:
    cash = _acct(name="Checking", kind=AccountKind.CHECKING, side=LedgerSide.ASSET, initial_value=10_000.0)
    brokerage = _acct(
        name="Brokerage",
        kind=AccountKind.INVESTMENT_BROKERAGE,
        side=LedgerSide.ASSET,
        current_value=100_000.0,
    )
    margin_loan = _acct(
        name="Margin Loan",
        kind=AccountKind.LOAN_MORTGAGE,
        side=LedgerSide.LIABILITY,
        current_value=30_000.0,
    )
    excluded_acct = _acct(
        name="Excluded Stash",
        kind=AccountKind.SAVINGS,
        side=LedgerSide.ASSET,
        include_in_balance=False,
        current_value=50_000.0,
    )
    paid_off_loan = _acct(
        name="Paid Off Loan",
        kind=AccountKind.LOAN_MORTGAGE,
        side=LedgerSide.LIABILITY,
        current_value=5_000.0,
    )
    closed_acct = _acct(
        name="Old Checking",
        kind=AccountKind.CHECKING,
        side=LedgerSide.ASSET,
        closed_at=datetime.now() + timedelta(days=1),
        current_value=9_999.0,
    )

    assert cash.id is not None
    assert brokerage.id is not None
    assert margin_loan.id is not None
    assert paid_off_loan.id is not None

    link = AccountFinancingDTO(
        id=uuid.uuid4(),
        owner_id=cash.owner_id,
        asset_account_id=brokerage.id,
        loan_account_id=margin_loan.id,
        financing_share=1.0,
        active=True,
    )
    paid_off_detail = LoanAccountDetailsDTO(account_id=paid_off_loan.id, is_paid_off=True)

    result = compute_financial_health(
        accounts=[cash, brokerage, margin_loan, excluded_acct, paid_off_loan, closed_acct],
        loan_details_by_id={paid_off_loan.id: paid_off_detail},
        financing_links=[link],
        balance_by_account_id={cash.id: 12_000.0},
        debt_payload=_debt_payload(),
        requested_currency="USD",
    )

    assert result["currency"] == "USD"
    assert result["multi_currency_warning"] is False
    sc = result["scorecard"]
    # Assets = 12,000 (cash ledger balance) + 100,000 (brokerage current_value) = 112,000
    assert sc["total_assets"] == 112_000.0
    # Liabilities = 30,000 (paid-off loan excluded)
    assert sc["total_liabilities"] == 30_000.0
    assert sc["reconciled_net_worth"] == 82_000.0
    assert sc["debt_to_asset_ratio_pct"] == round((30_000.0 / 112_000.0) * 100.0, 2)
    assert sc["margin_ltv_pct"] == 30.0
    assert sc["liquid_runway_months"] == 4.0
    assert sc["monthly_debt_service"] == 1_500.0
    assert sc["included_asset_count"] == 2
    assert sc["included_liability_count"] == 1
    assert sc["excluded_account_count"] == 2


def test_compute_financial_health_handles_empty_accounts_and_multi_currency() -> None:
    usd_acct = _acct(name="USD Cash", kind=AccountKind.CASH, side=LedgerSide.ASSET, currency="USD", current_value=0.0)
    cop_acct = _acct(
        name="COP Cash",
        kind=AccountKind.SAVINGS,
        side=LedgerSide.ASSET,
        currency="COP",
        current_value=5_000_000.0,
    )

    result = compute_financial_health(
        accounts=[usd_acct, cop_acct],
        loan_details_by_id={},
        financing_links=[],
        balance_by_account_id={},
        debt_payload=_debt_payload(liquid_cash=0.0, burn=0.0, runway=None, monthly_payment=0.0, monthly_interest=0.0),
        requested_currency="USD",
    )

    assert result["currency"] == "USD"
    assert result["multi_currency_warning"] is True
    assert set(result["available_currencies"]) == {"USD", "COP"}
    sc = result["scorecard"]
    assert sc["reconciled_net_worth"] == 0.0
    assert sc["debt_to_asset_ratio_pct"] is None
    assert sc["margin_ltv_pct"] is None
    assert sc["liquid_runway_months"] is None
