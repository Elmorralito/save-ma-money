"""Tests for account endpoints (PPT-036)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
from fastapi.testclient import TestClient

from auth_helpers import make_user
from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.services import get_accounts_service
from papita_txnsapi.main import create_app
from papita_txnsmodel.access.account_balances.dto import AccountBalancesDTO
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.model.enums import AccountKind, LedgerSide


def _sample_account(owner_id: uuid.UUID) -> AccountsDTO:
    now = datetime.now(timezone.utc)
    return AccountsDTO(
        id=uuid.uuid4(),
        name="Main Checking",
        description="Primary",
        owner_id=owner_id,
        account_kind=AccountKind.CHECKING,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
        created_at=now,
        updated_at=now,
    )


class TestAccountsAuth:
    """Protected route contract."""

    def test_list_accounts_without_token_returns_401(self, client: TestClient) -> None:
        response = client.get("/api/v1/accounts")
        assert response.status_code == 401


class TestAccountsRoutes:
    """Account CRUD with mocked AccountsService."""

    def test_list_accounts_returns_paginated_balances(
        self,
        accounts_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = accounts_client
        account = _sample_account(owner.id)
        mock_service.get_records.return_value = pd.DataFrame([account.model_dump(mode="python")])
        mock_service.balances_service.get_balances.return_value = pd.DataFrame(
            [{"account_id": account.id, "balance": 5000.0, "currency": "USD", "owner_id": owner.id}]
        )

        response = client.get("/api/v1/accounts")

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert payload["items"][0]["balance"] == 5000.0
        assert payload["items"][0]["account_kind"] == "checking"

    def test_get_account_not_found_returns_404(
        self,
        accounts_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, _owner, mock_service = accounts_client
        mock_service.get_with_extension.return_value = (None, None)

        response = client.get(f"/api/v1/accounts/{uuid.uuid4()}")

        assert response.status_code == 404

    def test_create_account_returns_201(
        self,
        accounts_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = accounts_client
        created = _sample_account(owner.id)
        mock_service.create_account.return_value = created
        mock_service.get_with_extension.return_value = (created, None)
        mock_service.get_balance.return_value = None

        response = client.post(
            "/api/v1/accounts",
            json={
                "name": "Main Checking",
                "account_kind": "checking",
                "ledger_side": "asset",
                "currency": "USD",
                "banking_details": {"entity": "Example Bank"},
            },
        )

        assert response.status_code == 201
        assert response.json()["name"] == "Main Checking"
        mock_service.create_account.assert_called_once()

    def test_create_account_uses_initial_value_when_mv_empty(
        self,
        accounts_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        """G8: balance falls back to ``initial_value`` when MV has no row."""
        client, owner, mock_service = accounts_client
        created = _sample_account(owner.id)
        created.initial_value = 1000.0
        mock_service.create_account.return_value = created
        mock_service.get_with_extension.return_value = (created, None)
        mock_service.get_balance.return_value = None

        response = client.post(
            "/api/v1/accounts",
            json={
                "name": "Savings",
                "account_kind": "savings",
                "ledger_side": "asset",
                "currency": "USD",
                "initial_value": 1000.0,
                "banking_details": {"entity": "Example Bank"},
            },
        )

        assert response.status_code == 201
        assert response.json()["balance"] == 1000.0

    def test_put_account_returns_200(
        self,
        accounts_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = accounts_client
        existing = _sample_account(owner.id)
        updated = existing.model_copy(update={"name": "Updated Name"})
        mock_service.get_with_extension.side_effect = [(existing, None), (updated, None)]
        mock_service.update_account.return_value = updated
        mock_service.get_balance.return_value = None

        response = client.put(
            f"/api/v1/accounts/{existing.id}",
            json={"name": "Updated Name"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
        mock_service.update_account.assert_called_once()

    def test_list_accounts_filter_by_account_kind(
        self,
        accounts_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = accounts_client
        cash = _sample_account(owner.id)
        cash.account_kind = AccountKind.CASH
        cash.name = "Cash Jar"
        mock_service.get_records.return_value = pd.DataFrame([cash.model_dump(mode="python")])
        mock_service.balances_service.get_balances.return_value = pd.DataFrame([])

        response = client.get("/api/v1/accounts?account_kind=cash")

        assert response.status_code == 200
        assert response.json()["items"][0]["account_kind"] == "cash"
        filter_arg = mock_service.get_records.call_args[0][0]
        assert filter_arg is not None
        assert filter_arg.account_kind == AccountKind.CASH

    def test_list_accounts_filter_by_ledger_side(
        self,
        accounts_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = accounts_client
        liability = _sample_account(owner.id)
        liability.ledger_side = LedgerSide.LIABILITY
        liability.name = "Credit Card"
        mock_service.get_records.return_value = pd.DataFrame([liability.model_dump(mode="python")])
        mock_service.balances_service.get_balances.return_value = pd.DataFrame([])

        response = client.get("/api/v1/accounts?ledger_side=liability")

        assert response.status_code == 200
        filter_arg = mock_service.get_records.call_args[0][0]
        assert filter_arg is not None
        assert filter_arg.ledger_side == LedgerSide.LIABILITY

    def test_list_accounts_filter_by_is_active(
        self,
        accounts_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = accounts_client
        inactive = _sample_account(owner.id)
        inactive.active = False
        mock_service.get_records.return_value = pd.DataFrame([inactive.model_dump(mode="python")])
        mock_service.balances_service.get_balances.return_value = pd.DataFrame([])

        response = client.get("/api/v1/accounts?is_active=false")

        assert response.status_code == 200
        filter_arg = mock_service.get_records.call_args[0][0]
        assert filter_arg is not None
        assert filter_arg.active is False

    def test_get_account_balance(
        self,
        accounts_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = accounts_client
        account = _sample_account(owner.id)
        mock_service.get.return_value = account
        mock_service.get_balance.return_value = AccountBalancesDTO(
            owner_id=owner.id,
            account_id=account.id,
            currency="USD",
            balance=2500.0,
            last_activity_ts=datetime.now(timezone.utc),
        )

        response = client.get(f"/api/v1/accounts/{account.id}/balance")

        assert response.status_code == 200
        assert response.json()["balance"] == 2500.0

    def test_delete_account_returns_204(
        self,
        accounts_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = accounts_client
        account = _sample_account(owner.id)
        mock_service.get.return_value = account

        response = client.delete(f"/api/v1/accounts/{account.id}")

        assert response.status_code == 204
        mock_service.delete.assert_called_once()


class TestAccountsTenancy:
    """Cross-tenant access returns 404."""

    def test_get_other_tenant_account_returns_404(self) -> None:
        get_settings.cache_clear()
        app = create_app()
        owner = make_user()
        other_account_id = uuid.uuid4()
        mock_accounts = MagicMock()
        mock_accounts.get_with_extension.return_value = (None, None)

        app.dependency_overrides[get_current_owner] = lambda: owner
        app.dependency_overrides[get_accounts_service] = lambda: mock_accounts
        client = TestClient(app)

        response = client.get(f"/api/v1/accounts/{other_account_id}")

        assert response.status_code == 404
        app.dependency_overrides.clear()

    def test_accounts_routes_registered_in_openapi(self, client: TestClient) -> None:
        schema = client.get("/api/openapi.json").json()
        assert "/api/v1/accounts" in schema["paths"]
        assert "/api/v1/accounts/{account_id}/balance" in schema["paths"]
