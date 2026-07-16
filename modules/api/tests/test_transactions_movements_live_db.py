"""Live-DB CRUD + tenancy tests for transactions and movements (PPT-037 / PPT-040, B0).

API-layer companion to model ``test_owned_table_repository.py`` (NFR-04): user B
must not read or mutate user A's ledger rows through HTTP (404).
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


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(client: TestClient, *, suffix: str, label: str) -> str:
    """Register a throwaway tenant and return a bearer access token."""
    payload = {
        "username": f"ppt040_{label}_{suffix}",
        "email": f"ppt040_{label}_{suffix}@example.local",
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


def _create_wallet(client: TestClient, headers: dict[str, str], *, name: str) -> str:
    """Create an other_asset account and return its id."""
    response = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "name": name,
            "account_kind": "other_asset",
            "ledger_side": "asset",
            "currency": "USD",
            "initial_value": 1_000.0,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_category(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str,
    category_type: str,
) -> str:
    """Create a category and return its id."""
    response = client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": name, "category_type": category_type},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@requires_postgres
class TestTransactionsMovementsLiveDb:
    """End-to-end transaction/movement HTTP against PostgreSQL (NFR-04)."""

    @pytest.fixture(scope="class")
    def live_client(self):
        """API client bound to live Postgres via ``DATABASE_URL``."""
        SQLDatabaseConnector.close()
        SQLDatabaseConnector.establish(connection={"url": POSTGRES_URL})
        UsersService.ensure_password_manager()
        get_settings.cache_clear()
        os.environ["DATABASE_URL"] = str(POSTGRES_URL)
        os.environ.setdefault("AUTH_PROVIDER", "local")
        yield TestClient(create_app())
        SQLDatabaseConnector.close()

    def test_transactions_crud_lifecycle(self, live_client: TestClient) -> None:
        """Create, list, get, update, and soft-delete an expense via HTTP."""
        suffix = uuid.uuid4().hex[:8]
        token = _register_and_login(live_client, suffix=suffix, label="txn")
        headers = _auth_headers(token)
        account_id = _create_wallet(live_client, headers, name="Txn Wallet")
        category_id = _create_category(
            live_client,
            headers,
            name=f"Txn Cat {suffix}",
            category_type="expense",
        )

        create_response = live_client.post(
            "/api/v1/transactions",
            headers=headers,
            json={
                "account_id": account_id,
                "category_id": category_id,
                "transaction_type": "expense",
                "amount": 42.5,
                "currency": "USD",
                "description": "B0 live expense",
                "transaction_date": "2026-03-15",
            },
        )
        assert create_response.status_code == 201, create_response.text
        created = create_response.json()
        transaction_id = created["id"]
        assert created["transaction_type"] == "expense"
        assert created["amount"] == 42.5

        list_response = live_client.get("/api/v1/transactions", headers=headers)
        assert list_response.status_code == 200
        list_payload = list_response.json()
        assert list_payload["total"] >= 1
        assert any(item["id"] == transaction_id for item in list_payload["items"])

        get_response = live_client.get(f"/api/v1/transactions/{transaction_id}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["description"] == "B0 live expense"

        update_response = live_client.put(
            f"/api/v1/transactions/{transaction_id}",
            headers=headers,
            json={"description": "B0 live expense updated", "amount": 50.0},
        )
        assert update_response.status_code == 200, update_response.text
        assert update_response.json()["description"] == "B0 live expense updated"
        assert update_response.json()["amount"] == 50.0

        delete_response = live_client.delete(f"/api/v1/transactions/{transaction_id}", headers=headers)
        assert delete_response.status_code == 204

        missing_response = live_client.get(f"/api/v1/transactions/{transaction_id}", headers=headers)
        assert missing_response.status_code == 404

    def test_movements_transfer_lifecycle(self, live_client: TestClient) -> None:
        """Create an immediate transfer via movements alias and read it back."""
        suffix = uuid.uuid4().hex[:8]
        token = _register_and_login(live_client, suffix=suffix, label="mov")
        headers = _auth_headers(token)
        source_id = _create_wallet(live_client, headers, name="Source Wallet")
        dest_id = _create_wallet(live_client, headers, name="Dest Wallet")

        create_response = live_client.post(
            "/api/v1/movements",
            headers=headers,
            json={
                "source_account_id": source_id,
                "destination_account_id": dest_id,
                "amount": 75.0,
                "currency": "USD",
                "movement_date": "2026-03-16",
                "description": "B0 live transfer",
                "scheduled": False,
            },
        )
        assert create_response.status_code == 201, create_response.text
        created = create_response.json()
        movement_id = created["id"]
        assert created["amount"] == 75.0
        assert created["status"] == "completed"

        list_response = live_client.get("/api/v1/movements", headers=headers)
        assert list_response.status_code == 200
        assert any(item["id"] == movement_id for item in list_response.json()["items"])

        get_response = live_client.get(f"/api/v1/movements/{movement_id}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["source_account_id"] == source_id
        assert get_response.json()["destination_account_id"] == dest_id

        # Transfers are excluded from default transaction list.
        txn_list = live_client.get("/api/v1/transactions", headers=headers)
        assert txn_list.status_code == 200
        assert all(item["id"] != movement_id for item in txn_list.json()["items"])

    def test_cross_tenant_transaction_returns_404(self, live_client: TestClient) -> None:
        """User B cannot read User A's transaction through the API."""
        suffix = uuid.uuid4().hex[:8]
        token_a = _register_and_login(live_client, suffix=suffix, label="ta")
        token_b = _register_and_login(live_client, suffix=suffix, label="tb")
        headers_a = _auth_headers(token_a)
        headers_b = _auth_headers(token_b)

        account_id = _create_wallet(live_client, headers_a, name="Tenant A Wallet")
        category_id = _create_category(
            live_client,
            headers_a,
            name=f"Tenant A Cat {suffix}",
            category_type="expense",
        )
        create_response = live_client.post(
            "/api/v1/transactions",
            headers=headers_a,
            json={
                "account_id": account_id,
                "category_id": category_id,
                "transaction_type": "expense",
                "amount": 10.0,
                "currency": "USD",
                "description": "private",
                "transaction_date": "2026-03-17",
            },
        )
        assert create_response.status_code == 201, create_response.text
        transaction_id = create_response.json()["id"]

        cross_get = live_client.get(
            f"/api/v1/transactions/{transaction_id}",
            headers=headers_b,
        )
        assert cross_get.status_code == 404

        cross_delete = live_client.delete(
            f"/api/v1/transactions/{transaction_id}",
            headers=headers_b,
        )
        assert cross_delete.status_code == 404

    def test_cross_tenant_movement_returns_404(self, live_client: TestClient) -> None:
        """User B cannot read User A's movement through the API."""
        suffix = uuid.uuid4().hex[:8]
        token_a = _register_and_login(live_client, suffix=suffix, label="ma")
        token_b = _register_and_login(live_client, suffix=suffix, label="mb")
        headers_a = _auth_headers(token_a)
        headers_b = _auth_headers(token_b)

        source_id = _create_wallet(live_client, headers_a, name="A Source")
        dest_id = _create_wallet(live_client, headers_a, name="A Dest")
        create_response = live_client.post(
            "/api/v1/movements",
            headers=headers_a,
            json={
                "source_account_id": source_id,
                "destination_account_id": dest_id,
                "amount": 25.0,
                "currency": "USD",
                "movement_date": "2026-03-18",
                "scheduled": False,
            },
        )
        assert create_response.status_code == 201, create_response.text
        movement_id = create_response.json()["id"]

        cross_get = live_client.get(f"/api/v1/movements/{movement_id}", headers=headers_b)
        assert cross_get.status_code == 404

        cross_delete = live_client.delete(f"/api/v1/movements/{movement_id}", headers=headers_b)
        assert cross_delete.status_code == 404
