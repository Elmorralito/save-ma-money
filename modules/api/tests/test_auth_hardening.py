"""Tests for auth hardening — rate limits, JWT type, inactive users."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi.testclient import TestClient

from auth_helpers import VALID_PASSWORD, make_user
from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.core.rate_limit import get_rate_limiter
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.main import create_app


@pytest.fixture
def rate_limited_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Client with strict auth rate limits enabled."""
    monkeypatch.setenv("AUTH_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("AUTH_LOGIN_RATE_LIMIT_PER_MINUTE", "2")
    monkeypatch.setenv("AUTH_REGISTER_RATE_LIMIT_PER_MINUTE", "2")
    monkeypatch.setenv("AUTH_OAUTH_RATE_LIMIT_PER_MINUTE", "2")
    get_settings.cache_clear()
    get_rate_limiter().reset()
    return TestClient(create_app())


class TestAuthRateLimit:
    """Per-IP sliding window on login and register."""

    def test_login_returns_429_after_limit_exceeded(self, rate_limited_client: TestClient) -> None:
        payload = {"username": "johndoe", "password": VALID_PASSWORD}
        assert rate_limited_client.post("/api/v1/auth/login", data=payload).status_code != 429
        assert rate_limited_client.post("/api/v1/auth/login", data=payload).status_code != 429
        blocked = rate_limited_client.post("/api/v1/auth/login", data=payload)
        assert blocked.status_code == 429
        assert blocked.json()["detail"] == "Too many authentication attempts. Try again later."
        assert blocked.headers.get("X-RateLimit-Limit") == "2"
        assert blocked.headers.get("Retry-After")

    def test_register_returns_429_after_limit_exceeded(self, rate_limited_client: TestClient) -> None:
        for index in range(2):
            response = rate_limited_client.post(
                "/api/v1/auth/register",
                json={
                    "username": f"ratelimit{index}",
                    "email": f"ratelimit{index}@example.local",
                    "password": VALID_PASSWORD,
                },
            )
            assert response.status_code in {201, 409, 422}

        blocked = rate_limited_client.post(
            "/api/v1/auth/register",
            json={
                "username": "ratelimit_blocked",
                "email": "ratelimit_blocked@example.local",
                "password": VALID_PASSWORD,
            },
        )
        assert blocked.status_code == 429

    def test_oauth_returns_429_after_limit_exceeded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from types import SimpleNamespace
        from unittest.mock import patch

        monkeypatch.setenv("AUTH_RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("AUTH_OAUTH_RATE_LIMIT_PER_MINUTE", "2")
        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
        monkeypatch.setenv("DATABASE_URL", "")
        get_settings.cache_clear()
        get_rate_limiter().reset()
        AuthSecurityManager.reset_instances()
        started = SimpleNamespace(
            provider="google",
            url="https://example.supabase.co/auth/v1/authorize?provider=google",
            code_verifier="pkce-verifier-0123456789abcdef",
        )
        with patch("papita_txnsapi.routers.v1.auth.supabase_oauth_authorize_url", return_value=started):
            client = TestClient(create_app())
            assert client.get("/api/v1/auth/oauth/google").status_code == 200
            assert client.get("/api/v1/auth/oauth/google").status_code == 200
            blocked = client.get("/api/v1/auth/oauth/google")
        assert blocked.status_code == 429
        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)


class TestJwtTypeValidation:
    """Access tokens must carry the configured JWT_TOKEN_TYPE claim."""

    def test_me_rejects_token_with_wrong_type_claim(self, users_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_service = users_client
        user = make_user()
        mock_service.get_owner.return_value = user
        settings = get_settings()
        now = datetime.now(timezone.utc)
        wrong_type_token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": now + timedelta(hours=1),
                "iat": now,
                "type": "refresh",
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {wrong_type_token}"})

        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"

    def test_decode_token_accepts_matching_type(self) -> None:
        settings = get_settings()
        manager = AuthSecurityManager(settings)
        token = manager.generate_token("550e8400-e29b-41d4-a716-446655440000")
        payload = manager.decode_token(token, expected_type=settings.JWT_TOKEN_TYPE)
        assert payload is not None
        assert payload["type"] == settings.JWT_TOKEN_TYPE


class TestInactiveUserRejected:
    """Deactivated accounts must not pass protected-route checks."""

    def test_me_rejects_inactive_owner(self, users_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_service = users_client
        user = make_user(active=False)
        mock_service.get_owner.return_value = user
        token = AuthSecurityManager(get_settings()).generate_token(str(user.id))

        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"

    def test_me_rejects_soft_deleted_owner(self, users_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_service = users_client
        user = make_user(deleted_at=datetime.now(timezone.utc))
        mock_service.get_owner.return_value = user
        token = AuthSecurityManager(get_settings()).generate_token(str(user.id))

        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401
