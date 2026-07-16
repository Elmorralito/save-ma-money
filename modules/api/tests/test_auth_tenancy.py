"""Live-DB tenancy tests for auth + cross-tenant isolation (NFR-04).

HTTP-layer companion to model ``test_owned_table_repository.py``: register/login
two tenants and prove User B cannot resolve User A's owned rows.
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
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.accounts.repository import AccountsRepository
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.model.enums import AccountKind, LedgerSide
from papita_txnsmodel.services.users import UsersService
from postgres_gate import postgres_url, requires_postgres

POSTGRES_URL = postgres_url()

_VALID_PASSWORD = "SecurePass1!"
_REGISTER = {
    "username": "ppt035_usera",
    "email": "ppt035_usera@example.local",
    "password": _VALID_PASSWORD,
}
_REGISTER_B = {
    "username": "ppt035_userb",
    "email": "ppt035_userb@example.local",
    "password": _VALID_PASSWORD,
}


@requires_postgres
class TestAuthTenancyLiveDb:
    """Register/login on Postgres and prove cross-tenant reads return no row (404 in routers)."""

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
        """API client bound to live Postgres via Settings DATABASE_URL."""
        get_settings.cache_clear()
        os.environ["DATABASE_URL"] = str(POSTGRES_URL)
        return TestClient(create_app())

    def test_register_login_and_cross_tenant_account_isolation(self, live_client: TestClient) -> None:
        suffix = uuid.uuid4().hex[:8]
        user_a = {**_REGISTER, "username": f"ppt035_a_{suffix}", "email": f"ppt035_a_{suffix}@example.local"}
        user_b = {**_REGISTER_B, "username": f"ppt035_b_{suffix}", "email": f"ppt035_b_{suffix}@example.local"}

        assert live_client.post("/api/v1/auth/register", json=user_a).status_code == 201
        assert live_client.post("/api/v1/auth/register", json=user_b).status_code == 201

        login_a = live_client.post(
            "/api/v1/auth/login",
            data={"username": user_a["username"], "password": _VALID_PASSWORD},
        )
        assert login_a.status_code == 200
        token_a = login_a.json()["access_token"]

        me_a = live_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})
        assert me_a.status_code == 200
        owner_a_id = me_a.json()["id"]

        login_b = live_client.post(
            "/api/v1/auth/login",
            data={"username": user_b["username"], "password": _VALID_PASSWORD},
        )
        assert login_b.status_code == 200
        me_b = live_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {login_b.json()['access_token']}"},
        )
        assert me_b.status_code == 200

        users_service = UsersService.model_validate({"connector": SQLDatabaseConnector})
        owner_a = users_service.get_owner(owner_a_id)
        owner_b = users_service.get_owner(me_b.json()["id"])
        assert owner_a is not None
        assert owner_b is not None

        account_id = uuid.uuid4()
        AccountsRepository().upsert_record(
            AccountsDTO(
                id=account_id,
                name="Tenant A account",
                description="isolated",
                owner_id=owner_a.id,
                account_kind=AccountKind.CASH,
                ledger_side=LedgerSide.ASSET,
            ),
            owner=owner_a,
        )

        record = AccountsRepository().get_record_by_id(account_id, owner=owner_b, dto_type=AccountsDTO)
        assert record is None
