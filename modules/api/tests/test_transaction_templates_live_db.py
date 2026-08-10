"""Live-DB CRUD + dues tests for transaction-templates (PPT-073 / #166, B0).

API-layer companion to model ``test_ppt072_dues_live_db.py``. User B must not
read or mutate user A's templates through HTTP (404). Skipped unless
``DATABASE_URL`` points at reachable PostgreSQL.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "model" / "tests"))

from postgres_gate import postgres_url, requires_postgres

from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.dependencies.services import (
    clear_transaction_templates_service_cache,
    clear_transactions_service_cache,
)
from papita_txnsapi.main import create_app
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.services.users import UsersService

POSTGRES_URL = postgres_url()

_VALID_PASSWORD = "SecurePass1!"


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(client: TestClient, *, suffix: str, label: str) -> str:
    """Register a throwaway tenant and return a bearer access token."""
    payload = {
        "username": f"ppt073_{label}_{suffix}",
        "email": f"ppt073_{label}_{suffix}@example.local",
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
    category_type: str = "expense",
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
class TestTransactionTemplatesLiveDb:
    """End-to-end template CRUD / dues HTTP against PostgreSQL (NFR-04)."""

    @pytest.fixture(scope="class")
    def live_client(self):
        """API client bound to live Postgres via ``DATABASE_URL``.

        Pin ``REDIS_ENABLED=false`` so JWT denylist does not fail-closed when the
        developer ``.env`` enables Redis but TestClient has no Redis pool
        (Compose API uses Redis; B0 pytest posture matches unit tests).
        """
        previous_redis = os.environ.get("REDIS_ENABLED")
        SQLDatabaseConnector.close()
        SQLDatabaseConnector.establish(connection={"url": POSTGRES_URL})
        UsersService.ensure_password_manager()
        clear_transactions_service_cache()
        clear_transaction_templates_service_cache()
        os.environ["DATABASE_URL"] = str(POSTGRES_URL)
        os.environ.setdefault("AUTH_PROVIDER", "local")
        os.environ["REDIS_ENABLED"] = "false"
        get_settings.cache_clear()
        yield TestClient(create_app())
        SQLDatabaseConnector.close()
        clear_transactions_service_cache()
        clear_transaction_templates_service_cache()
        if previous_redis is None:
            os.environ.pop("REDIS_ENABLED", None)
        else:
            os.environ["REDIS_ENABLED"] = previous_redis
        get_settings.cache_clear()

    def test_templates_crud_lifecycle(self, live_client: TestClient) -> None:
        """Create, list (with filter), get, update, and soft-delete a template."""
        suffix = uuid.uuid4().hex[:8]
        token = _register_and_login(live_client, suffix=suffix, label="crud")
        headers = _auth_headers(token)
        account_id = _create_wallet(live_client, headers, name=f"Tpl Wallet {suffix}")
        category_id = _create_category(live_client, headers, name=f"Tpl Cat {suffix}")
        other_category_id = _create_category(live_client, headers, name=f"Other Cat {suffix}")

        create_response = live_client.post(
            "/api/v1/transaction-templates",
            headers=headers,
            json={
                "name": "Rent",
                "description": "B0 live template",
                "category_id": category_id,
                "planned_amount": 1200.0,
                "planned_day": 1,
                "remind_days_before": 3,
                "from_account_id": account_id,
            },
        )
        assert create_response.status_code == 201, create_response.text
        created = create_response.json()
        template_id = created["id"]
        assert created["name"] == "Rent"
        assert created["remind_days_before"] == 3
        assert created["from_account_id"] == account_id

        # Noise row for category filter assertion.
        noise = live_client.post(
            "/api/v1/transaction-templates",
            headers=headers,
            json={
                "name": "Noise",
                "category_id": other_category_id,
                "planned_amount": 10.0,
                "planned_day": 5,
                "from_account_id": account_id,
            },
        )
        assert noise.status_code == 201, noise.text

        list_response = live_client.get("/api/v1/transaction-templates", headers=headers)
        assert list_response.status_code == 200, list_response.text
        list_payload = list_response.json()
        assert list_payload["total"] >= 2
        assert any(item["id"] == template_id for item in list_payload["items"])

        filtered = live_client.get(
            "/api/v1/transaction-templates",
            headers=headers,
            params={"category_id": category_id},
        )
        assert filtered.status_code == 200
        filtered_ids = {item["id"] for item in filtered.json()["items"]}
        assert template_id in filtered_ids
        assert noise.json()["id"] not in filtered_ids

        get_response = live_client.get(f"/api/v1/transaction-templates/{template_id}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["description"] == "B0 live template"

        update_response = live_client.put(
            f"/api/v1/transaction-templates/{template_id}",
            headers=headers,
            json={"name": "Rent updated", "planned_amount": 1250.0},
        )
        assert update_response.status_code == 200, update_response.text
        assert update_response.json()["name"] == "Rent updated"
        assert update_response.json()["planned_amount"] == 1250.0

        delete_response = live_client.delete(
            f"/api/v1/transaction-templates/{template_id}",
            headers=headers,
        )
        assert delete_response.status_code == 204

        missing_response = live_client.get(
            f"/api/v1/transaction-templates/{template_id}",
            headers=headers,
        )
        assert missing_response.status_code == 404

    def test_upcoming_dues_mark_paid_clear_paid_round_trip(self, live_client: TestClient) -> None:
        """Upcoming dues window + mark-paid / clear-paid against B0 Postgres."""
        suffix = uuid.uuid4().hex[:8]
        token = _register_and_login(live_client, suffix=suffix, label="dues")
        headers = _auth_headers(token)
        account_id = _create_wallet(live_client, headers, name=f"Dues Wallet {suffix}")
        category_id = _create_category(live_client, headers, name=f"Dues Cat {suffix}")

        create_response = live_client.post(
            "/api/v1/transaction-templates",
            headers=headers,
            json={
                "name": f"PPT073 rent {suffix}",
                "category_id": category_id,
                "planned_amount": 99.5,
                "planned_day": 12,
                "use_month_end": False,
                "remind_days_before": 0,
                "from_account_id": account_id,
            },
        )
        assert create_response.status_code == 201, create_response.text
        template_id = create_response.json()["id"]

        upcoming = live_client.get(
            "/api/v1/transaction-templates/upcoming-dues",
            headers=headers,
            params={"as_of": "2026-08-10", "window_days": 7, "include_paid": True},
        )
        assert upcoming.status_code == 200, upcoming.text
        payload = upcoming.json()
        assert payload["as_of"] == "2026-08-10"
        matched = [row for row in payload["items"] if row["template"]["id"] == template_id]
        assert len(matched) == 1
        assert matched[0]["due_date"] == "2026-08-12"
        assert matched[0]["is_paid"] is False

        mark = live_client.post(
            f"/api/v1/transaction-templates/{template_id}/mark-paid",
            headers=headers,
            json={"as_of": "2026-08-10"},
        )
        assert mark.status_code == 201, mark.text
        posted = mark.json()
        assert posted["template_id"] == template_id
        assert posted["amount"] == 99.5
        assert posted["transaction_type"] == "expense"

        paid_upcoming = live_client.get(
            "/api/v1/transaction-templates/upcoming-dues",
            headers=headers,
            params={"as_of": "2026-08-10", "window_days": 7},
        )
        assert paid_upcoming.status_code == 200
        paid_row = next(row for row in paid_upcoming.json()["items"] if row["template"]["id"] == template_id)
        assert paid_row["is_paid"] is True
        assert paid_row["paid_transaction_id"] == posted["id"]

        conflict = live_client.post(
            f"/api/v1/transaction-templates/{template_id}/mark-paid",
            headers=headers,
            json={"as_of": "2026-08-10"},
        )
        assert conflict.status_code == 409

        clear = live_client.post(
            f"/api/v1/transaction-templates/{template_id}/clear-paid",
            headers=headers,
            json={"as_of": "2026-08-10"},
        )
        assert clear.status_code == 200, clear.text
        assert clear.json()["id"] == posted["id"]

        after_clear = live_client.get(
            "/api/v1/transaction-templates/upcoming-dues",
            headers=headers,
            params={"as_of": "2026-08-10", "window_days": 7},
        )
        unpaid = next(row for row in after_clear.json()["items"] if row["template"]["id"] == template_id)
        assert unpaid["is_paid"] is False

    def test_cross_tenant_template_returns_404(self, live_client: TestClient) -> None:
        """User B cannot read, mark-paid, or delete user A's template."""
        suffix = uuid.uuid4().hex[:8]
        token_a = _register_and_login(live_client, suffix=suffix, label="ta")
        token_b = _register_and_login(live_client, suffix=suffix, label="tb")
        headers_a = _auth_headers(token_a)
        headers_b = _auth_headers(token_b)

        account_id = _create_wallet(live_client, headers_a, name=f"A Wallet {suffix}")
        category_id = _create_category(live_client, headers_a, name=f"A Cat {suffix}")
        create_response = live_client.post(
            "/api/v1/transaction-templates",
            headers=headers_a,
            json={
                "name": "Private due",
                "category_id": category_id,
                "planned_amount": 40.0,
                "planned_day": 12,
                "remind_days_before": 0,
                "from_account_id": account_id,
            },
        )
        assert create_response.status_code == 201, create_response.text
        template_id = create_response.json()["id"]

        cross_get = live_client.get(
            f"/api/v1/transaction-templates/{template_id}",
            headers=headers_b,
        )
        assert cross_get.status_code == 404

        cross_mark = live_client.post(
            f"/api/v1/transaction-templates/{template_id}/mark-paid",
            headers=headers_b,
            json={"as_of": "2026-08-10"},
        )
        assert cross_mark.status_code == 404

        cross_delete = live_client.delete(
            f"/api/v1/transaction-templates/{template_id}",
            headers=headers_b,
        )
        assert cross_delete.status_code == 404

        other_upcoming = live_client.get(
            "/api/v1/transaction-templates/upcoming-dues",
            headers=headers_b,
            params={"as_of": "2026-08-10", "window_days": 7},
        )
        assert other_upcoming.status_code == 200
        assert all(row["template"]["id"] != template_id for row in other_upcoming.json()["items"])
