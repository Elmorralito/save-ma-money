"""Live-DB CRUD tests for accounts and categories endpoints (PPT-036, B0)."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "model" / "tests"))

from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.main import create_app
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.services.users import UsersService
from postgres_gate import postgres_url, requires_postgres

POSTGRES_URL = postgres_url()

_VALID_PASSWORD = "SecurePass1!"


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_user(client: TestClient, *, suffix: str, label: str) -> dict[str, str]:
    """Register a tenant user and return the registration payload."""
    payload = {
        "username": f"ppt036_{label}_{suffix}",
        "email": f"ppt036_{label}_{suffix}@example.local",
        "password": _VALID_PASSWORD,
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return payload


def _login_token(client: TestClient, username: str) -> str:
    """Log in and return a bearer access token."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": _VALID_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@requires_postgres
class TestAccountsCategoriesLiveDb:
    """End-to-end account and category CRUD against PostgreSQL (NFR-04)."""

    @pytest.fixture(scope="class")
    def postgres_connector(self):
        """Session-scoped PostgreSQL connector."""
        SQLDatabaseConnector.close()
        SQLDatabaseConnector.establish(connection={"url": POSTGRES_URL})
        UsersService.ensure_password_manager()
        yield SQLDatabaseConnector
        SQLDatabaseConnector.close()

    @pytest.fixture
    def live_client(self, postgres_connector) -> TestClient:
        """API client bound to live Postgres via ``DATABASE_URL``."""
        get_settings.cache_clear()
        os.environ["DATABASE_URL"] = str(POSTGRES_URL)
        return TestClient(create_app())

    def test_accounts_crud_lifecycle(self, live_client: TestClient) -> None:
        """Create, read, update, balance, and soft-delete an account via HTTP."""
        suffix = uuid.uuid4().hex[:8]
        user = _register_user(live_client, suffix=suffix, label="acct")
        token = _login_token(live_client, user["username"])
        headers = _auth_headers(token)

        create_response = live_client.post(
            "/api/v1/accounts",
            headers=headers,
            json={
                "name": "Live Wallet",
                "description": "B0 integration",
                "account_kind": "other_asset",
                "ledger_side": "asset",
                "currency": "USD",
                "initial_value": 100.0,
            },
        )
        assert create_response.status_code == 201, create_response.text
        created = create_response.json()
        account_id = created["id"]
        assert created["account_kind"] == "other_asset"
        assert created["currency"] == "USD"

        list_response = live_client.get("/api/v1/accounts", headers=headers)
        assert list_response.status_code == 200
        list_payload = list_response.json()
        assert list_payload["total"] >= 1
        assert any(item["id"] == account_id for item in list_payload["items"])

        get_response = live_client.get(f"/api/v1/accounts/{account_id}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Live Wallet"

        balance_response = live_client.get(f"/api/v1/accounts/{account_id}/balance", headers=headers)
        assert balance_response.status_code == 200
        balance_payload = balance_response.json()
        assert balance_payload["account_id"] == account_id
        assert balance_payload["currency"] == "USD"
        assert balance_payload["balance"] == 100.0

        update_response = live_client.put(
            f"/api/v1/accounts/{account_id}",
            headers=headers,
            json={"name": "Live Wallet Updated"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Live Wallet Updated"

        delete_response = live_client.delete(f"/api/v1/accounts/{account_id}", headers=headers)
        assert delete_response.status_code == 204

        missing_response = live_client.get(f"/api/v1/accounts/{account_id}", headers=headers)
        assert missing_response.status_code == 404

    def test_accounts_create_with_banking_extension(self, live_client: TestClient) -> None:
        """Create a checking account with required banking extension details."""
        suffix = uuid.uuid4().hex[:8]
        user = _register_user(live_client, suffix=suffix, label="bank")
        token = _login_token(live_client, user["username"])
        headers = _auth_headers(token)

        response = live_client.post(
            "/api/v1/accounts",
            headers=headers,
            json={
                "name": "Live Checking",
                "account_kind": "checking",
                "ledger_side": "asset",
                "currency": "USD",
                "banking_details": {"entity": "Integration Bank", "account_number": "1234"},
            },
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["banking_details"]["entity"] == "Integration Bank"

        live_client.delete(f"/api/v1/accounts/{payload['id']}", headers=headers)

    def test_categories_crud_lifecycle(self, live_client: TestClient) -> None:
        """Create, read, update, list with hierarchy, and delete a category via HTTP."""
        suffix = uuid.uuid4().hex[:8]
        user = _register_user(live_client, suffix=suffix, label="cat")
        token = _login_token(live_client, user["username"])
        headers = _auth_headers(token)

        parent_response = live_client.post(
            "/api/v1/categories",
            headers=headers,
            json={
                "name": "Live Food",
                "description": "Meals",
                "category_type": "expense",
                "icon": "utensils",
                "color": "#FF5733",
            },
        )
        assert parent_response.status_code == 201, parent_response.text
        parent_id = parent_response.json()["id"]

        child_response = live_client.post(
            "/api/v1/categories",
            headers=headers,
            json={
                "name": "Live Restaurants",
                "description": "Dining out",
                "category_type": "expense",
                "parent_id": parent_id,
            },
        )
        assert child_response.status_code == 201, child_response.text

        list_response = live_client.get("/api/v1/categories", headers=headers)
        assert list_response.status_code == 200
        list_payload = list_response.json()
        parent_row = next(item for item in list_payload["items"] if item["id"] == parent_id)
        assert any(sub["name"] == "Live Restaurants" for sub in parent_row["subcategories"])

        get_response = live_client.get(f"/api/v1/categories/{parent_id}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["category_type"] == "expense"

        update_response = live_client.put(
            f"/api/v1/categories/{parent_id}",
            headers=headers,
            json={"name": "Live Food Updated"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Live Food Updated"

        delete_child = live_client.delete(f"/api/v1/categories/{child_response.json()['id']}", headers=headers)
        assert delete_child.status_code == 204

        delete_parent = live_client.delete(f"/api/v1/categories/{parent_id}", headers=headers)
        assert delete_parent.status_code == 204

        missing_response = live_client.get(f"/api/v1/categories/{parent_id}", headers=headers)
        assert missing_response.status_code == 404

    def test_cross_tenant_account_returns_404(self, live_client: TestClient) -> None:
        """User B cannot read User A's account through the API."""
        suffix = uuid.uuid4().hex[:8]
        user_a = _register_user(live_client, suffix=suffix, label="a")
        user_b = _register_user(live_client, suffix=suffix, label="b")
        token_a = _login_token(live_client, user_a["username"])
        token_b = _login_token(live_client, user_b["username"])

        create_response = live_client.post(
            "/api/v1/accounts",
            headers=_auth_headers(token_a),
            json={
                "name": "Tenant A Only",
                "account_kind": "other_asset",
                "ledger_side": "asset",
                "currency": "USD",
            },
        )
        assert create_response.status_code == 201
        account_id = create_response.json()["id"]

        cross_tenant_response = live_client.get(
            f"/api/v1/accounts/{account_id}",
            headers=_auth_headers(token_b),
        )
        assert cross_tenant_response.status_code == 404

    def test_cross_tenant_category_returns_404(self, live_client: TestClient) -> None:
        """User B cannot read User A's category through the API."""
        suffix = uuid.uuid4().hex[:8]
        user_a = _register_user(live_client, suffix=suffix, label="ca")
        user_b = _register_user(live_client, suffix=suffix, label="cb")
        token_a = _login_token(live_client, user_a["username"])
        token_b = _login_token(live_client, user_b["username"])

        create_response = live_client.post(
            "/api/v1/categories",
            headers=_auth_headers(token_a),
            json={"name": "Tenant A Category", "category_type": "expense"},
        )
        assert create_response.status_code == 201
        category_id = create_response.json()["id"]

        cross_tenant_response = live_client.get(
            f"/api/v1/categories/{category_id}",
            headers=_auth_headers(token_b),
        )
        assert cross_tenant_response.status_code == 404

    def test_global_category_put_delete_returns_404(self, live_client: TestClient, postgres_connector) -> None:
        """Global seed categories are readable but not mutable by tenants (G7)."""
        suffix = uuid.uuid4().hex[:8]
        user = _register_user(live_client, suffix=suffix, label="global")
        token = _login_token(live_client, user["username"])
        headers = _auth_headers(token)

        global_id = uuid.uuid4()
        with Session(postgres_connector.engine) as session:
            session.execute(
                text(
                    """
                    INSERT INTO papita_transactions.categories
                        (id, owner_id, parent_id, name, category_kind, description, tags, active, created_at, updated_at)
                    VALUES
                        (:id, NULL, NULL, :name, 'EXPENSE', 'seed', '{global,seed}', true, NOW(), NOW())
                    """
                ),
                {"id": str(global_id), "name": f"Global Seed {suffix}"},
            )
            session.commit()

        try:
            get_response = live_client.get(f"/api/v1/categories/{global_id}", headers=headers)
            assert get_response.status_code == 200
            assert get_response.json()["name"] == f"Global Seed {suffix}"

            put_response = live_client.put(
                f"/api/v1/categories/{global_id}",
                headers=headers,
                json={"name": "Tampered"},
            )
            assert put_response.status_code == 404

            delete_response = live_client.delete(f"/api/v1/categories/{global_id}", headers=headers)
            assert delete_response.status_code == 404
        finally:
            with Session(postgres_connector.engine) as session:
                session.execute(
                    text("DELETE FROM papita_transactions.categories WHERE id = :id"),
                    {"id": str(global_id)},
                )
                session.commit()

    def test_account_list_filter_by_kind(self, live_client: TestClient) -> None:
        """GET /accounts honors the account_kind query filter."""
        suffix = uuid.uuid4().hex[:8]
        user = _register_user(live_client, suffix=suffix, label="filter")
        token = _login_token(live_client, user["username"])
        headers = _auth_headers(token)

        cash_response = live_client.post(
            "/api/v1/accounts",
            headers=headers,
            json={
                "name": "Filter Cash",
                "account_kind": "cash",
                "ledger_side": "asset",
                "currency": "USD",
                "banking_details": {"entity": "Cash Entity"},
            },
        )
        assert cash_response.status_code == 201, cash_response.text

        other_response = live_client.post(
            "/api/v1/accounts",
            headers=headers,
            json={
                "name": "Filter Other",
                "account_kind": "other_asset",
                "ledger_side": "asset",
                "currency": "USD",
            },
        )
        assert other_response.status_code == 201, other_response.text

        filtered = live_client.get("/api/v1/accounts?account_kind=cash", headers=headers)
        assert filtered.status_code == 200
        items = filtered.json()["items"]
        assert items
        assert all(item["account_kind"] == "cash" for item in items)

        live_client.delete(f"/api/v1/accounts/{cash_response.json()['id']}", headers=headers)
        live_client.delete(f"/api/v1/accounts/{other_response.json()['id']}", headers=headers)
