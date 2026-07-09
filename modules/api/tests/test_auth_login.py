"""Tests for POST /auth/login."""

from __future__ import annotations

from unittest.mock import MagicMock

import jwt
from fastapi.testclient import TestClient

from auth_helpers import VALID_PASSWORD, make_user
from papita_txnsapi.config.settings import get_settings


class TestAuthLogin:
    """Login endpoint contract tests."""

    def test_login_with_username_returns_token(self, users_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_service = users_client
        user = make_user()
        mock_service.verify_credentials.return_value = user

        response = client.post(
            "/api/v1/auth/login",
            data={"username": "johndoe", "password": VALID_PASSWORD},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["token_type"] == "bearer"
        assert payload["expires_in"] == get_settings().JWT_EXPIRATION_TIME_SECONDS
        assert payload["access_token"]

        decoded = jwt.decode(
            payload["access_token"],
            get_settings().JWT_SECRET_KEY,
            algorithms=[get_settings().JWT_ALGORITHM],
        )
        assert decoded["sub"] == str(user.id)

    def test_login_with_email_returns_token(self, users_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_service = users_client
        user = make_user()
        mock_service.verify_credentials.return_value = user

        response = client.post(
            "/api/v1/auth/login",
            data={"username": "john@example.local", "password": VALID_PASSWORD},
        )

        assert response.status_code == 200
        assert response.json()["access_token"]

    def test_login_bad_password_returns_401(self, users_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_service = users_client
        mock_service.verify_credentials.return_value = None

        response = client.post(
            "/api/v1/auth/login",
            data={"username": "johndoe", "password": "WrongPass1!"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect username or password"
        assert response.headers.get("www-authenticate") == "Bearer"

    def test_login_unknown_user_returns_401(self, users_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_service = users_client
        mock_service.verify_credentials.return_value = None

        response = client.post(
            "/api/v1/auth/login",
            data={"username": "unknown@example.local", "password": VALID_PASSWORD},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect username or password"
