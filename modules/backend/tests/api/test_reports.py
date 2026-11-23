"""Tests for report endpoints (PPT-038).

Covers issue #48 acceptance: JWT on all routes, ReportService delegation (no
duplicated aggregation), date/`account_id` filters, CSV export stub, and 501
budget-performance.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

_SPENDING_PARAMS = {"start_date": "2026-02-01", "end_date": "2026-02-28"}
_EXPORT_PARAMS = {
    "report_type": "spending",
    "format": "csv",
    "start_date": "2026-02-01",
    "end_date": "2026-02-28",
}


class TestReportsAuth:
    """AC: all report routes require a valid JWT."""

    @pytest.mark.parametrize(
        ("path", "params"),
        [
            ("/api/v1/reports/spending", _SPENDING_PARAMS),
            ("/api/v1/reports/cash-flow", _SPENDING_PARAMS),
            ("/api/v1/reports/trends", {"months": 3}),
            ("/api/v1/reports/export", _EXPORT_PARAMS),
            ("/api/v1/reports/operating-cashflow", _SPENDING_PARAMS),
            ("/api/v1/reports/planned-vs-actual", _SPENDING_PARAMS),
            ("/api/v1/reports/debt-paydown", None),
        ],
    )
    def test_report_route_without_token_returns_401(
        self,
        client: TestClient,
        path: str,
        params: dict[str, str] | None,
    ) -> None:
        response = client.get(path, params=params)
        assert response.status_code == 401

    def test_debt_simulate_without_token_returns_401(self, client: TestClient) -> None:
        response = client.post("/api/v1/reports/debt-paydown/simulate", json={})
        assert response.status_code == 401


class TestReportsRoutes:
    """Report read models with mocked ReportService."""

    def test_openapi_lists_report_paths(self, client: TestClient) -> None:
        schema = client.get("/api/openapi.json").json()
        paths = schema["paths"]
        assert "/api/v1/reports/spending" in paths
        assert "/api/v1/reports/cash-flow" in paths
        assert "/api/v1/reports/trends" in paths
        assert "/api/v1/reports/export" in paths
        assert "/api/v1/reports/operating-cashflow" in paths
        assert "/api/v1/reports/planned-vs-actual" in paths
        assert "/api/v1/reports/debt-paydown" in paths
        assert "/api/v1/reports/debt-paydown/simulate" in paths

    def test_spending_maps_service_payload(
        self,
        reports_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = reports_client
        category_id = uuid.uuid4()
        account_id = uuid.uuid4()
        mock_service.spending.return_value = {
            "group_by": "category",
            "expenses": [{"category_id": category_id, "total": 40.0}],
            "expense_total": 40.0,
            "income_total": 100.0,
        }

        response = client.get(
            "/api/v1/reports/spending",
            params={**_SPENDING_PARAMS, "group_by": "category", "account_id": str(account_id)},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["total_spending"] == 40.0
        assert payload["total_income"] == 100.0
        assert payload["net_savings"] == 60.0
        assert payload["breakdown"][0]["amount"] == 40.0
        assert payload["breakdown"][0]["percentage"] == 100.0
        assert payload["trend"] == []
        mock_service.spending.assert_called_once()
        call_kwargs = mock_service.spending.call_args.kwargs
        assert call_kwargs["owner"] is owner
        assert call_kwargs["group_by"] == "category"
        assert call_kwargs["account_id"] == account_id

    def test_spending_foreign_account_maps_to_client_error(
        self,
        reports_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        """Cross-tenant account_id is rejected (owner-scoped validation)."""
        client, owner, mock_service = reports_client
        mock_service.spending.side_effect = ValueError("Account not found for tenant.")

        response = client.get(
            "/api/v1/reports/spending",
            params={**_SPENDING_PARAMS, "account_id": str(uuid.uuid4())},
        )

        assert response.status_code == 404
        assert "tenant" in response.json()["detail"].lower()
        assert mock_service.spending.call_args.kwargs["owner"] is owner

    def test_all_live_report_routes_pass_owner(
        self,
        reports_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        """Every live report handler forwards the JWT tenant as owner=."""
        client, owner, mock_service = reports_client
        mock_service.spending.return_value = {
            "group_by": "category",
            "expenses": [],
            "expense_total": 0.0,
            "income_total": 0.0,
        }
        mock_service.cash_flow.return_value = {
            "inflows": 0.0,
            "outflows": 0.0,
            "net": 0.0,
            "portfolio_total": 0.0,
        }
        mock_service.trends.return_value = {"period": "monthly", "series": []}
        mock_service.export.return_value = "metric,value\n"

        assert client.get("/api/v1/reports/spending", params=_SPENDING_PARAMS).status_code == 200
        assert client.get("/api/v1/reports/cash-flow", params=_SPENDING_PARAMS).status_code == 200
        assert client.get("/api/v1/reports/trends", params={"months": 1}).status_code == 200
        assert client.get("/api/v1/reports/export", params=_EXPORT_PARAMS).status_code == 200

        assert mock_service.spending.call_args.kwargs["owner"] is owner
        assert mock_service.cash_flow.call_args.kwargs["owner"] is owner
        assert mock_service.trends.call_args.kwargs["owner"] is owner
        assert mock_service.export.call_args.kwargs["owner"] is owner

    def test_spending_rejects_unsupported_group_by(
        self,
        reports_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, _, mock_service = reports_client
        response = client.get(
            "/api/v1/reports/spending",
            params={**_SPENDING_PARAMS, "group_by": "day"},
        )
        assert response.status_code in (400, 422)
        mock_service.spending.assert_not_called()

    def test_cash_flow_maps_portfolio_to_closing_balance(
        self,
        reports_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = reports_client
        account_id = uuid.uuid4()
        mock_service.cash_flow.return_value = {
            "inflows": 500.0,
            "outflows": 200.0,
            "net": 300.0,
            "portfolio_total": 12500.0,
        }

        response = client.get(
            "/api/v1/reports/cash-flow",
            params={**_SPENDING_PARAMS, "account_id": str(account_id)},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["total_inflows"] == 500.0
        assert payload["total_outflows"] == 200.0
        assert payload["net_cash_flow"] == 300.0
        assert payload["closing_balance"] == 12500.0
        assert payload["opening_balance"] == 0.0
        assert payload["by_account"] == []
        call_kwargs = mock_service.cash_flow.call_args.kwargs
        assert call_kwargs["owner"] is owner
        assert call_kwargs["refresh_balances"] is False
        assert call_kwargs["account_id"] == account_id

    def test_trends_maps_series_to_monthly_trends(
        self,
        reports_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, _, mock_service = reports_client
        mock_service.trends.return_value = {
            "period": "monthly",
            "series": [
                {
                    "period_start": datetime(2026, 2, 1, tzinfo=timezone.utc),
                    "transaction_kind": "EXPENSE",
                    "total": 250.0,
                },
                {
                    "period_start": datetime(2026, 2, 1, tzinfo=timezone.utc),
                    "transaction_kind": "INCOME",
                    "total": 1000.0,
                },
            ],
        }

        response = client.get("/api/v1/reports/trends", params={"months": 3})

        assert response.status_code == 200
        payload = response.json()
        assert payload["period"] == "monthly"
        assert len(payload["monthly_trends"]) == 1
        assert payload["monthly_trends"][0]["month"] == "2026-02"
        assert payload["monthly_trends"][0]["total_spending"] == 250.0
        assert payload["monthly_trends"][0]["total_income"] == 1000.0
        assert payload["monthly_trends"][0]["savings_rate"] == 75.0
        assert payload["insights"] == []
        assert payload["category_trends"] == []

    def test_export_returns_csv(
        self,
        reports_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, _, mock_service = reports_client
        mock_service.export.return_value = "metric,value\nexpense_total,1.0\n"

        response = client.get("/api/v1/reports/export", params=_EXPORT_PARAMS)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "expense_total" in response.text
        mock_service.export.assert_called_once()

    def test_export_json_delegates_to_service(
        self,
        reports_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, _, mock_service = reports_client
        mock_service.export.return_value = {"expense_total": 1.0, "income_total": 2.0}

        response = client.get(
            "/api/v1/reports/export",
            params={**_EXPORT_PARAMS, "format": "json"},
        )

        assert response.status_code == 200
        assert response.json()["expense_total"] == 1.0
        assert mock_service.export.call_args.kwargs["export_format"] == "json"

    def test_export_xlsx_returns_501(
        self,
        reports_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, _, mock_service = reports_client
        response = client.get(
            "/api/v1/reports/export",
            params={**_EXPORT_PARAMS, "format": "xlsx"},
        )
        assert response.status_code == 501
        assert "deferred" in response.json()["deferred_reason"].lower()
        mock_service.export.assert_not_called()

    def test_operating_cashflow_maps_payload_and_passes_owner(
        self,
        reports_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = reports_client
        mock_service.operating_cashflow.return_value = {
            "currency": "USD",
            "available_currencies": ["USD"],
            "multi_currency_warning": False,
            "waterfall": {
                "income_fixed": 1000.0,
                "income_variable": 200.0,
                "total_external_income": 1200.0,
                "loans": 150.0,
                "fixed_expenses": 350.0,
                "variable_expenses": 100.0,
                "unexpected_expenses": 0.0,
                "total_operating_outflows": 600.0,
                "operating_free_cashflow": 600.0,
                "organic_fcf_margin_pct": 50.0,
                "debt_service_to_income_pct": 12.5,
                "savings": 200.0,
                "capital_deployments": 100.0,
                "net_allocated_surplus": 300.0,
                "non_operating_inflows": 500.0,
                "net_ledger_cashflow": 800.0,
                "internal_sweeps_volume": 400.0,
                "status_tone": "positive",
            },
            "buckets": [],
            "in_transit": {"count": 0, "inflows": 0.0, "outflows": 0.0, "total_volume": 0.0},
            "monthly_series": [],
            "diagnostics": {
                "unbucketed_category_count": 0,
                "unbucketed_amount": 0.0,
                "cashflow_only_cc_excluded_count": 0,
                "cashflow_only_cc_excluded_amount": 0.0,
                "cashflow_only_cc_account_names": [],
            },
        }

        response = client.get(
            "/api/v1/reports/operating-cashflow",
            params={**_SPENDING_PARAMS, "currency": "usd", "include_monthly_series": "true"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["waterfall"]["operating_free_cashflow"] == 600.0
        assert payload["waterfall"]["non_operating_inflows"] == 500.0
        call_kwargs = mock_service.operating_cashflow.call_args.kwargs
        assert call_kwargs["owner"] is owner
        assert call_kwargs["currency"] == "USD"
        assert call_kwargs["include_monthly_series"] is True

    def test_operating_cashflow_foreign_account_returns_404(
        self,
        reports_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, _, mock_service = reports_client
        mock_service.operating_cashflow.side_effect = ValueError("Account not found for tenant.")

        response = client.get(
            "/api/v1/reports/operating-cashflow",
            params={**_SPENDING_PARAMS, "account_id": str(uuid.uuid4())},
        )
        assert response.status_code == 404

    def test_planned_vs_actual_maps_payload_and_rejects_bad_bucket(
        self,
        reports_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = reports_client
        mock_service.planned_vs_actual.return_value = {
            "currency": "USD",
            "available_currencies": ["USD"],
            "multi_currency_warning": False,
            "summary": {
                "planned_income": 1000.0,
                "actual_income": 1000.0,
                "planned_outflows": 500.0,
                "actual_outflows": 450.0,
                "planned_operating_fcf": 500.0,
                "actual_operating_fcf": 550.0,
                "net_fcf_variance": 50.0,
                "adherence_pct": 90.0,
                "reconciliation_flag_count": 0,
                "status_tone": "positive",
            },
            "bucket_rollups": [],
            "template_items": [],
            "unplanned_items": [],
            "reconciliation_flags": [],
        }

        ok_resp = client.get("/api/v1/reports/planned-vs-actual", params=_SPENDING_PARAMS)
        assert ok_resp.status_code == 200
        assert ok_resp.json()["summary"]["net_fcf_variance"] == 50.0
        assert mock_service.planned_vs_actual.call_args.kwargs["owner"] is owner

        bad_resp = client.get(
            "/api/v1/reports/planned-vs-actual",
            params={**_SPENDING_PARAMS, "cashflow_bucket": "not_a_bucket"},
        )
        assert bad_resp.status_code in (400, 422)

    def test_debt_paydown_and_simulation_routes(
        self,
        reports_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = reports_client
        mock_service.debt_paydown.return_value = {
            "currency": "USD",
            "available_currencies": ["USD"],
            "multi_currency_warning": False,
            "summary": {
                "total_debt": 5000.0,
                "active_liability_count": 1,
                "total_monthly_interest_drag": 70.0,
                "total_annual_interest_drag": 950.0,
                "total_monthly_contractual_payment": 300.0,
                "weighted_average_ea_pct": 19.0,
                "highest_rate_account_name": "Loan A",
                "highest_rate_payoff_date": "2027-08-01",
            },
            "liabilities": [],
            "liquidity_context": {
                "liquid_cash_total": 10000.0,
                "baseline_monthly_burn": 2000.0,
                "liquid_runway_months": 5.0,
                "target_liquidity_months": 4.0,
                "safe_lump_sum_headroom": 2000.0,
            },
            "excluded_liabilities": None,
        }
        mock_service.simulate_debt_paydown.return_value = {
            "currency": "USD",
            "strategy": "avalanche",
            "baseline_months_to_payoff": 20,
            "accelerated_months_to_payoff": 12,
            "baseline_payoff_date": "2027-10-01",
            "accelerated_payoff_date": "2027-02-01",
            "months_saved": 8,
            "baseline_total_interest": 800.0,
            "accelerated_total_interest": 400.0,
            "total_interest_saved": 400.0,
            "per_liability_impact": [],
            "monthly_trajectory": [],
            "liquidity_guardrail": {
                "status": "safe",
                "liquid_cash_total": 10000.0,
                "post_lump_sum_cash": 9000.0,
                "post_lump_sum_runway_months": 4.5,
                "target_liquidity_months": 4.0,
                "safe_lump_sum_headroom": 2000.0,
                "message": "Liquid cash remains above your target runway floor after planned prepayments.",
            },
        }

        debt_resp = client.get("/api/v1/reports/debt-paydown")
        assert debt_resp.status_code == 200
        assert debt_resp.json()["summary"]["total_debt"] == 5000.0
        assert mock_service.debt_paydown.call_args.kwargs["owner"] is owner

        sim_resp = client.post(
            "/api/v1/reports/debt-paydown/simulate",
            json={"strategy": "avalanche", "extra_monthly_prepayment": 250.0, "lump_sum_prepayment": 1000.0},
        )
        assert sim_resp.status_code == 200
        assert sim_resp.json()["months_saved"] == 8
        assert mock_service.simulate_debt_paydown.call_args.kwargs["owner"] is owner

        bad_sim = client.post(
            "/api/v1/reports/debt-paydown/simulate",
            json={"extra_monthly_prepayment": -50.0},
        )
        assert bad_sim.status_code == 422

    def test_ppt091_query_validation_currency_norm_and_cache_bypass(
        self,
        reports_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = reports_client

        inv_ocf = client.get(
            "/api/v1/reports/operating-cashflow",
            params={"start_date": "2026-03-10", "end_date": "2026-03-01"},
        )
        assert inv_ocf.status_code in (400, 422)

        inv_pva = client.get(
            "/api/v1/reports/planned-vs-actual",
            params={"start_date": "2026-03-10", "end_date": "2026-03-01"},
        )
        assert inv_pva.status_code in (400, 422)

        mock_service.planned_vs_actual.return_value = {
            "currency": "COP",
            "available_currencies": ["COP"],
            "multi_currency_warning": False,
            "summary": {
                "planned_income": 0.0,
                "actual_income": 0.0,
                "planned_outflows": 0.0,
                "actual_outflows": 0.0,
                "planned_operating_fcf": 0.0,
                "actual_operating_fcf": 0.0,
                "net_fcf_variance": 0.0,
                "adherence_pct": 100.0,
                "reconciliation_flag_count": 0,
                "status_tone": "positive",
            },
            "bucket_rollups": [],
            "template_items": [],
            "unplanned_items": [],
            "reconciliation_flags": [],
        }
        pva_ok = client.get(
            "/api/v1/reports/planned-vs-actual",
            params={**_SPENDING_PARAMS, "currency": "cop", "cashflow_bucket": "fixed_expense"},
        )
        assert pva_ok.status_code == 200
        assert mock_service.planned_vs_actual.call_args.kwargs["currency"] == "COP"

        mock_service.debt_paydown.return_value = {
            "currency": "COP",
            "available_currencies": ["COP"],
            "multi_currency_warning": False,
            "summary": {
                "total_debt": 0.0,
                "active_liability_count": 0,
                "total_monthly_interest_drag": 0.0,
                "total_annual_interest_drag": 0.0,
                "total_monthly_contractual_payment": 0.0,
                "weighted_average_ea_pct": 0.0,
                "highest_rate_account_name": None,
                "highest_rate_payoff_date": None,
            },
            "liabilities": [],
            "liquidity_context": {
                "liquid_cash_total": 0.0,
                "baseline_monthly_burn": 0.0,
                "liquid_runway_months": None,
                "target_liquidity_months": 4.0,
                "safe_lump_sum_headroom": 0.0,
            },
            "excluded_liabilities": None,
        }
        debt_ok = client.get("/api/v1/reports/debt-paydown", params={"currency": "cop"})
        assert debt_ok.status_code == 200
        assert mock_service.debt_paydown.call_args.kwargs["currency"] == "COP"

        # Cover _cached_report_call X-Cache: BYPASS when owner.id is None
        mock_service.operating_cashflow.return_value = {
            "currency": "USD",
            "available_currencies": ["USD"],
            "multi_currency_warning": False,
            "waterfall": {
                "income_fixed": 0.0,
                "income_variable": 0.0,
                "total_operating_inflows": 0.0,
                "loan_payments": 0.0,
                "fixed_expenses": 0.0,
                "variable_expenses": 0.0,
                "unexpected_expenses": 0.0,
                "total_operating_outflows": 0.0,
                "operating_free_cashflow": 0.0,
                "savings": 0.0,
                "capital_deployments": 0.0,
                "total_allocations": 0.0,
                "net_cash_generation": 0.0,
                "non_operating_inflows": 0.0,
                "internal_transfers_excluded": 0.0,
            },
            "buckets": [],
            "monthly_series": [],
            "diagnostics": {
                "unbucketed_transaction_count": 0,
                "unbucketed_amount": 0.0,
                "cashflow_only_card_expense_excluded_count": 0,
            },
        }
        owner.id = None  # type: ignore[attr-defined]
        bypass_resp = client.get("/api/v1/reports/operating-cashflow", params=_SPENDING_PARAMS)
        assert bypass_resp.status_code == 200
        assert bypass_resp.headers["X-Cache"] == "BYPASS"
