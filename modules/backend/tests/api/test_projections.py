"""Unit tests for Colombian EA & US APR/APY financial projection & amortization math."""

from __future__ import annotations

import pytest

from papita_txnsmodel.services.projections import (
    CreditCardProjectionRequest,
    InvestmentProjectionRequest,
    LoanAmortizationRequest,
    RealEstateProjectionRequest,
    annual_to_monthly_rate,
    build_credit_card_projection,
    build_investment_projection,
    build_loan_amortization,
    build_real_estate_projection,
)


def test_colombian_ea_vs_us_apr_monthly_conversion() -> None:
    # Colombia 19.00% EA -> (1.19)^(1/12) - 1 ≈ 1.4602% MV (matches AV Villas spreadsheet 1.46%)
    co_mv = annual_to_monthly_rate(19.0, "CO_EA")
    assert co_mv == pytest.approx(0.0146017, rel=1e-3)

    # US 19.00% APR -> 19% / 12 = 1.5833% monthly
    us_m = annual_to_monthly_rate(19.0, "US_APR")
    assert us_m == pytest.approx(0.19 / 12.0, rel=1e-6)


def test_av_villas_loan_amortization_and_extra_payment_savings() -> None:
    # Real spreadsheet figures: $54,562,218 COP @ 19.00% EA, 72 months, $41,436 insurance
    res = build_loan_amortization(
        LoanAmortizationRequest(
            principal=54_562_218.0,
            annual_rate_pct=19.0,
            rate_convention="CO_EA",
            remaining_months=72,
            monthly_insurance=41_436.0,
            extra_monthly_payment=500_000.0,
        )
    )
    assert res.monthly_rate_pct == pytest.approx(1.46, abs=0.02)
    assert res.payoff_months < 72
    assert res.interest_saved_vs_baseline > 0
    assert res.months_saved_vs_baseline > 0
    assert res.schedule[-1].closing_balance == 0.0


def test_credit_card_one_cuota_vs_revolving() -> None:
    one_cuota = build_credit_card_projection(
        CreditCardProjectionRequest(
            balance=675_100.0,
            annual_rate_pct=25.0,
            rate_convention="CO_EA",
            monthly_payment=675_100.0,
            pay_in_one_installment=True,
        )
    )
    assert one_cuota.months_to_payoff == 1
    assert one_cuota.total_interest == 0.0

    revolving = build_credit_card_projection(
        CreditCardProjectionRequest(
            balance=2_455_880.0,
            annual_rate_pct=25.0,
            rate_convention="CO_EA",
            monthly_payment=600_000.0,
            pay_in_one_installment=False,
        )
    )
    assert revolving.months_to_payoff is not None
    assert revolving.months_to_payoff == 5
    assert revolving.total_interest > 0


def test_real_estate_aluna_beach_equity_projection() -> None:
    # Real spreadsheet figures: $431M value, $159M mortgage @ 17.10% EA, 226 months, $258k HOA
    res = build_real_estate_projection(
        RealEstateProjectionRequest(
            current_value=431_000_000.0,
            annual_appreciation_pct=8.0,
            horizon_years=10,
            monthly_rent_income=3_500_000.0,
            occupancy_pct=75.0,
            monthly_hoa_and_maintenance=258_000.0,
            mortgage_balance=159_000_000.0,
            mortgage_annual_rate_pct=17.10,
            mortgage_rate_convention="CO_EA",
            mortgage_remaining_months=226,
            mortgage_monthly_insurance=64_344.0,
        )
    )
    assert res.current_net_equity == pytest.approx(272_000_000.0)
    assert res.projected_property_value > 431_000_000.0
    assert res.projected_mortgage_balance < 159_000_000.0
    assert res.projected_net_equity > res.current_net_equity
    assert len(res.schedule) == 10


def test_investment_projection_net_of_fees_inflation_and_tax() -> None:
    res = build_investment_projection(
        InvestmentProjectionRequest(
            initial_amount=58_711_242.0,
            investment_type="us_equity_etf",
            expected_annual_return_pct=9.0,
            rate_convention="US_APY",
            horizon_years=10,
            monthly_contribution=1_000_000.0,
            annual_fee_pct=0.25,
            annual_inflation_pct=5.0,
            tax_on_gains_pct=15.0,
        )
    )
    assert res.final_gross_value > res.total_contributed
    assert res.final_after_tax_value < res.final_gross_value
    assert res.final_real_value < res.final_gross_value
    assert len(res.schedule) == 10


def test_get_projection_portfolio_resolves_balances_and_configs() -> None:
    import uuid
    from types import SimpleNamespace

    import pandas as pd

    from papita_txnsapi.routers.v1.projections import get_projection_portfolio
    from papita_txnsmodel.access.users.dto import UsersDTO
    from papita_txnsmodel.model.enums import AccountKind, LedgerSide

    owner_id = uuid.uuid4()
    loan_id = uuid.uuid4()
    re_id = uuid.uuid4()
    owner = UsersDTO(
        id=owner_id,
        username="tester",
        email="tester@example.com",
        password="SecurePass1!",
        preferences={"projection_configs": {str(loan_id): {"annual_rate_pct": 19.0, "rate_convention": "CO_EA"}}},
    )
    accounts_df = pd.DataFrame(
        [
            {
                "id": loan_id,
                "owner_id": owner_id,
                "name": "Compra de Cartera AV Villas",
                "account_kind": AccountKind.LOAN_MORTGAGE,
                "ledger_side": LedgerSide.LIABILITY,
                "currency": "COP",
                "initial_value": 54_562_218.0,
                "active": True,
            },
            {
                "id": re_id,
                "owner_id": owner_id,
                "name": "Aluna Beach Resort",
                "account_kind": AccountKind.REAL_ESTATE,
                "ledger_side": LedgerSide.ASSET,
                "currency": "COP",
                "current_value": 431_000_000.0,
                "active": True,
            },
        ]
    )
    balances_df = pd.DataFrame([{"account_id": loan_id, "balance": -54_000_000.0}])
    fake_service = SimpleNamespace(
        list_accounts=lambda **_kw: (accounts_df, 2),
        balances_service=SimpleNamespace(get_balances=lambda **_kw: balances_df),
    )

    resp = get_projection_portfolio(owner=owner, accounts_service=fake_service)
    assert len(resp.debts) == 1
    assert resp.debts[0].balance == pytest.approx(54_000_000.0)
    assert resp.debts[0].config["annual_rate_pct"] == 19.0
    assert len(resp.real_estate) == 1
    assert resp.real_estate[0].balance == pytest.approx(431_000_000.0)
