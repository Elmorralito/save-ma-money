"""B1 Supabase pooler smoke tests (PPT-036 / PPT-033 §8).

Runs only when ``DATABASE_URL`` targets a reachable Supabase transaction pooler
(``:6543`` or ``pooler.supabase.com``). Local Docker Postgres (B0) skips these tests.
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
from postgres_gate import postgres_url, requires_supabase_b1

POSTGRES_URL = postgres_url()

_VALID_PASSWORD = "SecurePass1!"


@requires_supabase_b1
class TestSupabaseB1Smoke:
    """Minimal B1 validation: DB ping + authenticated accounts list."""

    @pytest.fixture(scope="class")
    def b1_client(self):
        """API client bound to Supabase pooler via ``DATABASE_URL``."""
        SQLDatabaseConnector.close()
        SQLDatabaseConnector.establish(connection={"url": POSTGRES_URL})
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

    def test_accounts_list_after_register(self, b1_client: TestClient) -> None:
        """One CRUD-adjacent path: register, login, list accounts (empty OK)."""
        suffix = uuid.uuid4().hex[:8]
        register_payload = {
            "username": f"b1_smoke_{suffix}",
            "email": f"b1_smoke_{suffix}@example.local",
            "password": _VALID_PASSWORD,
        }
        reg = b1_client.post("/api/v1/auth/register", json=register_payload)
        assert reg.status_code == 201, reg.text

        login = b1_client.post(
            "/api/v1/auth/login",
            data={"username": register_payload["username"], "password": _VALID_PASSWORD},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]

        listed = b1_client.get(
            "/api/v1/accounts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert listed.status_code == 200
        payload = listed.json()
        assert "items" in payload
        assert isinstance(payload["items"], list)
