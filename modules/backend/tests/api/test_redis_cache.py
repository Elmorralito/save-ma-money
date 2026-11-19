"""Tests for versioned Redis cache and write-path invalidation (PPT-043)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from auth_helpers import make_user
from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.core.cache import (
    CacheNamespace,
    bump_cache_versions,
    get_cache_version,
    get_versioned_cached_json,
    set_versioned_cached_json,
)
from papita_txnsapi.core.rate_limit import InMemoryRateLimiter
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.services import get_accounts_service, get_categories_service
from papita_txnsapi.main import create_app
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.model.enums import AccountKind, CategoryKind, LedgerSide


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


def _sample_category(owner_id: uuid.UUID) -> CategoriesDTO:
    now = datetime.now(timezone.utc)
    return CategoriesDTO(
        id=uuid.uuid4(),
        name="Groceries",
        description="Food",
        tags=["food"],
        owner_id=owner_id,
        category_kind=CategoryKind.EXPENSE,
        created_at=now,
        updated_at=now,
    )


class TestVersionedCacheHelpers:
    """Namespace version counters invalidate prior hashed keys."""

    def test_bump_invalidates_prior_entry(self, fake_redis: object) -> None:
        owner_id = uuid.uuid4()
        params = {"skip": 0, "limit": 20}
        assert get_cache_version(fake_redis, owner_id, CacheNamespace.ACCOUNTS) == 0
        set_versioned_cached_json(
            fake_redis,
            owner_id,
            CacheNamespace.ACCOUNTS,
            "accounts:list",
            params,
            value={"total": 1, "items": [], "skip": 0, "limit": 20},
            ttl_seconds=60,
        )
        hit, status, _version = get_versioned_cached_json(
            fake_redis, owner_id, CacheNamespace.ACCOUNTS, "accounts:list", params
        )
        assert status == "HIT"
        assert hit is not None

        bump_cache_versions(fake_redis, owner_id, CacheNamespace.ACCOUNTS)
        miss, status_after, _ = get_versioned_cached_json(
            fake_redis, owner_id, CacheNamespace.ACCOUNTS, "accounts:list", params
        )
        assert status_after == "MISS"
        assert miss is None
        assert get_cache_version(fake_redis, owner_id, CacheNamespace.ACCOUNTS) == 1


class TestAccountsCacheInvalidation:
    """Account mutations bump cache so the next list is a miss then rebuild."""

    def test_create_account_busts_list_cache(
        self,
        fake_redis: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        get_settings.cache_clear()
        InMemoryRateLimiter().reset()

        owner = make_user()
        account = _sample_account(owner.id)
        mock_service = MagicMock()
        mock_service.list_accounts.return_value = (pd.DataFrame([account.model_dump(mode="python")]), 1)
        mock_service.balances_service.get_balances.return_value = pd.DataFrame(
            [{"account_id": account.id, "balance": 100.0, "currency": "USD", "owner_id": owner.id}]
        )
        mock_service.create_account.return_value = (account, None)
        mock_service.get_balance.return_value = None

        with patch("papita_txnsapi.main.init_redis", return_value=fake_redis):
            app = create_app()
            app.state.redis = fake_redis
            app.dependency_overrides[get_current_owner] = lambda: owner
            app.dependency_overrides[get_accounts_service] = lambda: mock_service
            with TestClient(app) as client:
                first = client.get("/api/v1/accounts")
                second = client.get("/api/v1/accounts")
                create = client.post(
                    "/api/v1/accounts",
                    json={
                        "name": "Main Checking",
                        "account_kind": "checking",
                        "ledger_side": "asset",
                        "currency": "USD",
                        "banking_details": {"entity": "Example Bank"},
                    },
                )
                third = client.get("/api/v1/accounts")

        get_settings.cache_clear()
        monkeypatch.setenv("REDIS_ENABLED", "false")

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.headers.get("X-Cache") in {"MISS", "BYPASS"}
        assert second.headers.get("X-Cache") == "HIT"
        assert create.status_code == 201
        assert third.status_code == 200
        assert third.headers.get("X-Cache") == "MISS"
        assert mock_service.list_accounts.call_count == 2


class TestCategoriesCache:
    """Categories list uses Redis cache-aside."""

    def test_list_categories_cache_hit(
        self,
        fake_redis: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        get_settings.cache_clear()
        InMemoryRateLimiter().reset()

        owner = make_user()
        category = _sample_category(owner.id)
        mock_service = MagicMock()
        mock_service.list_categories.return_value = (
            pd.DataFrame([category.model_dump(mode="python")]),
            1,
        )
        mock_service.get_categories_for_parents.return_value = pd.DataFrame([])

        with patch("papita_txnsapi.main.init_redis", return_value=fake_redis):
            app = create_app()
            app.state.redis = fake_redis
            app.dependency_overrides[get_current_owner] = lambda: owner
            app.dependency_overrides[get_categories_service] = lambda: mock_service
            with TestClient(app) as client:
                first = client.get("/api/v1/categories")
                second = client.get("/api/v1/categories")

        get_settings.cache_clear()
        monkeypatch.setenv("REDIS_ENABLED", "false")

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.headers.get("X-Cache") == "HIT"
        assert mock_service.list_categories.call_count == 1

    def test_list_categories_with_parent_filter(
        self,
        fake_redis: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        get_settings.cache_clear()
        InMemoryRateLimiter().reset()

        owner = make_user()
        parent_id = uuid.uuid4()
        child = _sample_category(owner.id)
        child.parent_id = parent_id
        mock_service = MagicMock()
        mock_service.list_categories.return_value = (
            pd.DataFrame([child.model_dump(mode="python")]),
            1,
        )

        with patch("papita_txnsapi.main.init_redis", return_value=fake_redis):
            app = create_app()
            app.state.redis = fake_redis
            app.dependency_overrides[get_current_owner] = lambda: owner
            app.dependency_overrides[get_categories_service] = lambda: mock_service
            with TestClient(app) as client:
                response = client.get("/api/v1/categories", params={"parent_id": str(parent_id)})

        get_settings.cache_clear()
        monkeypatch.setenv("REDIS_ENABLED", "false")
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert mock_service.list_categories.call_args.kwargs["parent_id"] == parent_id
        mock_service.get_categories_for_parents.assert_not_called()
