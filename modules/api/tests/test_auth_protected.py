"""Tests for protected auth routes."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from auth_helpers import VALID_PASSWORD, make_user
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
