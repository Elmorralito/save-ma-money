"""Tests for movement (TRANSFER alias) endpoints (PPT-037)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
from fastapi.testclient import TestClient

from auth_helpers import make_user
from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.services import get_accounts_service, get_transactions_service
from papita_txnsapi.main import create_app
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.model.enums import AccountKind, LedgerSide, TransactionKind, TransactionStatus


def _sample_account(owner_id: uuid.UUID) -> AccountsDTO:
    return AccountsDTO(
        id=uuid.uuid4(),
        name="Checking",
        owner_id=owner_id,
        account_kind=AccountKind.CHECKING,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
    )


def _sample_transfer(owner_id: uuid.UUID) -> TransactionsDTO:
    now = datetime.now(timezone.utc)
    return TransactionsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        transaction_kind=TransactionKind.TRANSFER,
        amount=500.0,
        currency="USD",
        transaction_ts=now,
        from_account_id=uuid.uuid4(),
        to_account_id=uuid.uuid4(),
        status=TransactionStatus.PENDING,
        description="Scheduled transfer",
        created_at=now,
        updated_at=now,
    )


class TestMovementsAuth:
    """Protected route contract."""

    def test_list_movements_without_token_returns_401(self, client: TestClient) -> None:
        response = client.get("/api/v1/movements")
        assert response.status_code == 401


class TestMovementsRoutes:
    """Movement alias CRUD with mocked services."""

    def test_list_movements_returns_transfers(
        self,
        movements_client: tuple[TestClient, object, MagicMock, MagicMock],
    ) -> None:
        client, owner, mock_transactions, _mock_accounts = movements_client
        transfer = _sample_transfer(owner.id)
        mock_transactions.list_transfers.return_value = (
            pd.DataFrame([transfer.model_dump(mode="python")]),
            1,
        )

        response = client.get("/api/v1/movements")

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert payload["items"][0]["status"] == "pending"
        mock_transactions.list_transfers.assert_called_once()

    def test_create_movement_immediate_execute(
        self,
        movements_client: tuple[TestClient, object, MagicMock, MagicMock],
    ) -> None:
        client, owner, mock_transactions, mock_accounts = movements_client
        source = _sample_account(owner.id)
        destination = _sample_account(owner.id)
        destination.id = uuid.uuid4()
        transfer = _sample_transfer(owner.id)
        transfer.status = TransactionStatus.COMPLETED
        transfer.from_account_id = source.id
        transfer.to_account_id = destination.id

        mock_accounts.get.side_effect = lambda obj, owner=None, **kwargs: (
            source if obj == source.id else destination
        )
        mock_transactions.create_transfer.return_value = transfer.model_copy(update={"status": TransactionStatus.PENDING})
        mock_transactions.complete_transfer.return_value = transfer

        response = client.post(
            "/api/v1/movements",
            json={
                "source_account_id": str(source.id),
                "destination_account_id": str(destination.id),
                "amount": 500.0,
                "currency": "USD",
                "movement_date": "2026-02-04",
                "scheduled": False,
            },
        )

        assert response.status_code == 201
        assert response.json()["status"] == "completed"
        mock_transactions.create_transfer.assert_called_once()
        mock_transactions.complete_transfer.assert_called_once()

    def test_create_movement_currency_mismatch_returns_422(
        self,
        movements_client: tuple[TestClient, object, MagicMock, MagicMock],
    ) -> None:
        client, owner, _mock_transactions, mock_accounts = movements_client
        source = _sample_account(owner.id)
        destination = _sample_account(owner.id)
        destination.id = uuid.uuid4()
        destination.currency = "EUR"

        mock_accounts.get.side_effect = lambda obj, owner=None, **kwargs: (
            source if obj == source.id else destination
        )

        response = client.post(
            "/api/v1/movements",
            json={
                "source_account_id": str(source.id),
                "destination_account_id": str(destination.id),
                "amount": 500.0,
                "currency": "USD",
                "movement_date": "2026-02-04",
            },
        )

        assert response.status_code == 422

    def test_execute_movement_returns_completed(
        self,
        movements_client: tuple[TestClient, object, MagicMock, MagicMock],
    ) -> None:
        client, owner, mock_transactions, _mock_accounts = movements_client
        transfer = _sample_transfer(owner.id)
        completed = transfer.model_copy(update={"status": TransactionStatus.COMPLETED})
        mock_transactions.get.return_value = transfer
        mock_transactions.complete_transfer.return_value = completed

        response = client.post(f"/api/v1/movements/{transfer.id}/execute")

        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    def test_delete_movement_cancels_pending(
        self,
        movements_client: tuple[TestClient, object, MagicMock, MagicMock],
    ) -> None:
        client, owner, mock_transactions, _mock_accounts = movements_client
        transfer = _sample_transfer(owner.id)
        mock_transactions.get.return_value = transfer

        response = client.delete(f"/api/v1/movements/{transfer.id}")

        assert response.status_code == 204
        mock_transactions.cancel.assert_called_once()


class TestMovementsTenancy:
    """Cross-tenant access returns 404."""

    def test_get_other_tenant_movement_returns_404(self) -> None:
        get_settings.cache_clear()
        app = create_app()
        owner = make_user()
        mock_transactions = MagicMock()
        mock_transactions.get.return_value = None

        app.dependency_overrides[get_current_owner] = lambda: owner
        app.dependency_overrides[get_transactions_service] = lambda: mock_transactions
        app.dependency_overrides[get_accounts_service] = lambda: MagicMock()
        client = TestClient(app)

        response = client.get(f"/api/v1/movements/{uuid.uuid4()}")

        assert response.status_code == 404
        app.dependency_overrides.clear()

    def test_movements_routes_registered_in_openapi(self, client: TestClient) -> None:
        schema = client.get("/api/openapi.json").json()
        assert "/api/v1/movements" in schema["paths"]
        assert "/api/v1/movements/{movement_id}/execute" in schema["paths"]
