"""Tests for protected auth routes."""

from __future__ import annotations

from unittest.mock import MagicMock

from auth_helpers import VALID_PASSWORD, make_user
from fastapi.testclient import TestClient

from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.core.security import AuthSecurityManager


class TestAuthProtected:
    """Bearer token and /auth/me contract tests."""

    def test_me_without_token_returns_401(self, users_client: tuple[TestClient, MagicMock]) -> None:
        client, _mock_service = users_client

        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"

    def test_me_with_invalid_token_returns_401(self, users_client: tuple[TestClient, MagicMock]) -> None:
        client, _mock_service = users_client

        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-valid-jwt"})

        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"

    def test_me_with_valid_token_returns_profile(self, users_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_service = users_client
        user = make_user()
        mock_service.get_owner.return_value = user
        token = AuthSecurityManager(get_settings()).generate_token(str(user.id))

        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["username"] == user.username
        assert payload["email"] == user.email
        assert str(payload["id"]) == str(user.id)
        assert "password" not in payload

    def test_me_unknown_owner_returns_401(self, users_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_service = users_client
        user = make_user()
        mock_service.get_owner.return_value = None
        token = AuthSecurityManager(get_settings()).generate_token(str(user.id))

        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"

    def test_login_then_me_flow(self, users_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_service = users_client
        user = make_user()
        mock_service.verify_credentials.return_value = user
        mock_service.get_owner.return_value = user

        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "johndoe", "password": VALID_PASSWORD},
        )
        token = login_response.json()["access_token"]

        me_response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "johndoe"

    def test_login_sets_httponly_cookie_and_survives_reload(self, users_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_service = users_client
        user = make_user()
        mock_service.verify_credentials.return_value = user
        mock_service.get_owner.return_value = user

        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "johndoe", "password": VALID_PASSWORD},
        )
        assert login_response.status_code == 200
        set_cookie = login_response.headers.get("set-cookie", "")
        assert "papita_access_token=" in set_cookie
        assert "HttpOnly" in set_cookie

        # Without Authorization header, TestClient sends the HttpOnly cookie.
        me_response = client.get("/api/v1/auth/me")
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "johndoe"

        # Logout clears the cookie even in local (501) mode.
        logout_response = client.post(
            "/api/v1/auth/logout",
            headers={"Origin": "http://testserver"},
            json={"refresh_token": "local-stateless"},
        )
        assert logout_response.status_code == 501
        assert "papita_access_token=" in logout_response.headers.get("set-cookie", "")
        assert "Max-Age=0" in logout_response.headers.get("set-cookie", "")
