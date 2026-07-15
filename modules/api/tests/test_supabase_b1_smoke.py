"""B1 Supabase pooler smoke tests (PPT-039 / PPT-036 / PPT-033 §8).

Runs only when ``DATABASE_URL`` targets a reachable Supabase transaction pooler
(``:6543`` or ``pooler.supabase.com``). Local Docker Postgres (B0) skips these tests.

One-liner (from repo root; values never commit)::

    DATABASE_URL="<pooler>" JWT_SECRET_KEY="…" \\
      poetry run pytest modules/api/tests/test_supabase_b1_smoke.py -q

Or ``make b1-smoke`` when those env vars are already exported.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "model" / "tests"))

from postgres_gate import postgres_url, requires_supabase_b1

from papita_txnsapi.config.settings import get_settings, postgres_engine_kwargs
from papita_txnsapi.main import create_app
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.services.users import UsersService

POSTGRES_URL = postgres_url()

_VALID_PASSWORD = "SecurePass1!"


def _register_and_login(client: TestClient, *, prefix: str) -> str:
    """Register a throwaway user and return a bearer access token."""
    suffix = uuid.uuid4().hex[:8]
    register_payload = {
        "username": f"{prefix}_{suffix}",
        "email": f"{prefix}_{suffix}@example.local",
        "password": _VALID_PASSWORD,
    }
    reg = client.post("/api/v1/auth/register", json=register_payload)
    assert reg.status_code == 201, reg.text

    login = client.post(
        "/api/v1/auth/login",
        data={"username": register_payload["username"], "password": _VALID_PASSWORD},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


@requires_supabase_b1
class TestSupabaseB1Smoke:
    """Minimal B1 validation: health + auth + domain list probes."""

    @pytest.fixture(scope="class")
    def b1_client(self):
        """API client bound to Supabase pooler via ``DATABASE_URL``."""
        assert POSTGRES_URL is not None
        SQLDatabaseConnector.close()
        SQLDatabaseConnector.establish(
            connection={"url": POSTGRES_URL},
            **postgres_engine_kwargs(url=POSTGRES_URL, pool_size=5),
        )
        UsersService.ensure_password_manager()
        get_settings.cache_clear()
        os.environ["DATABASE_URL"] = str(POSTGRES_URL)
        yield TestClient(create_app())
        SQLDatabaseConnector.close()

    def test_health_ready_returns_200(self, b1_client: TestClient) -> None:
        """``GET /health/ready`` succeeds against the pooler."""
        response = b1_client.get("/api/v1/health/ready")
        assert response.status_code == 200
        assert response.json().get("ready") is True

    def test_health_database_returns_200(self, b1_client: TestClient) -> None:
        """``GET /health/database`` succeeds against the pooler."""
        response = b1_client.get("/api/v1/health/database")
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload.get("status") == "healthy"
        assert payload.get("connected") is True

    def test_accounts_list_after_register(self, b1_client: TestClient) -> None:
        """One CRUD-adjacent path: register, login, list accounts (empty OK)."""
        token = _register_and_login(b1_client, prefix="b1_smoke")
        listed = b1_client.get(
            "/api/v1/accounts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert listed.status_code == 200
        payload = listed.json()
        assert "items" in payload
        assert isinstance(payload["items"], list)

    def test_categories_list_after_register(self, b1_client: TestClient) -> None:
        """Categories list over pooler (empty tenant tree OK)."""
        token = _register_and_login(b1_client, prefix="b1_cat")
        listed = b1_client.get(
            "/api/v1/categories",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert listed.status_code == 200, listed.text
        payload = listed.json()
        assert "items" in payload
        assert isinstance(payload["items"], list)

    def test_transactions_list_after_register(self, b1_client: TestClient) -> None:
        """Transactions list over pooler (empty OK; TRANSFER excluded by default)."""
        token = _register_and_login(b1_client, prefix="b1_txn")
        listed = b1_client.get(
            "/api/v1/transactions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert listed.status_code == 200, listed.text
        payload = listed.json()
        assert "items" in payload
        assert isinstance(payload["items"], list)

    def test_reports_spending_after_register(self, b1_client: TestClient) -> None:
        """PPT-038 B1 probe: authenticated empty spending report via pooler."""
        token = _register_and_login(b1_client, prefix="b1_rpt")
        report = b1_client.get(
            "/api/v1/reports/spending",
            headers={"Authorization": f"Bearer {token}"},
            params={"start_date": "2026-02-01", "end_date": "2026-02-28"},
        )
        assert report.status_code == 200, report.text
        payload = report.json()
        assert payload["total_spending"] == 0.0
        assert payload["total_income"] == 0.0
        assert payload["breakdown"] == []
