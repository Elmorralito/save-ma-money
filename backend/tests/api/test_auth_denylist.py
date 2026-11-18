"""Tests for Redis JWT denylist wiring on auth + logout (PPT-043 P2)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from auth_helpers import make_user
from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.core.rate_limit import InMemoryRateLimiter
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.dependencies.services import get_users_service
from papita_txnsapi.main import create_app


class TestLogoutDenylist:
    """Local logout + protected route rejection when Redis denylist is active."""

    def test_local_logout_denylists_token(
        self,
        fake_redis: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()
        InMemoryRateLimiter().reset()

        owner = make_user()
        assert owner.id is not None
        mock_users = MagicMock()
        mock_users.get_owner.return_value = owner

        with patch("papita_txnsapi.main.init_redis", return_value=fake_redis):
            app = create_app()
            app.state.redis = fake_redis
            app.dependency_overrides[get_users_service] = lambda: mock_users
            settings = get_settings()
            token = AuthSecurityManager(settings).generate_token(str(owner.id))

            with TestClient(app) as client:
                me_ok = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
                logout = client.post(
                    "/api/v1/auth/logout",
                    json={"refresh_token": "unused-local", "access_token": token},
                )
                me_denied = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

        get_settings.cache_clear()
        monkeypatch.setenv("REDIS_ENABLED", "false")

        assert me_ok.status_code == 200
        assert logout.status_code == 204
        assert me_denied.status_code == 401

    def test_denylist_fail_closed_returns_503(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When Redis is required but the client is missing, protected routes 503."""
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()
        InMemoryRateLimiter().reset()

        owner = make_user()
        mock_users = MagicMock()
        mock_users.get_owner.return_value = owner

        with patch("papita_txnsapi.main.init_redis", return_value=None):
            app = create_app()
            app.state.redis = None
            app.dependency_overrides[get_users_service] = lambda: mock_users
            settings = get_settings()
            token = AuthSecurityManager(settings).generate_token(str(owner.id))

            with TestClient(app) as client:
                response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

        get_settings.cache_clear()
        monkeypatch.setenv("REDIS_ENABLED", "false")

        assert response.status_code == 503
        assert "revocation" in response.json()["detail"].lower()
