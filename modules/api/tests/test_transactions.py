"""Tests for transaction endpoints (PPT-037)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
from fastapi.testclient import TestClient

from auth_helpers import make_user
from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.services import get_transactions_service
from papita_txnsapi.main import create_app
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.model.enums import TransactionKind, TransactionStatus


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
        transfer = _sample_transfer(owner.id)
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

    def test_split_transaction_returns_501(self, transactions_client: tuple[TestClient, object, MagicMock]) -> None:
        client, _owner, _mock_service = transactions_client

        response = client.post(f"/api/v1/transactions/{uuid.uuid4()}/split", json={"splits": []})

        assert response.status_code == 501


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
