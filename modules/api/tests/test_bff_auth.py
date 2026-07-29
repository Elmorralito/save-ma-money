"""Tests for BFF HttpOnly cookie sessions (PPT-049)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from auth_helpers import make_user
from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.core.bff_session import BFF_CSRF_HEADER, BFF_SESSION_COOKIE, clear_memory_bff_sessions
from papita_txnsapi.core.rate_limit import InMemoryRateLimiter
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.dependencies.services import get_users_service
from papita_txnsapi.main import create_app


@pytest.fixture
def bff_client() -> tuple[TestClient, MagicMock]:
    """Test client with mocked UsersService for local BFF auth."""
    get_settings.cache_clear()
    AuthSecurityManager.reset_instances()
    InMemoryRateLimiter().reset()
    clear_memory_bff_sessions()

    app = create_app()
    owner = make_user(email="bff@example.com")
    mock_users = MagicMock()
    mock_users.verify_credentials.return_value = owner
    mock_users.get_owner.return_value = owner
    mock_users.register.return_value = owner
    app.dependency_overrides[get_users_service] = lambda: mock_users
    client = TestClient(app)
    yield client, mock_users
    app.dependency_overrides.clear()
    clear_memory_bff_sessions()
    get_settings.cache_clear()


class TestBffCookieSession:
    """Cookie flags, session lifecycle, CSRF, and cookie→protected route path."""

    def test_login_sets_httponly_session_cookie(self, bff_client: tuple[TestClient, MagicMock]) -> None:
        client, _ = bff_client
        response = client.post(
            "/api/v1/bff/auth/login",
            json={"email": "bff@example.com", "password": "password12"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["authenticated"] is True
        assert body["csrf_token"]
        assert "access_token" not in body
        assert "refresh_token" not in body
        assert BFF_SESSION_COOKIE in response.cookies
        # Starlette TestClient exposes cookie jar; Set-Cookie flags via headers.
        set_cookie = response.headers.get("set-cookie", "")
        assert "HttpOnly" in set_cookie or "httponly" in set_cookie.lower()
        assert "Path=/api" in set_cookie or "path=/api" in set_cookie.lower()

    def test_session_probe_unauthenticated(self, bff_client: tuple[TestClient, MagicMock]) -> None:
        client, _ = bff_client
        response = client.get("/api/v1/bff/auth/session")
        assert response.status_code == 200
        assert response.json()["authenticated"] is False

    def test_cookie_authorizes_auth_me(self, bff_client: tuple[TestClient, MagicMock]) -> None:
        client, _ = bff_client
        login = client.post(
            "/api/v1/bff/auth/login",
            json={"email": "bff@example.com", "password": "password12"},
        )
        assert login.status_code == 200
        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == "bff@example.com"

    def test_mutation_without_csrf_is_forbidden(self, bff_client: tuple[TestClient, MagicMock]) -> None:
        client, _ = bff_client
        login = client.post(
            "/api/v1/bff/auth/login",
            json={"email": "bff@example.com", "password": "password12"},
        )
        assert login.status_code == 200
        denied = client.post("/api/v1/bff/auth/logout")
        assert denied.status_code == 403
        assert "CSRF" in denied.json()["detail"]

    def test_logout_with_csrf_clears_session(self, bff_client: tuple[TestClient, MagicMock]) -> None:
        client, _ = bff_client
        login = client.post(
            "/api/v1/bff/auth/login",
            json={"email": "bff@example.com", "password": "password12"},
        )
        csrf = login.json()["csrf_token"]
        logout = client.post("/api/v1/bff/auth/logout", headers={BFF_CSRF_HEADER: csrf})
        assert logout.status_code == 204
        me = client.get("/api/v1/auth/me")
        assert me.status_code == 401
        session = client.get("/api/v1/bff/auth/session")
        assert session.json()["authenticated"] is False

    def test_bearer_still_works_without_cookie(self, bff_client: tuple[TestClient, MagicMock]) -> None:
        """Token-path / auth-smoke coexistence: Bearer bypasses BFF cookie + CSRF."""
        client, mock_users = bff_client
        owner = mock_users.verify_credentials.return_value
        settings = get_settings()
        token = AuthSecurityManager(settings).generate_token(str(owner.id))
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200

    def test_register_then_login(self, bff_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_users = bff_client
        registered = client.post(
            "/api/v1/bff/auth/register",
            json={"email": "bff@example.com", "password": "password12"},
        )
        assert registered.status_code == 201
        mock_users.register.assert_called_once()
        login = client.post(
            "/api/v1/bff/auth/login",
            json={"email": "bff@example.com", "password": "password12"},
        )
        assert login.status_code == 200
        assert login.json()["authenticated"] is True
