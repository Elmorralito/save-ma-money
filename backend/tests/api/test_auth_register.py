"""Tests for POST /auth/register."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from auth_helpers import VALID_PASSWORD, make_user

from papita_txnsmodel.model.enums import ProviderType


class TestAuthRegister:
    """Register endpoint contract tests."""

    def test_register_returns_201_without_password(self, users_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_service = users_client
        user = make_user(email="johndoe@example.local")
        user.display_name = "John Doe"
        user.phone = "+15551234567"
        user.provider_type = "email"
        mock_service.register.return_value = user

        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "johndoe@example.local",
                "password": VALID_PASSWORD,
                "display_name": "John Doe",
                "phone": "+15551234567",
                "provider": "email",
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["email"] == "johndoe@example.local"
        assert payload["display_name"] == "John Doe"
        assert payload["phone"] == "+15551234567"
        assert payload["provider"] == "email"
        assert payload["auth_provider"] == "local"
        assert str(payload["id"]) == str(user.id)
        assert "password" not in payload
        assert "created_at" in payload
        mock_service.register.assert_called_once()
        kwargs = mock_service.register.call_args.kwargs
        assert kwargs["email"] == "johndoe@example.local"
        assert kwargs["username"] == "johndoe"
        assert kwargs["display_name"] == "John Doe"
        assert kwargs["phone"] == "+15551234567"
        assert kwargs["provider_type"] == ProviderType.EMAIL or kwargs["provider_type"] == "email"

    def test_register_duplicate_email_returns_409(self, users_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_service = users_client
        mock_service.register.side_effect = ValueError("Email already registered")

        response = client.post(
            "/api/v1/auth/register",
            json={"email": "john@example.local", "password": VALID_PASSWORD},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "Email already registered"

    def test_register_invalid_password_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "john@example.local", "password": "short"},
        )

        assert response.status_code == 422

    def test_register_rejects_oauth_provider_for_password(self, client: TestClient) -> None:
        for provider in ("google", "github"):
            response = client.post(
                "/api/v1/auth/register",
                json={"email": "john@example.local", "password": VALID_PASSWORD, "provider": provider},
            )
            assert response.status_code == 422, provider
