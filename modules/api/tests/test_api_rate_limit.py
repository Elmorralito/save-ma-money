"""Tenant API rate-limit tiers (PPT-043 Free / Pro / Enterprise)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from auth_helpers import make_user
from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.core.api_tier import ApiTier, limits_for_tier, resolve_api_tier
from papita_txnsapi.core.rate_limit import InMemoryRateLimiter
from papita_txnsapi.core.redis_keys import redis_key
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.services import get_accounts_service
from papita_txnsapi.main import create_app


def _enable_api_limits(monkeypatch: pytest.MonkeyPatch, *, tier: str = "free", per_minute: int = 2) -> None:
    monkeypatch.setenv("API_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("API_RATE_LIMIT_DEFAULT_TIER", tier)
    monkeypatch.setenv("API_RATE_LIMIT_FREE_PER_MINUTE", str(per_minute))
    monkeypatch.setenv("API_RATE_LIMIT_FREE_PER_DAY", "1000")
    monkeypatch.setenv("API_RATE_LIMIT_PRO_PER_MINUTE", "5")
    monkeypatch.setenv("API_RATE_LIMIT_PRO_PER_DAY", "10000")
    get_settings.cache_clear()
    AuthSecurityManager.reset_instances()
    InMemoryRateLimiter().reset()


def _accounts_client_with_owner(owner=None) -> tuple[TestClient, object, MagicMock]:
    app = create_app()
    owner = owner or make_user()
    mock_service = MagicMock()
    mock_service.list_accounts.return_value = (pd.DataFrame([]), 0)
    mock_service.balances_service = None
    app.dependency_overrides[get_current_owner] = lambda: owner
    app.dependency_overrides[get_accounts_service] = lambda: mock_service
    return TestClient(app), owner, mock_service


class TestProtectedRouteCoverage:
    """Logout/me/budgets participate in rate-limit coverage (PPT-044 L1)."""

    def test_me_counts_toward_tenant_api_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _enable_api_limits(monkeypatch, per_minute=2)
        app = create_app()
        owner = make_user()
        app.dependency_overrides[get_current_owner] = lambda: owner
        client = TestClient(app)
        assert client.get("/api/v1/auth/me").status_code == 200
        assert client.get("/api/v1/auth/me").status_code == 200
        blocked = client.get("/api/v1/auth/me")
        assert blocked.status_code == 429
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        InMemoryRateLimiter().reset()

    def test_budgets_counts_toward_tenant_api_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _enable_api_limits(monkeypatch, per_minute=2)
        app = create_app()
        owner = make_user()
        app.dependency_overrides[get_current_owner] = lambda: owner
        client = TestClient(app)
        assert client.get("/api/v1/budgets").status_code == 501
        assert client.get("/api/v1/budgets").status_code == 501
        blocked = client.get("/api/v1/budgets")
        assert blocked.status_code == 429
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        InMemoryRateLimiter().reset()


class TestApiTierHelpers:
    """Unit tests for tier resolution and limits."""

    def test_limits_for_free_and_pro(self) -> None:
        settings = get_settings()
        free = limits_for_tier(settings, ApiTier.FREE)
        pro = limits_for_tier(settings, ApiTier.PRO)
        enterprise = limits_for_tier(settings, ApiTier.ENTERPRISE)
        assert free.per_minute == settings.API_RATE_LIMIT_FREE_PER_MINUTE
        assert pro.per_minute == settings.API_RATE_LIMIT_PRO_PER_MINUTE
        assert enterprise.unlimited is True

    def test_resolve_default_tier(self) -> None:
        settings = get_settings()
        owner = make_user()
        assert resolve_api_tier(settings, owner.id) == ApiTier(settings.API_RATE_LIMIT_DEFAULT_TIER)

    def test_resolve_redis_override(self, fake_redis: object) -> None:
        settings = get_settings()
        owner = make_user()
        fake_redis.set(redis_key(owner.id, "api_tier"), "pro")
        assert resolve_api_tier(settings, owner.id, fake_redis) is ApiTier.PRO

    def test_resolve_ignores_invalid_redis_tier(self, fake_redis: object) -> None:
        settings = get_settings()
        owner = make_user()
        fake_redis.set(redis_key(owner.id, "api_tier"), "gold")
        assert resolve_api_tier(settings, owner.id, fake_redis) == ApiTier(
            settings.API_RATE_LIMIT_DEFAULT_TIER
        )

    def test_resolve_redis_error_falls_back(self) -> None:
        settings = get_settings()
        owner = make_user()
        client = MagicMock()
        from redis.exceptions import RedisError

        client.get.side_effect = RedisError("boom")
        assert resolve_api_tier(settings, owner.id, client) == ApiTier(settings.API_RATE_LIMIT_DEFAULT_TIER)

    def test_resolve_invalid_default_tier_is_free(self) -> None:
        settings = MagicMock()
        settings.API_RATE_LIMIT_DEFAULT_TIER = "not-a-tier"
        owner = make_user()
        assert resolve_api_tier(settings, owner.id) is ApiTier.FREE


class TestMergeLimitHeaders:
    """Unit coverage for minute/day header selection."""

    def test_merge_limit_header_branches(self) -> None:
        from papita_txnsapi.core.rate_limit import RateLimitResult
        from papita_txnsapi.dependencies.rate_limit import _client_ip, _merge_limit_headers

        unlimited = RateLimitResult(allowed=True, limit=0, remaining=0, reset_at=1)
        minute = RateLimitResult(allowed=True, limit=10, remaining=2, reset_at=10)
        day = RateLimitResult(allowed=True, limit=100, remaining=90, reset_at=20)
        assert _merge_limit_headers(unlimited, unlimited) == {}
        assert _merge_limit_headers(unlimited, day)["X-RateLimit-Limit"] == "100"
        assert _merge_limit_headers(minute, unlimited)["X-RateLimit-Limit"] == "10"
        assert _merge_limit_headers(minute, day)["X-RateLimit-Remaining"] == "2"

        request = MagicMock()
        request.client = None
        assert _client_ip(request) == "unknown"


class TestTenantApiRateLimit:
    """HTTP tests for tenant-scoped API quotas on protected routers."""

    def test_missing_owner_id_returns_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _enable_api_limits(monkeypatch, per_minute=10)
        owner = make_user()
        owner.id = None
        client, _, _ = _accounts_client_with_owner(owner=owner)
        try:
            assert client.get("/api/v1/accounts").status_code == 401
        finally:
            get_settings.cache_clear()
            monkeypatch.setenv("API_RATE_LIMIT_ENABLED", "false")

    def test_allows_under_limit_and_sets_headers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _enable_api_limits(monkeypatch, per_minute=3)
        client, _, _ = _accounts_client_with_owner()
        try:
            response = client.get("/api/v1/accounts")
            assert response.status_code == 200
            assert response.headers.get("X-RateLimit-Limit") == "3"
            assert response.headers.get("X-RateLimit-Tier") == "free"
            assert int(response.headers.get("X-RateLimit-Remaining", "0")) >= 0
        finally:
            get_settings.cache_clear()
            monkeypatch.setenv("API_RATE_LIMIT_ENABLED", "false")

    def test_returns_429_when_minute_quota_exceeded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _enable_api_limits(monkeypatch, per_minute=2)
        client, _, _ = _accounts_client_with_owner()
        try:
            assert client.get("/api/v1/accounts").status_code == 200
            assert client.get("/api/v1/accounts").status_code == 200
            blocked = client.get("/api/v1/accounts")
            assert blocked.status_code == 429
            assert "Retry-After" in blocked.headers
            assert blocked.headers.get("X-RateLimit-Tier") == "free"
            assert "rate limit" in blocked.json()["detail"].lower()
        finally:
            get_settings.cache_clear()
            monkeypatch.setenv("API_RATE_LIMIT_ENABLED", "false")

    def test_enterprise_is_unlimited(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _enable_api_limits(monkeypatch, tier="enterprise", per_minute=1)
        client, _, _ = _accounts_client_with_owner()
        try:
            for _ in range(5):
                assert client.get("/api/v1/accounts").status_code == 200
            assert client.get("/api/v1/accounts").headers.get("X-RateLimit-Tier") == "enterprise"
        finally:
            get_settings.cache_clear()
            monkeypatch.setenv("API_RATE_LIMIT_ENABLED", "false")

    def test_pro_tier_via_redis_override(self, monkeypatch: pytest.MonkeyPatch, fake_redis: object) -> None:
        _enable_api_limits(monkeypatch, tier="free", per_minute=1)
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("API_RATE_LIMIT_PRO_PER_MINUTE", "3")
        get_settings.cache_clear()
        InMemoryRateLimiter().reset()

        owner = make_user()
        assert owner.id is not None
        fake_redis.set(redis_key(owner.id, "api_tier"), "pro")
        mock_service = MagicMock()
        mock_service.list_accounts.return_value = (pd.DataFrame([]), 0)
        mock_service.balances_service = None

        with patch("papita_txnsapi.main.init_redis", return_value=fake_redis):
            app = create_app()
            app.dependency_overrides[get_current_owner] = lambda: owner
            app.dependency_overrides[get_accounts_service] = lambda: mock_service
            with TestClient(app) as client:
                assert client.get("/api/v1/accounts").status_code == 200
                assert client.get("/api/v1/accounts").status_code == 200
                third = client.get("/api/v1/accounts")
                assert third.status_code == 200
                assert third.headers.get("X-RateLimit-Tier") == "pro"
                blocked = client.get("/api/v1/accounts")
                assert blocked.status_code == 429

        get_settings.cache_clear()
        monkeypatch.setenv("API_RATE_LIMIT_ENABLED", "false")
        monkeypatch.setenv("REDIS_ENABLED", "false")

    def test_disabled_skips_enforcement(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("API_RATE_LIMIT_ENABLED", "false")
        monkeypatch.setenv("API_RATE_LIMIT_FREE_PER_MINUTE", "1")
        get_settings.cache_clear()
        InMemoryRateLimiter().reset()
        client, _, _ = _accounts_client_with_owner()
        for _ in range(3):
            assert client.get("/api/v1/accounts").status_code == 200
