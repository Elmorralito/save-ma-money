"""Tests for POST /auth/register."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from auth_helpers import VALID_PASSWORD, make_user


class TestAuthRegister:
    """Register endpoint contract tests."""

    def test_register_returns_201_without_password(self, users_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_service = users_client
        user = make_user()
        mock_service.register.return_value = user

        response = client.post(
            "/api/v1/auth/register",
            json={"username": "johndoe", "email": "john@example.local", "password": VALID_PASSWORD},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["username"] == "johndoe"
        assert payload["email"] == "john@example.local"
        assert str(payload["id"]) == str(user.id)
        assert "password" not in payload
        assert "created_at" in payload

    def test_register_duplicate_username_returns_409(self, users_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_service = users_client
        mock_service.register.side_effect = ValueError("Username already registered")

        response = client.post(
            "/api/v1/auth/register",
            json={"username": "johndoe", "email": "other@example.local", "password": VALID_PASSWORD},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "Username already registered"

    def test_register_duplicate_email_returns_409(self, users_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_service = users_client
        mock_service.register.side_effect = ValueError("Email already registered")

        response = client.post(
            "/api/v1/auth/register",
            json={"username": "otheruser", "email": "john@example.local", "password": VALID_PASSWORD},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "Email already registered"

    def test_register_invalid_password_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/register",
            json={"username": "johndoe", "email": "john@example.local", "password": "short"},
        )

        assert response.status_code == 422
