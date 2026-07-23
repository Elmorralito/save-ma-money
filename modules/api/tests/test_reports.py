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
            ("/api/v1/reports/budget-performance", None),
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


class TestReportsRoutes:
    """Report read models with mocked ReportService."""

    def test_openapi_lists_report_paths(self, client: TestClient) -> None:
        schema = client.get("/api/openapi.json").json()
        paths = schema["paths"]
        assert "/api/v1/reports/spending" in paths
        assert "/api/v1/reports/cash-flow" in paths
        assert "/api/v1/reports/trends" in paths
        assert "/api/v1/reports/export" in paths
        assert "/api/v1/reports/budget-performance" in paths

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

    def test_budget_performance_returns_501(
        self,
        reports_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, _, _ = reports_client
        response = client.get("/api/v1/reports/budget-performance")
        assert response.status_code == 501
        body = response.json()
        assert body["detail"]
        assert "budget" in (body.get("deferred_reason") or "").lower()
