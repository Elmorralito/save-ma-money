"""Unit tests for Supabase Auth JWT verification and provision (PPT-039)."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.security import AuthSecurityManager, supabase_issuer
from papita_txnsapi.dependencies.services import get_users_service
from papita_txnsapi.main import create_app
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.users import UsersService


@pytest.fixture
def rsa_keypair():
    """Generate an ephemeral RSA keypair for JWKS-style token signing."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def _mint_supabase_token(
    private_pem: bytes,
    *,
    subject: uuid.UUID,
    email: str,
    supabase_url: str,
    audience: str = "authenticated",
) -> str:
    now = int(time.time())
    payload = {
        "sub": str(subject),
        "email": email,
        "aud": audience,
        "iss": supabase_issuer(supabase_url),
        "role": "authenticated",
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": "test-kid"})


class TestUsersDtoPreservesExplicitId:
    """UsersDTO must not rewrite Supabase subject IDs."""

    def test_explicit_id_survives_model_validate(self) -> None:
        subject = uuid.uuid4()
        user = UsersDTO.model_validate(
            {
                "id": subject,
                "username": "sbuser1",
                "email": "sbuser1@example.local",
                "password": "SecurePass1!",
            }
        )
        assert user.id == subject

    def test_missing_id_uses_username_uuid5(self) -> None:
        user = UsersDTO(username="johndoe", email="john@example.local", password="SecurePass1!")
        other = UsersDTO(username="johndoe", email="other@example.local", password="SecurePass1!")
        assert user.id == other.id


class TestEnsureFromAuthSubject:
    """Provision-on-first-seen for Auth subjects."""

    def test_returns_existing_owner(self) -> None:
        subject = uuid.uuid4()
        existing = UsersDTO.model_construct(
            id=subject,
            username="existing",
            email="existing@example.local",
            password="$argon2$hash",
            active=True,
            deleted_at=None,
            created_at=datetime.now(timezone.utc),
        )
        service = UsersService()
        service.get_owner = MagicMock(return_value=existing)  # type: ignore[method-assign]
        result = service.ensure_from_auth_subject(subject=subject, email="existing@example.local")
        assert result is existing

    def test_creates_when_missing(self) -> None:
        subject = uuid.uuid4()
        service = UsersService()
        service.get_owner = MagicMock(return_value=None)  # type: ignore[method-assign]
        service._lookup_by_identifier = MagicMock(return_value=None)  # type: ignore[method-assign]
        created = UsersDTO.model_construct(
            id=subject,
            username="sb_user",
            email="new@example.local",
            password="$argon2$hash",
            active=True,
            deleted_at=None,
            created_at=datetime.now(timezone.utc),
        )
        service.create = MagicMock(return_value=created)  # type: ignore[method-assign]
        with patch.object(UsersService, "ensure_password_manager"):
            result = service.ensure_from_auth_subject(subject=subject, email="new@example.local", username="sbuser1")
        assert result.id == subject
        service.create.assert_called_once()


class TestSupabaseDecodeToken:
    """JWKS verification path with a mocked signing key."""

    def test_decode_accepts_valid_supabase_jwt(self, rsa_keypair, monkeypatch: pytest.MonkeyPatch) -> None:
        private_pem, public_pem = rsa_keypair
        supabase_url = "https://example.supabase.co"
        subject = uuid.uuid4()
        token = _mint_supabase_token(
            private_pem,
            subject=subject,
            email="owner@example.local",
            supabase_url=supabase_url,
        )

        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", supabase_url)
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
        monkeypatch.setenv("DATABASE_URL", "")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()

        settings = Settings(
            AUTH_PROVIDER="supabase",
            SUPABASE_URL=supabase_url,
            JWT_SECRET_KEY="test-jwt-secret-key-minimum-32-characters",
            DATABASE_URL=None,
        )
        manager = AuthSecurityManager(settings)

        class _Key:
            key = public_pem

        manager._jwks_client = MagicMock()
        manager._jwks_client.get_signing_key_from_jwt.return_value = _Key()

        payload = manager.decode_token(token)
        assert payload is not None
        assert payload["sub"] == str(subject)

        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()

    def test_local_generate_disabled_for_supabase(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()
        settings = Settings(
            AUTH_PROVIDER="supabase",
            SUPABASE_URL="https://example.supabase.co",
            JWT_SECRET_KEY="test-jwt-secret-key-minimum-32-characters",
            DATABASE_URL=None,
        )
        manager = AuthSecurityManager(settings)
        with pytest.raises(RuntimeError, match="Local JWT issuance is disabled"):
            manager.generate_token(str(uuid.uuid4()))
        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()


class TestSupabaseProtectedRoute:
    """Protected /auth/me with supabase provider + provision."""

    def test_me_provisions_owner_from_claims(self, rsa_keypair, monkeypatch: pytest.MonkeyPatch) -> None:
        private_pem, public_pem = rsa_keypair
        supabase_url = "https://example.supabase.co"
        subject = uuid.uuid4()
        token = _mint_supabase_token(
            private_pem,
            subject=subject,
            email="owner@example.local",
            supabase_url=supabase_url,
        )

        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", supabase_url)
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
        monkeypatch.setenv("DATABASE_URL", "")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()

        app = create_app()
        mock_users = MagicMock()
        provisioned = UsersDTO.model_construct(
            id=subject,
            username="owner1",
            email="owner@example.local",
            password="$argon2$hash",
            active=True,
            deleted_at=None,
            created_at=datetime.now(timezone.utc),
        )
        mock_users.ensure_from_auth_subject.return_value = provisioned
        app.dependency_overrides[get_users_service] = lambda: mock_users

        # Patch JWKS after app creation so singleton reads supabase settings.
        AuthSecurityManager.reset_instances()
        settings = get_settings()
        manager = AuthSecurityManager(settings)

        class _Key:
            key = public_pem

        manager._jwks_client = MagicMock()
        manager._jwks_client.get_signing_key_from_jwt.return_value = _Key()

        client = TestClient(app)
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["id"] == str(subject)
        mock_users.ensure_from_auth_subject.assert_called_once()
        app.dependency_overrides.clear()
        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.delenv("SUPABASE_URL", raising=False)


class TestSupabaseAuthRoutes:
    """Register/login delegate to Supabase Auth client helpers."""

    def test_register_uses_supabase_sign_up(self, monkeypatch: pytest.MonkeyPatch) -> None:
        subject = uuid.uuid4()
        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
        monkeypatch.setenv("DATABASE_URL", "")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()

        app = create_app()
        mock_users = MagicMock()
        provisioned = UsersDTO.model_construct(
            id=subject,
            username="johndoe",
            email="john@example.local",
            password="$argon2$hash",
            active=True,
            deleted_at=None,
            created_at=datetime.now(timezone.utc),
        )
        mock_users.ensure_from_auth_subject.return_value = provisioned
        app.dependency_overrides[get_users_service] = lambda: mock_users

        auth_result = MagicMock()
        auth_result.user_id = subject
        auth_result.email = "john@example.local"

        with patch("papita_txnsapi.routers.v1.auth.supabase_sign_up", return_value=auth_result) as mock_sign_up:
            client = TestClient(app)
            response = client.post(
                "/api/v1/auth/register",
                json={"username": "johndoe", "email": "john@example.local", "password": "SecurePass1!"},
            )

        assert response.status_code == 201
        assert response.json()["id"] == str(subject)
        mock_sign_up.assert_called_once()
        mock_users.ensure_from_auth_subject.assert_called_once()
        app.dependency_overrides.clear()
        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    def test_login_uses_supabase_sign_in(self, monkeypatch: pytest.MonkeyPatch) -> None:
        subject = uuid.uuid4()
        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
        monkeypatch.setenv("DATABASE_URL", "")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()

        app = create_app()
        mock_users = MagicMock()
        mock_users.ensure_from_auth_subject.return_value = UsersDTO.model_construct(
            id=subject,
            username="johndoe",
            email="john@example.local",
            password="$argon2$hash",
            active=True,
            deleted_at=None,
            created_at=datetime.now(timezone.utc),
        )
        app.dependency_overrides[get_users_service] = lambda: mock_users

        auth_result = MagicMock()
        auth_result.user_id = subject
        auth_result.email = "john@example.local"
        auth_result.access_token = "supabase-access-token"
        auth_result.expires_in = 3600

        with patch("papita_txnsapi.routers.v1.auth.supabase_sign_in", return_value=auth_result):
            client = TestClient(app)
            response = client.post(
                "/api/v1/auth/login",
                data={"username": "john@example.local", "password": "SecurePass1!"},
            )

        assert response.status_code == 200
        assert response.json()["access_token"] == "supabase-access-token"
        mock_users.ensure_from_auth_subject.assert_called_once()
        app.dependency_overrides.clear()
        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
