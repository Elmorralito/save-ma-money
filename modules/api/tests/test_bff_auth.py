"""Tests for BFF HttpOnly cookie sessions (PPT-049)."""

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
from supabase_auth.errors import AuthApiError

from auth_helpers import make_user
from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.core.bff_session import (
    BFF_CSRF_HEADER,
    BFF_SESSION_COOKIE,
    BffSessionStore,
    clear_memory_bff_sessions,
)
from papita_txnsapi.core.rate_limit import InMemoryRateLimiter
from papita_txnsapi.core.security import AuthSecurityManager, supabase_issuer
from papita_txnsapi.dependencies.services import get_users_service
from papita_txnsapi.main import create_app
from papita_txnsmodel.access.users.dto import UsersDTO


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


@pytest.fixture
def rsa_keypair():
    """Ephemeral RSA keypair for minting Supabase-style JWTs in BFF tests."""
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
) -> str:
    now = int(time.time())
    payload = {
        "sub": str(subject),
        "email": email,
        "aud": "authenticated",
        "iss": supabase_issuer(supabase_url),
        "role": "authenticated",
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": "test-kid"})


def _configure_supabase_jwks(public_pem: bytes) -> None:
    AuthSecurityManager.reset_instances()
    settings = get_settings()
    manager = AuthSecurityManager(settings)

    class _Key:
        key = public_pem

    manager._jwks_client = MagicMock()
    manager._jwks_client.get_signing_key_from_jwt.return_value = _Key()


def _supabase_owner(subject: uuid.UUID, email: str) -> UsersDTO:
    return UsersDTO.model_construct(
        id=subject,
        username="bffuser",
        email=email,
        password=None,
        auth_provider="supabase",
        active=True,
        deleted_at=None,
        created_at=datetime.now(timezone.utc),
    )


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

    def test_session_probe_authenticated_includes_csrf(self, bff_client: tuple[TestClient, MagicMock]) -> None:
        client, _ = bff_client
        login = client.post(
            "/api/v1/bff/auth/login",
            json={"email": "bff@example.com", "password": "password12"},
        )
        csrf = login.json()["csrf_token"]
        session = client.get("/api/v1/bff/auth/session")
        assert session.status_code == 200
        body = session.json()
        assert body["authenticated"] is True
        assert body["csrf_token"] == csrf

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

    def test_login_rejects_bad_credentials(self, bff_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_users = bff_client
        mock_users.verify_credentials.return_value = None
        response = client.post(
            "/api/v1/bff/auth/login",
            json={"email": "bff@example.com", "password": "wrong-password"},
        )
        assert response.status_code == 401

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

    def test_mutation_with_wrong_csrf_is_forbidden(self, bff_client: tuple[TestClient, MagicMock]) -> None:
        client, _ = bff_client
        login = client.post(
            "/api/v1/bff/auth/login",
            json={"email": "bff@example.com", "password": "password12"},
        )
        assert login.status_code == 200
        denied = client.post("/api/v1/bff/auth/logout", headers={BFF_CSRF_HEADER: "not-the-token"})
        assert denied.status_code == 403

    def test_unknown_cookie_skips_csrf_and_continues(self, bff_client: tuple[TestClient, MagicMock]) -> None:
        client, _ = bff_client
        client.cookies.set(BFF_SESSION_COOKIE, "unknown-session-id-abcdefgh")
        # No matching store record → CSRF middleware continues; logout clears cookie.
        response = client.post("/api/v1/bff/auth/logout")
        assert response.status_code == 204

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

    def test_refresh_requires_supabase_provider(self, bff_client: tuple[TestClient, MagicMock]) -> None:
        client, _ = bff_client
        login = client.post(
            "/api/v1/bff/auth/login",
            json={"email": "bff@example.com", "password": "password12"},
        )
        csrf = login.json()["csrf_token"]
        refresh = client.post("/api/v1/bff/auth/refresh", headers={BFF_CSRF_HEADER: csrf})
        assert refresh.status_code == 501
        assert "supabase" in refresh.json()["detail"].lower()

    def test_refresh_missing_cookie_is_unauthorized(self, bff_client: tuple[TestClient, MagicMock]) -> None:
        client, _ = bff_client
        response = client.post("/api/v1/bff/auth/refresh")
        assert response.status_code == 401

    def test_refresh_invalid_session_is_unauthorized(self, bff_client: tuple[TestClient, MagicMock]) -> None:
        client, _ = bff_client
        client.cookies.set(BFF_SESSION_COOKIE, "missing-session-abcdefghij")
        response = client.post("/api/v1/bff/auth/refresh")
        assert response.status_code == 401


class TestBffSupabaseCookieSession:
    """Supabase IdP branches for BFF login/register/refresh/logout + silent refresh."""

    def test_login_sets_cookie_and_authorizes_me(
        self, rsa_keypair, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        private_pem, public_pem = rsa_keypair
        supabase_url = "https://example.supabase.co"
        subject = uuid.uuid4()
        email = "bff-sb@example.local"
        access = _mint_supabase_token(
            private_pem, subject=subject, email=email, supabase_url=supabase_url
        )

        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", supabase_url)
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
        monkeypatch.setenv("DATABASE_URL", "")
        monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()
        InMemoryRateLimiter().reset()
        clear_memory_bff_sessions()

        app = create_app()
        mock_users = MagicMock()
        mock_users.ensure_from_auth_subject.return_value = _supabase_owner(subject, email)
        app.dependency_overrides[get_users_service] = lambda: mock_users
        _configure_supabase_jwks(public_pem)

        auth_result = MagicMock()
        auth_result.user_id = subject
        auth_result.email = email
        auth_result.access_token = access
        auth_result.refresh_token = "sb-refresh"
        auth_result.expires_in = 3600

        with patch("papita_txnsapi.routers.v1.bff_auth.supabase_sign_in", return_value=auth_result):
            client = TestClient(app)
            login = client.post(
                "/api/v1/bff/auth/login",
                json={"email": email, "password": "SecurePass1!"},
            )
            assert login.status_code == 200
            assert login.json()["authenticated"] is True
            assert BFF_SESSION_COOKIE in login.cookies
            me = client.get("/api/v1/auth/me")
            assert me.status_code == 200
            assert me.json()["id"] == str(subject)

        app.dependency_overrides.clear()
        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()
        clear_memory_bff_sessions()
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    def test_login_maps_auth_api_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
        monkeypatch.setenv("DATABASE_URL", "")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()
        InMemoryRateLimiter().reset()
        clear_memory_bff_sessions()

        app = create_app()
        app.dependency_overrides[get_users_service] = lambda: MagicMock()
        with patch(
            "papita_txnsapi.routers.v1.bff_auth.supabase_sign_in",
            side_effect=AuthApiError("Invalid login credentials", 400, "invalid_credentials"),
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/bff/auth/login",
                json={"email": "x@example.local", "password": "bad-password"},
            )
        assert response.status_code == 401
        app.dependency_overrides.clear()
        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    def test_login_provision_value_error_inactive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
        monkeypatch.setenv("DATABASE_URL", "")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()
        InMemoryRateLimiter().reset()
        clear_memory_bff_sessions()

        subject = uuid.uuid4()
        app = create_app()
        mock_users = MagicMock()
        mock_users.ensure_from_auth_subject.side_effect = ValueError("User is inactive or deleted")
        app.dependency_overrides[get_users_service] = lambda: mock_users
        auth_result = MagicMock()
        auth_result.user_id = subject
        auth_result.email = "inactive@example.local"
        auth_result.access_token = "tok"
        auth_result.refresh_token = "ref"
        auth_result.expires_in = 3600
        with patch("papita_txnsapi.routers.v1.bff_auth.supabase_sign_in", return_value=auth_result):
            client = TestClient(app)
            response = client.post(
                "/api/v1/bff/auth/login",
                json={"email": "inactive@example.local", "password": "SecurePass1!"},
            )
        assert response.status_code == 401
        app.dependency_overrides.clear()
        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    def test_register_uses_supabase_sign_up(self, monkeypatch: pytest.MonkeyPatch) -> None:
        subject = uuid.uuid4()
        email = "new-bff@example.local"
        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
        monkeypatch.setenv("DATABASE_URL", "")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()
        InMemoryRateLimiter().reset()
        clear_memory_bff_sessions()

        app = create_app()
        mock_users = MagicMock()
        mock_users.ensure_from_auth_subject.return_value = _supabase_owner(subject, email)
        app.dependency_overrides[get_users_service] = lambda: mock_users
        auth_result = MagicMock()
        auth_result.user_id = subject
        auth_result.email = email
        with patch(
            "papita_txnsapi.routers.v1.bff_auth.supabase_sign_up", return_value=auth_result
        ) as mock_sign_up:
            client = TestClient(app)
            response = client.post(
                "/api/v1/bff/auth/register",
                json={"email": email, "password": "SecurePass1!"},
            )
        assert response.status_code == 201
        assert response.json()["id"] == str(subject)
        mock_sign_up.assert_called_once()
        app.dependency_overrides.clear()
        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    def test_register_maps_conflict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
        monkeypatch.setenv("DATABASE_URL", "")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()
        InMemoryRateLimiter().reset()
        clear_memory_bff_sessions()

        app = create_app()
        app.dependency_overrides[get_users_service] = lambda: MagicMock()
        with patch(
            "papita_txnsapi.routers.v1.bff_auth.supabase_sign_up",
            side_effect=AuthApiError("User already registered", 400, "email_exists"),
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/bff/auth/register",
                json={"email": "dup@example.local", "password": "SecurePass1!"},
            )
        assert response.status_code == 409
        app.dependency_overrides.clear()
        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    def test_register_provision_failure_cleans_orphan(self, monkeypatch: pytest.MonkeyPatch) -> None:
        subject = uuid.uuid4()
        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
        monkeypatch.setenv("DATABASE_URL", "")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()
        InMemoryRateLimiter().reset()
        clear_memory_bff_sessions()

        app = create_app()
        mock_users = MagicMock()
        mock_users.ensure_from_auth_subject.side_effect = ValueError("email already linked")
        app.dependency_overrides[get_users_service] = lambda: mock_users
        auth_result = MagicMock()
        auth_result.user_id = subject
        auth_result.email = "orphan@example.local"
        with (
            patch("papita_txnsapi.routers.v1.bff_auth.supabase_sign_up", return_value=auth_result),
            patch("papita_txnsapi.routers.v1.bff_auth._cleanup_orphan_auth_user") as mock_cleanup,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/bff/auth/register",
                json={"email": "orphan@example.local", "password": "SecurePass1!"},
            )
        assert response.status_code in {400, 409, 500, 502}
        mock_cleanup.assert_called_once()
        app.dependency_overrides.clear()
        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    def test_refresh_rotates_cookie_and_tokens(
        self, rsa_keypair, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        private_pem, public_pem = rsa_keypair
        supabase_url = "https://example.supabase.co"
        subject = uuid.uuid4()
        email = "refresh@example.local"
        access = _mint_supabase_token(
            private_pem, subject=subject, email=email, supabase_url=supabase_url
        )
        rotated = _mint_supabase_token(
            private_pem, subject=subject, email=email, supabase_url=supabase_url
        )

        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", supabase_url)
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
        monkeypatch.setenv("DATABASE_URL", "")
        monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()
        InMemoryRateLimiter().reset()
        clear_memory_bff_sessions()

        app = create_app()
        mock_users = MagicMock()
        mock_users.ensure_from_auth_subject.return_value = _supabase_owner(subject, email)
        app.dependency_overrides[get_users_service] = lambda: mock_users
        _configure_supabase_jwks(public_pem)

        login_result = MagicMock()
        login_result.user_id = subject
        login_result.email = email
        login_result.access_token = access
        login_result.refresh_token = "old-refresh"
        login_result.expires_in = 3600

        refresh_result = MagicMock()
        refresh_result.user_id = subject
        refresh_result.email = email
        refresh_result.access_token = rotated
        refresh_result.refresh_token = "new-refresh"
        refresh_result.expires_in = 1800

        with (
            patch("papita_txnsapi.routers.v1.bff_auth.supabase_sign_in", return_value=login_result),
            patch(
                "papita_txnsapi.routers.v1.bff_auth.supabase_refresh_session",
                return_value=refresh_result,
            ) as mock_refresh,
        ):
            client = TestClient(app)
            login = client.post(
                "/api/v1/bff/auth/login",
                json={"email": email, "password": "SecurePass1!"},
            )
            assert login.status_code == 200
            old_sid = login.cookies.get(BFF_SESSION_COOKIE)
            csrf = login.json()["csrf_token"]
            refreshed = client.post(
                "/api/v1/bff/auth/refresh",
                headers={BFF_CSRF_HEADER: csrf},
            )
            assert refreshed.status_code == 200
            assert refreshed.json()["authenticated"] is True
            assert refreshed.json()["csrf_token"] == csrf
            new_sid = refreshed.cookies.get(BFF_SESSION_COOKIE)
            assert new_sid
            assert new_sid != old_sid
            mock_refresh.assert_called_once()
            me = client.get("/api/v1/auth/me")
            assert me.status_code == 200

        app.dependency_overrides.clear()
        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()
        clear_memory_bff_sessions()
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    def test_refresh_without_refresh_token_is_unauthorized(
        self, rsa_keypair, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        private_pem, public_pem = rsa_keypair
        supabase_url = "https://example.supabase.co"
        subject = uuid.uuid4()
        email = "noref@example.local"
        access = _mint_supabase_token(
            private_pem, subject=subject, email=email, supabase_url=supabase_url
        )

        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", supabase_url)
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
        monkeypatch.setenv("DATABASE_URL", "")
        monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()
        InMemoryRateLimiter().reset()
        clear_memory_bff_sessions()

        app = create_app()
        mock_users = MagicMock()
        mock_users.ensure_from_auth_subject.return_value = _supabase_owner(subject, email)
        app.dependency_overrides[get_users_service] = lambda: mock_users
        _configure_supabase_jwks(public_pem)

        store = BffSessionStore(None, default_ttl_seconds=3600)
        sid, record = store.create(
            access_token=access,
            refresh_token=None,
            expires_in=3600,
            owner_id=str(subject),
        )
        client = TestClient(app)
        client.cookies.set(BFF_SESSION_COOKIE, sid)
        response = client.post(
            "/api/v1/bff/auth/refresh",
            headers={BFF_CSRF_HEADER: record.csrf_token},
        )
        assert response.status_code == 401
        assert "refresh token" in response.json()["detail"].lower()

        app.dependency_overrides.clear()
        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()
        clear_memory_bff_sessions()
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    def test_refresh_auth_error_is_unauthorized(
        self, rsa_keypair, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        private_pem, public_pem = rsa_keypair
        supabase_url = "https://example.supabase.co"
        subject = uuid.uuid4()
        email = "badref@example.local"
        access = _mint_supabase_token(
            private_pem, subject=subject, email=email, supabase_url=supabase_url
        )

        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", supabase_url)
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
        monkeypatch.setenv("DATABASE_URL", "")
        monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()
        InMemoryRateLimiter().reset()
        clear_memory_bff_sessions()

        app = create_app()
        mock_users = MagicMock()
        mock_users.ensure_from_auth_subject.return_value = _supabase_owner(subject, email)
        app.dependency_overrides[get_users_service] = lambda: mock_users
        _configure_supabase_jwks(public_pem)

        login_result = MagicMock()
        login_result.user_id = subject
        login_result.email = email
        login_result.access_token = access
        login_result.refresh_token = "stale-refresh"
        login_result.expires_in = 3600

        with (
            patch("papita_txnsapi.routers.v1.bff_auth.supabase_sign_in", return_value=login_result),
            patch(
                "papita_txnsapi.routers.v1.bff_auth.supabase_refresh_session",
                side_effect=AuthApiError("Invalid refresh token", 401, "invalid_grant"),
            ),
        ):
            client = TestClient(app)
            login = client.post(
                "/api/v1/bff/auth/login",
                json={"email": email, "password": "SecurePass1!"},
            )
            csrf = login.json()["csrf_token"]
            refreshed = client.post(
                "/api/v1/bff/auth/refresh",
                headers={BFF_CSRF_HEADER: csrf},
            )
        assert refreshed.status_code == 401

        app.dependency_overrides.clear()
        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()
        clear_memory_bff_sessions()
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    def test_logout_calls_supabase_sign_out(
        self, rsa_keypair, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        private_pem, public_pem = rsa_keypair
        supabase_url = "https://example.supabase.co"
        subject = uuid.uuid4()
        email = "out@example.local"
        access = _mint_supabase_token(
            private_pem, subject=subject, email=email, supabase_url=supabase_url
        )

        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", supabase_url)
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
        monkeypatch.setenv("DATABASE_URL", "")
        monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()
        InMemoryRateLimiter().reset()
        clear_memory_bff_sessions()

        app = create_app()
        mock_users = MagicMock()
        mock_users.ensure_from_auth_subject.return_value = _supabase_owner(subject, email)
        app.dependency_overrides[get_users_service] = lambda: mock_users
        _configure_supabase_jwks(public_pem)

        login_result = MagicMock()
        login_result.user_id = subject
        login_result.email = email
        login_result.access_token = access
        login_result.refresh_token = "logout-refresh"
        login_result.expires_in = 3600

        with (
            patch("papita_txnsapi.routers.v1.bff_auth.supabase_sign_in", return_value=login_result),
            patch("papita_txnsapi.routers.v1.bff_auth.supabase_sign_out") as mock_sign_out,
        ):
            client = TestClient(app)
            login = client.post(
                "/api/v1/bff/auth/login",
                json={"email": email, "password": "SecurePass1!"},
            )
            csrf = login.json()["csrf_token"]
            logout = client.post(
                "/api/v1/bff/auth/logout",
                headers={BFF_CSRF_HEADER: csrf},
            )
        assert logout.status_code == 204
        mock_sign_out.assert_called_once()
        assert mock_sign_out.call_args.kwargs["refresh_token"] == "logout-refresh"

        app.dependency_overrides.clear()
        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()
        clear_memory_bff_sessions()
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    def test_logout_sign_out_failure_is_best_effort(
        self, rsa_keypair, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        private_pem, public_pem = rsa_keypair
        supabase_url = "https://example.supabase.co"
        subject = uuid.uuid4()
        email = "outfail@example.local"
        access = _mint_supabase_token(
            private_pem, subject=subject, email=email, supabase_url=supabase_url
        )

        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", supabase_url)
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
        monkeypatch.setenv("DATABASE_URL", "")
        monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()
        InMemoryRateLimiter().reset()
        clear_memory_bff_sessions()

        app = create_app()
        mock_users = MagicMock()
        mock_users.ensure_from_auth_subject.return_value = _supabase_owner(subject, email)
        app.dependency_overrides[get_users_service] = lambda: mock_users
        _configure_supabase_jwks(public_pem)

        login_result = MagicMock()
        login_result.user_id = subject
        login_result.email = email
        login_result.access_token = access
        login_result.refresh_token = "logout-refresh"
        login_result.expires_in = 3600

        with (
            patch("papita_txnsapi.routers.v1.bff_auth.supabase_sign_in", return_value=login_result),
            patch(
                "papita_txnsapi.routers.v1.bff_auth.supabase_sign_out",
                side_effect=AuthApiError("gone", 401, "session_not_found"),
            ),
        ):
            client = TestClient(app)
            login = client.post(
                "/api/v1/bff/auth/login",
                json={"email": email, "password": "SecurePass1!"},
            )
            csrf = login.json()["csrf_token"]
            logout = client.post(
                "/api/v1/bff/auth/logout",
                headers={BFF_CSRF_HEADER: csrf},
            )
        assert logout.status_code == 204

        app.dependency_overrides.clear()
        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()
        clear_memory_bff_sessions()
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    def test_silent_refresh_on_expired_access(
        self, rsa_keypair, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        private_pem, public_pem = rsa_keypair
        supabase_url = "https://example.supabase.co"
        subject = uuid.uuid4()
        email = "silent@example.local"
        stale = _mint_supabase_token(
            private_pem, subject=subject, email=email, supabase_url=supabase_url
        )
        fresh = _mint_supabase_token(
            private_pem, subject=subject, email=email, supabase_url=supabase_url
        )

        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", supabase_url)
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
        monkeypatch.setenv("DATABASE_URL", "")
        monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()
        InMemoryRateLimiter().reset()
        clear_memory_bff_sessions()

        app = create_app()
        mock_users = MagicMock()
        mock_users.ensure_from_auth_subject.return_value = _supabase_owner(subject, email)
        app.dependency_overrides[get_users_service] = lambda: mock_users
        _configure_supabase_jwks(public_pem)

        store = BffSessionStore(None, default_ttl_seconds=3600)
        # expires_in=1 → immediately inside the 30s skew window → silent refresh.
        sid, _ = store.create(
            access_token=stale,
            refresh_token="silent-refresh",
            expires_in=1,
            owner_id=str(subject),
        )

        refresh_result = MagicMock()
        refresh_result.user_id = subject
        refresh_result.email = email
        refresh_result.access_token = fresh
        refresh_result.refresh_token = "silent-refresh-2"
        refresh_result.expires_in = 3600

        with patch(
            "papita_txnsapi.dependencies.auth.supabase_refresh_session",
            return_value=refresh_result,
        ) as mock_refresh:
            client = TestClient(app)
            client.cookies.set(BFF_SESSION_COOKIE, sid)
            me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        mock_refresh.assert_called_once()

        app.dependency_overrides.clear()
        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()
        clear_memory_bff_sessions()
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    def test_silent_refresh_failure_clears_session(
        self, rsa_keypair, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        private_pem, public_pem = rsa_keypair
        supabase_url = "https://example.supabase.co"
        subject = uuid.uuid4()
        email = "silent-fail@example.local"
        stale = _mint_supabase_token(
            private_pem, subject=subject, email=email, supabase_url=supabase_url
        )

        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", supabase_url)
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
        monkeypatch.setenv("DATABASE_URL", "")
        monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
        get_settings.cache_clear()
        AuthSecurityManager.reset_instances()
        InMemoryRateLimiter().reset()
        clear_memory_bff_sessions()

        app = create_app()
        mock_users = MagicMock()
        mock_users.ensure_from_auth_subject.return_value = _supabase_owner(subject, email)
        app.dependency_overrides[get_users_service] = lambda: mock_users
        _configure_supabase_jwks(public_pem)

        store = BffSessionStore(None, default_ttl_seconds=3600)
        sid, _ = store.create(
            access_token=stale,
            refresh_token="dead-refresh",
            expires_in=1,
            owner_id=str(subject),
        )

        with patch(
            "papita_txnsapi.dependencies.auth.supabase_refresh_session",
            side_effect=AuthApiError("Invalid refresh token", 401, "invalid_grant"),
        ):
            client = TestClient(app)
            client.cookies.set(BFF_SESSION_COOKIE, sid)
            me = client.get("/api/v1/auth/me")
        assert me.status_code == 401
        assert store.get(sid) is None

        app.dependency_overrides.clear()
        AuthSecurityManager.reset_instances()
        get_settings.cache_clear()
        clear_memory_bff_sessions()
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
