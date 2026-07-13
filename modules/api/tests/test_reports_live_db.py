"""Live-DB report smoke tests for PPT-038 (B0 Docker Postgres).

Creates seeded income/expense rows via the API and asserts ``ReportService``
totals through ``GET /reports/spending`` and ``GET /reports/cash-flow``.
Skipped unless ``DATABASE_URL`` points at reachable PostgreSQL.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "model" / "tests"))

from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.main import create_app
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.services.users import UsersService
from postgres_gate import postgres_url, requires_postgres

POSTGRES_URL = postgres_url()

_VALID_PASSWORD = "SecurePass1!"
_PERIOD = {"start_date": "2026-02-01", "end_date": "2026-02-28"}


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(client: TestClient, *, suffix: str) -> str:
    payload = {
        "username": f"ppt038_{suffix}",
        "email": f"ppt038_{suffix}@example.local",
        "password": _VALID_PASSWORD,
    }
    reg = client.post("/api/v1/auth/register", json=payload)
    assert reg.status_code == 201, reg.text
    login = client.post(
        "/api/v1/auth/login",
        data={"username": payload["username"], "password": _VALID_PASSWORD},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


@requires_postgres
class TestReportsLiveDb:
    """B0 seeded-ledger acceptance for PPT-038."""

    @pytest.fixture(scope="class")
    def live_client(self):
        """API client bound to live Postgres via ``DATABASE_URL``."""
        SQLDatabaseConnector.close()
        SQLDatabaseConnector.establish(connection={"url": POSTGRES_URL})
        UsersService.ensure_password_manager()
        get_settings.cache_clear()
        os.environ["DATABASE_URL"] = str(POSTGRES_URL)
        yield TestClient(create_app())
        SQLDatabaseConnector.close()

    def test_seeded_spending_and_cash_flow_totals(self, live_client: TestClient) -> None:
        """Create account + txn seed; assert report totals match expected amounts."""
        suffix = uuid.uuid4().hex[:8]
        token = _register_and_login(live_client, suffix=suffix)
        headers = _auth_headers(token)

        account = live_client.post(
            "/api/v1/accounts",
            headers=headers,
            json={
                "name": "Reports Wallet",
                "account_kind": "other_asset",
                "ledger_side": "asset",
                "currency": "USD",
                "initial_value": 0.0,
            },
        )
        assert account.status_code == 201, account.text
        account_id = account.json()["id"]

        category = live_client.post(
            "/api/v1/categories",
            headers=headers,
            json={"name": f"Reports Cat {suffix}", "category_type": "expense"},
        )
        assert category.status_code == 201, category.text
        category_id = category.json()["id"]

        income_cat = live_client.post(
            "/api/v1/categories",
            headers=headers,
            json={"name": f"Reports Income {suffix}", "category_type": "income"},
        )
        assert income_cat.status_code == 201, income_cat.text
        income_category_id = income_cat.json()["id"]

        income = live_client.post(
            "/api/v1/transactions",
            headers=headers,
            json={
                "account_id": account_id,
                "category_id": income_category_id,
                "transaction_type": "income",
                "amount": 500.0,
                "currency": "USD",
                "description": "seed income",
                "transaction_date": "2026-02-10",
            },
        )
        assert income.status_code == 201, income.text

        expense = live_client.post(
            "/api/v1/transactions",
            headers=headers,
            json={
                "account_id": account_id,
                "category_id": category_id,
                "transaction_type": "expense",
                "amount": 120.0,
                "currency": "USD",
                "description": "seed expense",
                "transaction_date": "2026-02-12",
            },
        )
        assert expense.status_code == 201, expense.text

        spending = live_client.get(
            "/api/v1/reports/spending",
            headers=headers,
            params={**_PERIOD, "account_id": account_id},
        )
        assert spending.status_code == 200, spending.text
        spending_payload = spending.json()
        assert spending_payload["total_income"] == 500.0
        assert spending_payload["total_spending"] == 120.0
        assert spending_payload["net_savings"] == 380.0

        cash_flow = live_client.get(
            "/api/v1/reports/cash-flow",
            headers=headers,
            params={**_PERIOD, "account_id": account_id, "refresh_balances": True},
        )
        assert cash_flow.status_code == 200, cash_flow.text
        cash_flow_payload = cash_flow.json()
        assert cash_flow_payload["total_inflows"] == 500.0
        assert cash_flow_payload["total_outflows"] == 120.0
        assert cash_flow_payload["net_cash_flow"] == 380.0

        export = live_client.get(
            "/api/v1/reports/export",
            headers=headers,
            params={
                "report_type": "spending",
                "format": "csv",
                **_PERIOD,
                "account_id": account_id,
            },
        )
        assert export.status_code == 200, export.text
        assert "expense_total" in export.text

        deferred = live_client.get("/api/v1/reports/budget-performance", headers=headers)
        assert deferred.status_code == 501

    def test_foreign_account_id_rejected(self, live_client: TestClient) -> None:
        """User B cannot run reports against User A's account_id."""
        suffix = uuid.uuid4().hex[:8]
        token_a = _register_and_login(live_client, suffix=f"{suffix}a")
        token_b = _register_and_login(live_client, suffix=f"{suffix}b")
        headers_a = _auth_headers(token_a)
        headers_b = _auth_headers(token_b)

        account = live_client.post(
            "/api/v1/accounts",
            headers=headers_a,
            json={
                "name": "Tenant A Wallet",
                "account_kind": "other_asset",
                "ledger_side": "asset",
                "currency": "USD",
                "initial_value": 0.0,
            },
        )
        assert account.status_code == 201, account.text
        account_id = account.json()["id"]

        cross = live_client.get(
            "/api/v1/reports/spending",
            headers=headers_b,
            params={**_PERIOD, "account_id": account_id},
        )
        assert cross.status_code == 400
        assert "tenant" in cross.json()["detail"].lower()
