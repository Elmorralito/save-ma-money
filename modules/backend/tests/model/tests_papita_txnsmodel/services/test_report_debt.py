"""Unit tests for Debt Interest-Drag ranking and Avalanche/Snowball simulator (PPT-091 / #184)."""

from __future__ import annotations

import uuid
from datetime import date

from papita_txnsmodel.access.account_details.dto import LoanAccountDetailsDTO
from papita_txnsmodel.access.account_financing.dto import AccountFinancingDTO
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.transactions.dto import TransactionTemplatesDTO
from papita_txnsmodel.model.enums import AccountKind, CategoryKind, InterestRateBasis, LedgerSide
from papita_txnsmodel.services.report_debt import compute_debt_paydown, normalize_interest_rates, simulate_debt_paydown


def test_rate_normalization_apy_and_nominal_monthly() -> None:
    """Verify both percent (>=1) and decimal (<1) rates convert cleanly between APY and MV."""
    ea_apy, mv_apy = normalize_interest_rates(19.0, InterestRateBasis.APY)
    assert round(ea_apy, 4) == 0.19
    assert round((1.0 + mv_apy) ** 12 - 1.0, 6) == 0.19

    ea_mv, mv_mv = normalize_interest_rates(0.015, InterestRateBasis.NOMINAL_MONTHLY)
    assert round(mv_mv, 4) == 0.015
    assert round(ea_mv, 6) == round(1.015**12 - 1.0, 6)


def test_debt_ranking_excludes_paid_off_and_computes_avalanche_rollover_without_double_count() -> None:
    """Verify priority ranking, linked asset carry, liquidity guardrail, and exact payoff rollover."""
    owner_id = uuid.uuid4()
    checking = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Checking",
        account_kind=AccountKind.CHECKING,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
        current_value=5000.0,
    )
    property_asset = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Rental Unit",
        account_kind=AccountKind.REAL_ESTATE,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
        current_value=200000.0,
        periodic_earnings=1200.0,
    )
    high_loan = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="High-Rate Loan",
        account_kind=AccountKind.LOAN_MORTGAGE,
        ledger_side=LedgerSide.LIABILITY,
        currency="USD",
        current_value=1200.0,
        interest_rate=24.0,
        interest_rate_basis=InterestRateBasis.APY,
        periodic_payment=650.0,
        overall_periods=2,
        periods_paid=0,
    )
    low_loan = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Mortgage",
        account_kind=AccountKind.LOAN_MORTGAGE,
        ledger_side=LedgerSide.LIABILITY,
        currency="USD",
        current_value=5000.0,
        interest_rate=12.0,
        interest_rate_basis=InterestRateBasis.APY,
        periodic_payment=600.0,
        overall_periods=10,
        periods_paid=0,
    )
    paid_off_loan = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Cleared Loan",
        account_kind=AccountKind.LOAN_MORTGAGE,
        ledger_side=LedgerSide.LIABILITY,
        currency="USD",
        current_value=1000.0,
        interest_rate=30.0,
        interest_rate_basis=InterestRateBasis.APY,
        periodic_payment=200.0,
    )
    excluded_acct = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Contingent Liability",
        account_kind=AccountKind.OTHER_LIABILITY,
        ledger_side=LedgerSide.LIABILITY,
        currency="USD",
        include_in_balance=False,
        current_value=900.0,
    )

    loan_details = {
        high_loan.id: LoanAccountDetailsDTO(
            account_id=high_loan.id,
            is_paid_off=False,
            insurance_payment=20.0,
            extras_payment=5.0,
        ),
        paid_off_loan.id: LoanAccountDetailsDTO(account_id=paid_off_loan.id, is_paid_off=True),
    }
    financing = [
        AccountFinancingDTO(
            owner_id=owner_id,
            asset_account_id=property_asset.id,
            loan_account_id=low_loan.id,
            financing_share=1.0,
        )
    ]

    paydown = compute_debt_paydown(
        accounts=[checking, property_asset, high_loan, low_loan, paid_off_loan, excluded_acct],
        loan_details_by_id=loan_details,
        financing_links=financing,
        balance_by_account_id={checking.id: 5000.0},
        templates=[],
        operating_outflows_90d=6000.0,  # 2000/mo burn -> 2.5 mos runway
        requested_currency="USD",
        include_excluded=True,
        target_liquidity_months=4.0,
        as_of=date(2026, 2, 1),
    )

    assert len(paydown["liabilities"]) == 2
    assert paydown["liabilities"][0]["account_name"] == "High-Rate Loan"
    assert paydown["liabilities"][0]["priority_rank"] == 1
    assert paydown["liabilities"][0]["monthly_extras_payment"] == 25.0
    assert paydown["liabilities"][1]["linked_asset"]["asset_name"] == "Rental Unit"
    assert paydown["liabilities"][1]["linked_asset"]["net_monthly_carry"] == 600.0
    assert paydown["excluded_liabilities"]["count"] == 2

    sim = simulate_debt_paydown(
        paydown_report=paydown,
        strategy="avalanche",
        extra_monthly_prepayment=200.0,
        lump_sum_prepayment=2500.0,
        lump_sum_month_offset=1,
        periodic_lump_sums=[{"month_of_year": 6, "amount": 500.0}],
        target_liquidity_months=4.0,
        horizon_months=24,
        as_of=date(2026, 2, 1),
    )

    assert sim["accelerated_months_to_payoff"] < sim["baseline_months_to_payoff"]
    assert sim["months_saved"] > 0
    assert sim["total_interest_saved"] > 0
    assert sim["liquidity_guardrail"]["status"] == "warning"
    # Verify month 1 did NOT double-count freed scheduled_pi of High-Rate Loan in the same month it paid off
    month_1 = sim["monthly_trajectory"][0]
    assert month_1["extra_applied"] <= 200.0 + 2500.0 + 625.0  # capped by extra + lump + any unused scheduled_pi


def test_debt_paydown_and_simulator_edge_cases() -> None:
    """Cover rate empty/zero, amortization fallback, neg amort, financing ties, template burn, snowball & guardrails."""
    assert normalize_interest_rates(None, InterestRateBasis.APY) == (0.0, 0.0)
    assert normalize_interest_rates(0.0, InterestRateBasis.NOMINAL_MONTHLY) == (0.0, 0.0)

    owner_id = uuid.uuid4()
    checking = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Checking",
        account_kind=AccountKind.CHECKING,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
        current_value=2500.0,  # not in balance_by_account_id -> fallback to current_value
    )
    eur_loan = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Euro Loan",
        account_kind=AccountKind.LOAN_MORTGAGE,
        ledger_side=LedgerSide.LIABILITY,
        currency="EUR",
        current_value=3000.0,
    )
    zero_loan = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Zero Balance Card",
        account_kind=AccountKind.CREDIT_CARD,
        ledger_side=LedgerSide.LIABILITY,
        currency="USD",
        current_value=0.0,
        interest_rate=25.0,
        periodic_payment=0.0,
    )
    amort_loan = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Personal Loan",
        account_kind=AccountKind.OTHER_LIABILITY,
        ledger_side=LedgerSide.LIABILITY,
        currency="USD",
        current_value=600.0,
        interest_rate=12.0,
        interest_rate_basis=InterestRateBasis.APY,
        periodic_payment=220.0,  # no overall_periods -> _estimate_remaining_periods loop
    )
    neg_amort_loan = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Neg Amort Loan",
        account_kind=AccountKind.OTHER_LIABILITY,
        ledger_side=LedgerSide.LIABILITY,
        currency="USD",
        current_value=5000.0,
        interest_rate=36.0,
        interest_rate_basis=InterestRateBasis.APY,
        periodic_payment=50.0,  # below monthly interest -> neg_amort=True & un-payoffable
    )
    missing_asset_id = uuid.uuid4()
    small_asset = AccountsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Primary Asset",
        account_kind=AccountKind.REAL_ESTATE,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
        current_value=None,
        initial_value=50000.0,
    )

    financing = [
        AccountFinancingDTO(
            owner_id=owner_id,
            asset_account_id=missing_asset_id,
            loan_account_id=amort_loan.id,
            financing_share=0.2,
            active=False,  # inactive skipped
        ),
        AccountFinancingDTO(
            owner_id=owner_id,
            asset_account_id=missing_asset_id,
            loan_account_id=amort_loan.id,
            financing_share=0.3,
        ),
        AccountFinancingDTO(
            owner_id=owner_id,
            asset_account_id=small_asset.id,
            loan_account_id=amort_loan.id,
            financing_share=0.8,  # higher share wins over 0.3
        ),
        AccountFinancingDTO(
            owner_id=owner_id,
            asset_account_id=missing_asset_id,
            loan_account_id=neg_amort_loan.id,
            financing_share=1.0,  # asset missing -> linked_asset None
        ),
    ]
    cat_inc = CategoriesDTO(
        id=uuid.uuid4(),
        name="Salary",
        category_kind=CategoryKind.INCOME,
    )
    cat_exp = CategoriesDTO(
        id=uuid.uuid4(),
        name="Bills",
        category_kind=CategoryKind.EXPENSE,
    )
    templates = [
        TransactionTemplatesDTO(
            id=uuid.uuid4(),
            owner_id=owner_id,
            category_id=cat_inc.id,
            name="Income Tpl",
            planned_amount=5000.0,
            planned_day=1,
            from_account_id=checking.id,
        ),
        TransactionTemplatesDTO(
            id=uuid.uuid4(),
            owner_id=owner_id,
            category_id=cat_exp.id,
            name="Due Date Tpl",
            planned_amount=300.0,
            planned_day=5,
            due_date=date(2026, 4, 5),
            from_account_id=checking.id,
        ),
        TransactionTemplatesDTO(
            id=uuid.uuid4(),
            owner_id=owner_id,
            category_id=cat_exp.id,
            name="Recurring Expense",
            planned_amount=600.0,
            planned_day=10,
            from_account_id=checking.id,
        ),
    ]

    paydown = compute_debt_paydown(
        accounts=[checking, eur_loan, zero_loan, amort_loan, neg_amort_loan, small_asset],
        loan_details_by_id={},
        financing_links=financing,
        balance_by_account_id={},  # force checking.current_value fallback
        templates=templates,
        categories=[cat_inc, cat_exp],
        operating_outflows_90d=0.0,  # force recurring template burn fallback (=600.0)
        requested_currency="USD",
        target_liquidity_months=3.0,
        as_of=date(2026, 2, 1),
    )

    assert paydown["liquidity_context"]["liquid_cash_total"] == 2500.0
    assert paydown["liquidity_context"]["baseline_monthly_burn"] == 600.0
    by_name = {item["account_name"]: item for item in paydown["liabilities"]}
    assert by_name["Zero Balance Card"]["remaining_periods"] == 0
    assert by_name["Personal Loan"]["remaining_periods"] == 3
    assert by_name["Personal Loan"]["linked_asset"]["asset_name"] == "Primary Asset"
    assert by_name["Neg Amort Loan"]["negative_amortization"] is True
    assert by_name["Neg Amort Loan"]["remaining_periods"] is None
    assert by_name["Neg Amort Loan"]["linked_asset"] is None

    # Snowball with small lump_sum -> "caution" guardrail (post cash = 2000 -> 3.33 mos < 4.0)
    sim_caution = simulate_debt_paydown(
        paydown_report=paydown,
        strategy="snowball",
        extra_monthly_prepayment=20.0,
        lump_sum_prepayment=500.0,
        target_liquidity_months=4.0,
        horizon_months=12,
        as_of=date(2026, 2, 1),
    )
    assert sim_caution["strategy"] == "snowball"
    assert sim_caution["months_saved"] is None  # neg amort baseline never pays off
    assert sim_caution["liquidity_guardrail"]["status"] == "caution"

    # Zero lump_sum -> "safe" guardrail (runway 4.17 >= 4.0)
    sim_safe = simulate_debt_paydown(
        paydown_report=paydown,
        strategy="avalanche",
        extra_monthly_prepayment=0.0,
        lump_sum_prepayment=0.0,
        target_liquidity_months=4.0,
        horizon_months=6,
        as_of=date(2026, 2, 1),
    )
    assert sim_safe["liquidity_guardrail"]["status"] == "safe"

    # Extra budget stops once open loans are exhausted & large lump_sum triggers "warning" guardrail
    sim_paid = simulate_debt_paydown(
        paydown_report={
            "currency": "USD",
            "_internal_ranked": [
                {
                    "account_id": str(amort_loan.id),
                    "account_name": "Mini Loan",
                    "effective_annual_rate_pct": 12.0,
                    "balance": 100.0,
                    "_r_m": 0.01,
                    "_sort_ea": 0.12,
                    "_scheduled_pi": 50.0,
                }
            ],
            "liquidity_context": {"liquid_cash_total": 1000.0, "baseline_monthly_burn": 500.0},
        },
        strategy="snowball",
        extra_monthly_prepayment=200.0,
        lump_sum_prepayment=500.0,
        target_liquidity_months=4.0,
        horizon_months=6,
        as_of=date(2026, 2, 1),
    )
    assert sim_paid["accelerated_months_to_payoff"] == 1
    assert sim_paid["liquidity_guardrail"]["status"] == "warning"
