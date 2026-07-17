"""Tests for transaction Redis cache and Idempotency-Key (PPT-043)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from auth_helpers import make_user
from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.core.idempotency import begin_idempotency, complete_idempotency
from papita_txnsapi.core.rate_limit import InMemoryRateLimiter
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


def _create_body(expense: TransactionsDTO) -> dict:
    return {
        "transaction_type": "expense",
        "amount": expense.amount,
        "currency": expense.currency,
        "transaction_date": expense.transaction_ts.date().isoformat(),
        "account_id": str(expense.from_account_id),
        "category_id": str(expense.category_id),
        "description": expense.description,
    }


class TestTransactionListCache:
    """Short-TTL cache-aside on GET /transactions."""

    def test_list_cache_hit_and_create_invalidates(
        self,
        fake_redis: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        get_settings.cache_clear()
        InMemoryRateLimiter().reset()

        owner = make_user()
        expense = _sample_expense(owner.id)
        mock_service = MagicMock()
        mock_service.list_transactions.return_value = (
            pd.DataFrame([expense.model_dump(mode="python")]),
            1,
        )
        mock_service.create.return_value = expense

        with patch("papita_txnsapi.main.init_redis", return_value=fake_redis):
            app = create_app()
            app.state.redis = fake_redis
            app.dependency_overrides[get_current_owner] = lambda: owner
            app.dependency_overrides[get_transactions_service] = lambda: mock_service
            with TestClient(app) as client:
                first = client.get("/api/v1/transactions")
                second = client.get("/api/v1/transactions")
                created = client.post("/api/v1/transactions", json=_create_body(expense))
                third = client.get("/api/v1/transactions")

        get_settings.cache_clear()
        monkeypatch.setenv("REDIS_ENABLED", "false")

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.headers.get("X-Cache") == "HIT"
        assert created.status_code == 201
        assert third.status_code == 200
        assert third.headers.get("X-Cache") == "MISS"
        assert mock_service.list_transactions.call_count == 2


class TestTransactionIdempotency:
    """Idempotency-Key replay for POST /transactions."""

    def test_create_replay_skips_second_service_call(
        self,
        fake_redis: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        get_settings.cache_clear()
        InMemoryRateLimiter().reset()

        owner = make_user()
        expense = _sample_expense(owner.id)
        mock_service = MagicMock()
        mock_service.create.return_value = expense

        with patch("papita_txnsapi.main.init_redis", return_value=fake_redis):
            app = create_app()
            app.state.redis = fake_redis
            app.dependency_overrides[get_current_owner] = lambda: owner
            app.dependency_overrides[get_transactions_service] = lambda: mock_service
            headers = {"Idempotency-Key": "txn-create-1"}
            with TestClient(app) as client:
                first = client.post("/api/v1/transactions", json=_create_body(expense), headers=headers)
                second = client.post("/api/v1/transactions", json=_create_body(expense), headers=headers)

        get_settings.cache_clear()
        monkeypatch.setenv("REDIS_ENABLED", "false")

        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["id"] == second.json()["id"]
        assert mock_service.create.call_count == 1

    def test_begin_conflict_when_pending(self, fake_redis: object) -> None:
        owner_id = uuid.uuid4()
        first = begin_idempotency(
            fake_redis, owner_id, scope="transactions:create", key="k1", ttl_seconds=60
        )
        second = begin_idempotency(
            fake_redis, owner_id, scope="transactions:create", key="k1", ttl_seconds=60
        )
        assert first.state == "miss"
        assert second.state == "conflict"

    def test_begin_hit_after_complete(self, fake_redis: object) -> None:
        owner_id = uuid.uuid4()
        begun = begin_idempotency(
            fake_redis, owner_id, scope="transactions:create", key="k2", ttl_seconds=60
        )
        assert begun.state == "miss"
        complete_idempotency(
            fake_redis,
            owner_id,
            scope="transactions:create",
            key="k2",
            body={"id": str(uuid.uuid4()), "amount": 1.0},
            ttl_seconds=60,
        )
        replay = begin_idempotency(
            fake_redis, owner_id, scope="transactions:create", key="k2", ttl_seconds=60
        )
        assert replay.state == "hit"
        assert replay.payload is not None
        assert replay.payload["amount"] == 1.0
