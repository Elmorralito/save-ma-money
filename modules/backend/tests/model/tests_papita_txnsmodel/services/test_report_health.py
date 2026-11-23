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


def test_compute_financial_health_value_fallbacks_and_inactive_links() -> None:
    liquid_current = _acct(
        name="Liquid Current",
        kind=AccountKind.SAVINGS,
        side=LedgerSide.ASSET,
        current_value=2_000.0,
        initial_value=500.0,
    )
    liquid_initial = _acct(
        name="Liquid Initial",
        kind=AccountKind.CASH,
        side=LedgerSide.ASSET,
        current_value=None,
        initial_value=1_000.0,
    )
    non_liquid_balance = _acct(
        name="Other Asset Balance",
        kind=AccountKind.OTHER_ASSET,
        side=LedgerSide.ASSET,
        current_value=None,
        initial_value=100.0,
    )
    non_liquid_initial = _acct(
        name="Other Asset Initial",
        kind=AccountKind.REAL_ESTATE,
        side=LedgerSide.ASSET,
        current_value=None,
        initial_value=5_000.0,
    )
    liab_balance = _acct(
        name="Card Balance",
        kind=AccountKind.CREDIT_CARD,
        side=LedgerSide.LIABILITY,
        current_value=None,
        initial_value=200.0,
    )
    liab_initial = _acct(
        name="Other Liab Initial",
        kind=AccountKind.OTHER_LIABILITY,
        side=LedgerSide.LIABILITY,
        current_value=None,
        initial_value=800.0,
    )
    excluded_collateral = _acct(
        name="Excluded Collateral",
        kind=AccountKind.INVESTMENT_BROKERAGE,
        side=LedgerSide.ASSET,
        include_in_balance=False,
        current_value=50_000.0,
    )

    assert non_liquid_balance.id is not None
    assert liab_balance.id is not None
    assert liab_initial.id is not None
    assert excluded_collateral.id is not None
    assert liquid_current.id is not None

    inactive_link = AccountFinancingDTO(
        id=uuid.uuid4(),
        owner_id=liquid_current.owner_id,
        asset_account_id=non_liquid_balance.id,
        loan_account_id=liab_balance.id,
        financing_share=1.0,
        active=False,
    )
    missing_acct_link = AccountFinancingDTO(
        id=uuid.uuid4(),
        owner_id=liquid_current.owner_id,
        asset_account_id=uuid.uuid4(),
        loan_account_id=liab_balance.id,
        financing_share=1.0,
        active=True,
    )
    excluded_asset_link = AccountFinancingDTO(
        id=uuid.uuid4(),
        owner_id=liquid_current.owner_id,
        asset_account_id=excluded_collateral.id,
        loan_account_id=liab_initial.id,
        financing_share=1.0,
        active=True,
    )

    result = compute_financial_health(
        accounts=[
            liquid_current,
            liquid_initial,
            non_liquid_balance,
            non_liquid_initial,
            liab_balance,
            liab_initial,
            excluded_collateral,
        ],
        loan_details_by_id={},
        financing_links=[inactive_link, missing_acct_link, excluded_asset_link],
        balance_by_account_id={non_liquid_balance.id: 3_000.0, liab_balance.id: -1_200.0},
        debt_payload=_debt_payload(),
        requested_currency="USD",
    )

    sc = result["scorecard"]
    # Assets = 2,000 + 1,000 + 3,000 + 5,000 = 11,000
    assert sc["total_assets"] == 11_000.0
    # Liabilities = 1,200 + 800 = 2,000
    assert sc["total_liabilities"] == 2_000.0
    assert sc["reconciled_net_worth"] == 9_000.0
    assert sc["margin_ltv_pct"] is None


def test_financial_health_uses_trading_position_valuation_and_margin_ltv() -> None:
    """Trading accounts with unit_price compute units * unit_price * fx_rate and feed Margin LTV."""
    from papita_txnsmodel.access.account_details.dto import TradingAccountDetailsDTO
    from papita_txnsmodel.services.report_health import compute_position_valuation

    owner_id = uuid.uuid4()
    broker_id = uuid.uuid4()
    margin_id = uuid.uuid4()

    assert compute_position_valuation(units=250.0, unit_price=72.68, fx_rate=4000.0) == 72_680_000.0

    accounts = [
        AccountsDTO(
            id=broker_id,
            owner_id=owner_id,
            name="IBKR IAU",
            account_kind=AccountKind.INVESTMENT_BROKERAGE,
            ledger_side=LedgerSide.ASSET,
            currency="COP",
            fx_rate=4000.0,
            include_in_balance=True,
            current_value=None,
        ),
        AccountsDTO(
            id=margin_id,
            owner_id=owner_id,
            name="IBKR Leverage",
            account_kind=AccountKind.LOAN_MORTGAGE,
            ledger_side=LedgerSide.LIABILITY,
            currency="COP",
            fx_rate=4000.0,
            include_in_balance=True,
            current_value=36_340_000.0,
        ),
    ]
    trading_details = {
        broker_id: TradingAccountDetailsDTO(
            account_id=broker_id,
            symbol="IAU",
            buy_value=97.75,
            units=250.0,
            unit_price=72.68,
            fx_rate=4000.0,
        )
    }
    financing = [
        AccountFinancingDTO(
            owner_id=owner_id,
            asset_account_id=broker_id,
            loan_account_id=margin_id,
            financing_share=1.0,
        )
    ]

    result = compute_financial_health(
        accounts=accounts,
        loan_details_by_id={},
        financing_links=financing,
        balance_by_account_id={},
        debt_payload={"summary": {}, "liquidity_context": {}},
        requested_currency="COP",
        trading_details_by_id=trading_details,
    )
    sc = result["scorecard"]
    assert sc["total_assets"] == 72_680_000.0
    assert sc["total_liabilities"] == 36_340_000.0
    assert sc["reconciled_net_worth"] == 36_340_000.0
    assert sc["margin_ltv_pct"] == 50.0


def test_financial_health_converts_foreign_usd_ibkr_assets_and_margin_to_cop() -> None:
    """USD accounts with fx_rate != 1.0 convert into COP net worth and Margin LTV."""
    from papita_txnsmodel.access.account_details.dto import TradingAccountDetailsDTO

    owner_id = uuid.uuid4()
    cop_checking_id = uuid.uuid4()
    usd_broker_id = uuid.uuid4()
    usd_margin_id = uuid.uuid4()

    accounts = [
        AccountsDTO(
            id=cop_checking_id,
            owner_id=owner_id,
            name="Bancolombia",
            account_kind=AccountKind.CHECKING,
            ledger_side=LedgerSide.ASSET,
            currency="COP",
            fx_rate=1.0,
            include_in_balance=True,
            current_value=20_000_000.0,
        ),
        AccountsDTO(
            id=usd_broker_id,
            owner_id=owner_id,
            name="IBKR IAU USD",
            account_kind=AccountKind.INVESTMENT_BROKERAGE,
            ledger_side=LedgerSide.ASSET,
            currency="USD",
            fx_rate=4000.0,
            include_in_balance=True,
            current_value=None,
        ),
        AccountsDTO(
            id=usd_margin_id,
            owner_id=owner_id,
            name="IBKR Margin USD",
            account_kind=AccountKind.LOAN_MORTGAGE,
            ledger_side=LedgerSide.LIABILITY,
            currency="USD",
            fx_rate=4000.0,
            include_in_balance=True,
            current_value=10_000.0,
        ),
    ]
    trading_details = {
        usd_broker_id: TradingAccountDetailsDTO(
            account_id=usd_broker_id,
            symbol="IAU",
            buy_value=80.0,
            units=250.0,
            unit_price=80.0,
            fx_rate=4000.0,
        )
    }
    financing = [
        AccountFinancingDTO(
            owner_id=owner_id,
            asset_account_id=usd_broker_id,
            loan_account_id=usd_margin_id,
            financing_share=1.0,
        )
    ]

    result = compute_financial_health(
        accounts=accounts,
        loan_details_by_id={},
        financing_links=financing,
        balance_by_account_id={cop_checking_id: 20_000_000.0},
        debt_payload={"summary": {}, "liquidity_context": {}},
        requested_currency="COP",
        trading_details_by_id=trading_details,
    )
    sc = result["scorecard"]
    # 20M COP checking + (250 * 80 * 4000 = 80M COP IAU) = 100M COP assets
    assert sc["total_assets"] == 100_000_000.0
    # 10,000 USD * 4000 = 40M COP margin loan
    assert sc["total_liabilities"] == 40_000_000.0
    assert sc["reconciled_net_worth"] == 60_000_000.0
    # 40M / 80M = 50.0% Margin LTV
    assert sc["margin_ltv_pct"] == 50.0
