"""Unit tests for Supabase Auth client helpers."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from papita_txnsapi.core.supabase_auth import (
    AuthApiError,
    SupabaseSignUpProfile,
    classify_supabase_auth_error,
    clear_supabase_client_cache,
    create_supabase_admin_client,
    create_supabase_auth_client,
    supabase_admin_delete_user,
    supabase_auth_user_created_recently,
    supabase_refresh_session,
    supabase_sign_in,
    supabase_sign_out,
    supabase_sign_up,
)


def test_create_supabase_auth_client_reuses_cached_instance() -> None:
    clear_supabase_client_cache()
    sentinel = MagicMock(name="auth-client")
    with patch("papita_txnsapi.core.supabase_auth.create_client", return_value=sentinel) as mock_create:
        first = create_supabase_auth_client(supabase_url="https://example.supabase.co/", anon_key="anon")
        second = create_supabase_auth_client(supabase_url="https://example.supabase.co", anon_key="anon")
    assert first is second is sentinel
    mock_create.assert_called_once_with("https://example.supabase.co", "anon")
    clear_supabase_client_cache()


def test_create_supabase_admin_client_reuses_cached_instance() -> None:
    clear_supabase_client_cache()
    sentinel = MagicMock(name="admin-client")
    with patch("papita_txnsapi.core.supabase_auth.create_client", return_value=sentinel) as mock_create:
        first = create_supabase_admin_client(
            supabase_url="https://example.supabase.co",
            service_role_key="service",
        )
        second = create_supabase_admin_client(
            supabase_url="https://example.supabase.co",
            service_role_key="service",
        )
    assert first is second is sentinel
    mock_create.assert_called_once()
    clear_supabase_client_cache()



def test_classify_supabase_auth_error_conflict() -> None:
    status_code, detail = classify_supabase_auth_error(
        AuthApiError("User already registered", 400, "email_exists"),
        fallback="failed",
    )
    assert status_code == 409
    assert detail == "Email already registered"


def test_classify_supabase_auth_error_rate_limit() -> None:
    status_code, detail = classify_supabase_auth_error(
        AuthApiError("email rate limit exceeded", 429, "over_email_send_rate_limit"),
        fallback="failed",
    )
    assert status_code == 429


def test_classify_supabase_auth_error_masks_raw_4xx_detail() -> None:
    status_code, detail = classify_supabase_auth_error(
        AuthApiError("GoTrue internal stacktrace leak", 400, "unexpected_failure"),
        fallback="failed",
    )
    assert status_code == 400
    assert detail == "Authentication request failed"
    assert "stacktrace" not in detail


def test_supabase_admin_delete_user() -> None:
    subject = uuid.uuid4()
    client = MagicMock()
    supabase_admin_delete_user(
        supabase_url="https://example.supabase.co",
        service_role_key="service-role",
        user_id=subject,
        client=client,
    )
    client.auth.admin.delete_user.assert_called_once_with(str(subject), should_soft_delete=False)


def test_supabase_auth_user_created_recently_true() -> None:
    from datetime import datetime, timezone

    subject = uuid.uuid4()
    client = MagicMock()
    client.auth.admin.get_user_by_id.return_value = SimpleNamespace(
        user=SimpleNamespace(created_at=datetime.now(timezone.utc).isoformat())
    )
    assert (
        supabase_auth_user_created_recently(
            supabase_url="https://example.supabase.co",
            service_role_key="service-role",
            user_id=subject,
            client=client,
        )
        is True
    )


def test_supabase_sign_up_maps_user_and_metadata() -> None:
    subject = uuid.uuid4()
    client = MagicMock()
    client.auth.sign_up.return_value = SimpleNamespace(
        user=SimpleNamespace(id=str(subject), email="a@example.local"),
        session=None,
    )
    result = supabase_sign_up(
        supabase_url="https://example.supabase.co",
        anon_key="anon",
        email="a@example.local",
        password="SecurePass1!",
        profile=SupabaseSignUpProfile(username="alice01"),
        client=client,
    )
    assert result.user_id == subject
    assert result.email == "a@example.local"
    assert result.access_token is None
    assert result.refresh_token is None
    client.auth.sign_up.assert_called_once()
    payload = client.auth.sign_up.call_args.args[0]
    assert payload["options"]["data"]["username"] == "alice01"
    assert payload["options"]["data"]["provider"] == "email"


def test_supabase_sign_in_requires_access_token() -> None:
    subject = uuid.uuid4()
    client = MagicMock()
    client.auth.sign_in_with_password.return_value = SimpleNamespace(
        user=SimpleNamespace(id=str(subject), email="a@example.local"),
        session=SimpleNamespace(access_token="tok", refresh_token="rtok", expires_in=120),
    )
    result = supabase_sign_in(
        supabase_url="https://example.supabase.co",
        anon_key="anon",
        email="a@example.local",
        password="SecurePass1!",
        client=client,
    )
    assert result.access_token == "tok"
    assert result.refresh_token == "rtok"
    assert result.expires_in == 120


def test_supabase_refresh_session_rotates_tokens() -> None:
    subject = uuid.uuid4()
    client = MagicMock()
    client.auth.refresh_session.return_value = SimpleNamespace(
        user=SimpleNamespace(id=str(subject), email="a@example.local"),
        session=SimpleNamespace(access_token="new-tok", refresh_token="new-rtok", expires_in=90),
    )
    result = supabase_refresh_session(
        supabase_url="https://example.supabase.co",
        anon_key="anon",
        refresh_token="old-rtok",
        client=client,
    )
    assert result.access_token == "new-tok"
    assert result.refresh_token == "new-rtok"
    client.auth.refresh_session.assert_called_once_with("old-rtok")


def test_supabase_refresh_session_rejects_blank_token() -> None:
    with pytest.raises(ValueError, match="refresh_token is required"):
        supabase_refresh_session(
            supabase_url="https://example.supabase.co",
            anon_key="anon",
            refresh_token="   ",
            client=MagicMock(),
        )


def test_supabase_oauth_authorize_url() -> None:
    client = MagicMock()
    client.auth.sign_in_with_oauth.return_value = SimpleNamespace(
        url="https://example.supabase.co/auth/v1/authorize?provider=google"
    )
    client.auth._storage = MagicMock()
    client.auth._storage.get_item.return_value = "pkce-verifier-0123456789abcdef"
    client.auth._storage_key = "supabase.auth.token"
    from papita_txnsapi.core.supabase_auth import supabase_oauth_authorize_url

    started = supabase_oauth_authorize_url(
        supabase_url="https://example.supabase.co",
        anon_key="anon",
        provider="google",
        redirect_to="http://localhost:3000/cb",
        client=client,
    )
    assert "authorize" in started.url
    assert started.code_verifier.startswith("pkce-verifier")
    creds = client.auth.sign_in_with_oauth.call_args.args[0]
    assert creds["provider"] == "google"
    assert creds["options"]["redirect_to"] == "http://localhost:3000/cb"


def test_supabase_exchange_code_for_session() -> None:
    subject = uuid.uuid4()
    client = MagicMock()
    client.auth.exchange_code_for_session.return_value = SimpleNamespace(
        user=SimpleNamespace(id=str(subject), email="a@gmail.com"),
        session=SimpleNamespace(access_token="atok", refresh_token="rtok", expires_in=60),
    )
    from papita_txnsapi.core.supabase_auth import supabase_exchange_code_for_session

    result = supabase_exchange_code_for_session(
        supabase_url="https://example.supabase.co",
        anon_key="anon",
        auth_code="auth-code",
        code_verifier="pkce-verifier-0123456789abcdef",
        client=client,
    )
    assert result.user_id == subject
    assert result.access_token == "atok"
    params = client.auth.exchange_code_for_session.call_args.args[0]
    assert params["auth_code"] == "auth-code"
    assert params["code_verifier"].startswith("pkce-verifier")


def test_supabase_establish_session_maps_user() -> None:
    subject = uuid.uuid4()
    client = MagicMock()
    client.auth.set_session.return_value = SimpleNamespace(
        user=SimpleNamespace(id=str(subject), email="a@gmail.com"),
        session=SimpleNamespace(access_token="atok", refresh_token="rtok", expires_in=60),
    )
    from papita_txnsapi.core.supabase_auth import supabase_establish_session

    result = supabase_establish_session(
        supabase_url="https://example.supabase.co",
        anon_key="anon",
        access_token="atok",
        refresh_token="rtok",
        client=client,
    )
    assert result.user_id == subject
    assert result.email == "a@gmail.com"
    assert result.access_token == "atok"
