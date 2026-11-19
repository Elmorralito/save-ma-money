"""Tests for transaction endpoints (PPT-037)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
from auth_helpers import make_user
from fastapi.testclient import TestClient

from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.services import get_transactions_service
from papita_txnsapi.main import create_app
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.model.enums import AccountKind, LedgerSide, SettlementStatus, TransactionKind, TransactionStatus


def _sample_account(owner_id: uuid.UUID) -> AccountsDTO:
    return AccountsDTO(
        id=uuid.uuid4(),
        name="Checking",
        owner_id=owner_id,
        account_kind=AccountKind.CHECKING,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
    )


def _sample_expense(owner_id: uuid.UUID) -> TransactionsDTO:
    now = datetime.now(timezone.utc)
    return TransactionsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        transaction_kind=TransactionKind.EXPENSE,
        amount=45.5,
        currency="USD",
        transaction_ts=now,
        from_account_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        status=TransactionStatus.COMPLETED,
        description="Lunch",
        created_at=now,
        updated_at=now,
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
        status=TransactionStatus.COMPLETED,
        description="Savings transfer",
        created_at=now,
        updated_at=now,
    )


class TestTransactionsAuth:
    """Protected route contract."""

    def test_list_transactions_without_token_returns_401(self, client: TestClient) -> None:
        response = client.get("/api/v1/transactions")
        assert response.status_code == 401


class TestTransactionsRoutes:
    """Transaction CRUD with mocked TransactionsService."""

    def test_list_transactions_excludes_transfers_by_default(
        self,
        transactions_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = transactions_client
        expense = _sample_expense(owner.id)
        mock_service.list_transactions.return_value = (
            pd.DataFrame([expense.model_dump(mode="python")]),
            1,
        )

        response = client.get("/api/v1/transactions")

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert payload["items"][0]["transaction_type"] == "expense"

    def test_list_transactions_includes_transfers_when_filtered(
        self,
        transactions_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = transactions_client
        transfer = _sample_transfer(owner.id)
        mock_service.list_transactions.return_value = (
            pd.DataFrame([transfer.model_dump(mode="python")]),
            1,
        )

        response = client.get("/api/v1/transactions?transaction_type=transfer")

        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["transaction_type"] == "transfer"

    def test_create_transaction_returns_201(
        self,
        transactions_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = transactions_client
        created = _sample_expense(owner.id)
        mock_service.create.return_value = created

        response = client.post(
            "/api/v1/transactions",
            json={
                "account_id": str(uuid.uuid4()),
                "category_id": str(uuid.uuid4()),
                "transaction_type": "expense",
                "amount": 45.5,
                "currency": "USD",
                "description": "Lunch",
                "transaction_date": "2026-02-04",
            },
        )

        assert response.status_code == 201
        assert response.json()["transaction_type"] == "expense"
        mock_service.create.assert_called_once()

    def test_create_transfer_on_transactions_returns_422(
        self,
        transactions_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, _owner, _mock_service = transactions_client

        response = client.post(
            "/api/v1/transactions",
            json={
                "account_id": str(uuid.uuid4()),
                "category_id": str(uuid.uuid4()),
                "transaction_type": "transfer",
                "amount": 45.5,
                "currency": "USD",
                "transaction_date": "2026-02-04",
            },
        )

        assert response.status_code == 422

    def test_get_transaction_not_found_returns_404(
        self,
        transactions_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, _owner, mock_service = transactions_client
        mock_service.get.return_value = None

        response = client.get(f"/api/v1/transactions/{uuid.uuid4()}")

        assert response.status_code == 404

    def test_delete_transaction_returns_204(
        self,
        transactions_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = transactions_client
        existing = _sample_expense(owner.id)
        mock_service.get.return_value = existing

        response = client.delete(f"/api/v1/transactions/{existing.id}")

        assert response.status_code == 204
        mock_service.delete.assert_called_once()

    def test_create_transfer_immediate_execute(
        self,
        movements_client: tuple[TestClient, object, MagicMock, MagicMock],
    ) -> None:
        client, owner, mock_transactions, mock_accounts = movements_client
        source = _sample_account(owner.id)
        destination = _sample_account(owner.id)
        destination.id = uuid.uuid4()
        transfer = _sample_transfer(owner.id)
        transfer.status = TransactionStatus.COMPLETED
        transfer.settlement_status = SettlementStatus.SETTLED
        transfer.from_account_id = source.id
        transfer.to_account_id = destination.id

        mock_accounts.get.side_effect = lambda obj, owner=None, **kwargs: source if obj == source.id else destination
        mock_transactions.create_transfer.return_value = transfer.model_copy(
            update={"status": TransactionStatus.PENDING, "settlement_status": SettlementStatus.IN_TRANSIT}
        )
        mock_transactions.complete_transfer.return_value = transfer

        response = client.post(
            "/api/v1/transactions",
            json={
                "transaction_type": "transfer",
                "from_account_id": str(source.id),
                "to_account_id": str(destination.id),
                "amount": 500.0,
                "currency": "USD",
                "transaction_date": "2026-02-04",
                "scheduled": False,
                "settlement_status": "settled",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["transaction_type"] == "transfer"
        assert body["status"] == "completed"
        assert body["settlement_status"] == "settled"
        mock_transactions.create_transfer.assert_called_once()
        mock_transactions.complete_transfer.assert_called_once()
        mock_transactions.refresh_balance_views.assert_called_once()

    def test_create_scheduled_in_transit_transfer_and_execute(
        self,
        movements_client: tuple[TestClient, object, MagicMock, MagicMock],
    ) -> None:
        client, owner, mock_transactions, mock_accounts = movements_client
        source = _sample_account(owner.id)
        destination = _sample_account(owner.id)
        destination.id = uuid.uuid4()
        transfer = _sample_transfer(owner.id)
        transfer.status = TransactionStatus.PENDING
        transfer.settlement_status = SettlementStatus.IN_TRANSIT
        transfer.from_account_id = source.id
        transfer.to_account_id = destination.id

        mock_accounts.get.side_effect = lambda obj, owner=None, **kwargs: source if obj == source.id else destination
        mock_transactions.create_transfer.return_value = transfer

        response = client.post(
            "/api/v1/transactions",
            json={
                "transaction_type": "transfer",
                "source_account_id": str(source.id),
                "destination_account_id": str(destination.id),
                "amount": 500.0,
                "currency": "USD",
                "movement_date": "2026-02-04",
                "scheduled": True,
                "settlement_status": "in_transit",
            },
        )
        assert response.status_code == 201
        assert response.json()["status"] == "pending"
        assert response.json()["settlement_status"] == "in_transit"
        mock_transactions.complete_transfer.assert_not_called()

        completed = transfer.model_copy(
            update={"status": TransactionStatus.COMPLETED, "settlement_status": SettlementStatus.SETTLED}
        )
        mock_transactions.get.return_value = transfer
        mock_transactions.complete_transfer.return_value = completed

        exec_resp = client.post(f"/api/v1/transactions/{transfer.id}/execute")
        assert exec_resp.status_code == 200
        assert exec_resp.json()["status"] == "completed"
        assert exec_resp.json()["settlement_status"] == "settled"


class TestTransactionsTenancy:
    """Cross-tenant access returns 404."""

    def test_get_other_tenant_transaction_returns_404(self) -> None:
        get_settings.cache_clear()
        app = create_app()
        owner = make_user()
        mock_service = MagicMock()
        mock_service.get.return_value = None

        app.dependency_overrides[get_current_owner] = lambda: owner
        app.dependency_overrides[get_transactions_service] = lambda: mock_service
        client = TestClient(app)

        response = client.get(f"/api/v1/transactions/{uuid.uuid4()}")

        assert response.status_code == 404
        app.dependency_overrides.clear()

    def test_transactions_routes_registered_in_openapi(self, client: TestClient) -> None:
        schema = client.get("/api/openapi.json").json()
        assert "/api/v1/transactions" in schema["paths"]
        assert "/api/v1/transactions/bulk" in schema["paths"]
        assert "/api/v1/transactions/{transaction_id}/execute" in schema["paths"]
        assert "/api/v1/movements" not in schema["paths"]
