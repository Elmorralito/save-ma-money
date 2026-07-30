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
    is_email_not_confirmed_error,
    is_invalid_credentials_error,
    maybe_auto_confirm_auth_email,
    supabase_admin_confirm_email,
    supabase_admin_delete_user,
    supabase_auth_user_created_recently,
    supabase_refresh_session,
    supabase_sign_in,
    supabase_sign_out,
    supabase_sign_up,
)
from papita_txnsapi.core.supabase_auth_local import (
    SupabaseClientOverrides,
    _auth_user_email_unconfirmed,
    _email_from_auth_user,
    _result_from_admin_user_response,
    _user_id_from_auth_user,
    supabase_admin_create_user,
    supabase_register_user,
    supabase_sign_in_with_optional_auto_confirm,
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
    assert "rate limit" in detail.lower()


def test_supabase_admin_create_user_skips_email() -> None:
    subject = uuid.uuid4()
    client = MagicMock()
    client.auth.admin.create_user.return_value = SimpleNamespace(
        user=SimpleNamespace(id=str(subject), email="a@example.local"),
    )
    result = supabase_admin_create_user(
        supabase_url="https://example.supabase.co",
        service_role_key="service-role",
        email="a@example.local",
        password="SecurePass1!",
        profile=SupabaseSignUpProfile(username="alice01"),
        client=client,
    )
    assert result.user_id == subject
    assert result.access_token is None
    payload = client.auth.admin.create_user.call_args.args[0]
    assert payload["email_confirm"] is True
    assert payload["user_metadata"]["username"] == "alice01"


def test_supabase_register_user_prefers_admin_create() -> None:
    subject = uuid.uuid4()
    admin = MagicMock()
    admin.auth.admin.create_user.return_value = SimpleNamespace(
        user=SimpleNamespace(id=str(subject), email="a@example.local"),
    )
    anon = MagicMock()
    result = supabase_register_user(
        supabase_url="https://example.supabase.co",
        anon_key="anon",
        email="a@example.local",
        password="SecurePass1!",
        service_role_key="service-role",
        prefer_admin_create=True,
        clients=SupabaseClientOverrides(anon=anon, admin=admin),
    )
    assert result.user_id == subject
    admin.auth.admin.create_user.assert_called_once()
    anon.auth.sign_up.assert_not_called()


def test_classify_supabase_auth_error_masks_raw_4xx_detail() -> None:
    status_code, detail = classify_supabase_auth_error(
        AuthApiError("GoTrue internal stacktrace leak", 400, "unexpected_failure"),
        fallback="failed",
    )
    assert status_code == 400
    assert detail == "Authentication request failed"
    assert "stacktrace" not in detail


def test_classify_supabase_auth_error_email_not_confirmed() -> None:
    status_code, detail = classify_supabase_auth_error(
        AuthApiError("Email not confirmed", 400, "email_not_confirmed"),
        fallback="failed",
    )
    assert status_code == 401
    assert detail == "Email not confirmed"


def test_supabase_admin_confirm_email() -> None:
    subject = uuid.uuid4()
    client = MagicMock()
    supabase_admin_confirm_email(
        supabase_url="https://example.supabase.co",
        service_role_key="service-role",
        user_id=subject,
        client=client,
    )
    client.auth.admin.update_user_by_id.assert_called_once_with(str(subject), {"email_confirm": True})


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


def test_supabase_sign_in_with_optional_auto_confirm_retries_when_unconfirmed() -> None:
    subject = uuid.uuid4()
    client = MagicMock()
    client.auth.sign_in_with_password.side_effect = [
        AuthApiError("Invalid login credentials", 400, "invalid_credentials"),
        SimpleNamespace(
            user=SimpleNamespace(id=str(subject), email="a@example.local"),
            session=SimpleNamespace(access_token="tok", refresh_token="rtok", expires_in=120),
        ),
    ]
    with (
        patch(
            "papita_txnsapi.core.supabase_auth_local._auth_user_email_unconfirmed",
            return_value=True,
        ) as mock_unconfirmed,
        patch(
            "papita_txnsapi.core.supabase_auth_local.maybe_auto_confirm_auth_email",
            return_value=True,
        ) as mock_confirm,
    ):
        result = supabase_sign_in_with_optional_auto_confirm(
            supabase_url="https://example.supabase.co",
            anon_key="anon",
            email="a@example.local",
            password="SecurePass1!",
            service_role_key="service-role",
            auth_user_id=subject,
            auto_confirm=True,
            client=client,
        )
    assert result.access_token == "tok"
    mock_unconfirmed.assert_called_once()
    mock_confirm.assert_called_once()
    assert client.auth.sign_in_with_password.call_count == 2


def test_supabase_sign_in_with_optional_auto_confirm_skips_when_already_confirmed() -> None:
    subject = uuid.uuid4()
    client = MagicMock()
    client.auth.sign_in_with_password.side_effect = AuthApiError(
        "Invalid login credentials",
        400,
        "invalid_credentials",
    )
    with (
        patch(
            "papita_txnsapi.core.supabase_auth_local._auth_user_email_unconfirmed",
            return_value=False,
        ) as mock_unconfirmed,
        patch(
            "papita_txnsapi.core.supabase_auth_local.maybe_auto_confirm_auth_email",
        ) as mock_confirm,
    ):
        with pytest.raises(AuthApiError):
            supabase_sign_in_with_optional_auto_confirm(
                supabase_url="https://example.supabase.co",
                anon_key="anon",
                email="a@example.local",
                password="wrong-password",
                service_role_key="service-role",
                auth_user_id=subject,
                auto_confirm=True,
                client=client,
            )
    mock_unconfirmed.assert_called_once()
    mock_confirm.assert_not_called()
    assert client.auth.sign_in_with_password.call_count == 1


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


def test_is_email_not_confirmed_error_by_code_and_message() -> None:
    assert is_email_not_confirmed_error(AuthApiError("x", 400, "email_not_confirmed"))
    assert is_email_not_confirmed_error(AuthApiError("Email not confirmed", 400, "other"))
    assert not is_email_not_confirmed_error(AuthApiError("nope", 400, "invalid_credentials"))


def test_is_invalid_credentials_error_variants() -> None:
    assert is_invalid_credentials_error(AuthApiError("Email not confirmed", 400, "email_not_confirmed"))
    assert is_invalid_credentials_error(AuthApiError("bad", 400, "invalid_credentials"))
    assert is_invalid_credentials_error(AuthApiError("bad", 400, "invalid_grant"))
    assert is_invalid_credentials_error(AuthApiError("Invalid login", 401, "other"))
    assert not is_invalid_credentials_error(AuthApiError("rate limited", 429, "over_email_send_rate_limit"))


def test_supabase_admin_confirm_email_requires_service_role_and_user_id() -> None:
    with pytest.raises(ValueError, match="SUPABASE_SERVICE_ROLE_KEY"):
        supabase_admin_confirm_email(
            supabase_url="https://example.supabase.co",
            service_role_key="  ",
            user_id=uuid.uuid4(),
            client=MagicMock(),
        )
    with pytest.raises(ValueError, match="user_id is required"):
        supabase_admin_confirm_email(
            supabase_url="https://example.supabase.co",
            service_role_key="service-role",
            user_id="   ",
            client=MagicMock(),
        )


def test_maybe_auto_confirm_auth_email_gates_and_failures() -> None:
    subject = uuid.uuid4()
    assert (
        maybe_auto_confirm_auth_email(
            supabase_url="https://example.supabase.co",
            service_role_key="service-role",
            user_id=subject,
            enabled=False,
        )
        is False
    )
    assert (
        maybe_auto_confirm_auth_email(
            supabase_url="https://example.supabase.co",
            service_role_key=None,
            user_id=subject,
            enabled=True,
        )
        is False
    )
    with patch(
        "papita_txnsapi.core.supabase_auth.supabase_admin_confirm_email",
        side_effect=AuthApiError("nope", 400, "unexpected_failure"),
    ):
        assert (
            maybe_auto_confirm_auth_email(
                supabase_url="https://example.supabase.co",
                service_role_key="service-role",
                user_id=subject,
                enabled=True,
            )
            is False
        )
    with patch("papita_txnsapi.core.supabase_auth.supabase_admin_confirm_email") as mock_confirm:
        assert (
            maybe_auto_confirm_auth_email(
                supabase_url="https://example.supabase.co",
                service_role_key="service-role",
                user_id=subject,
                enabled=True,
            )
            is True
        )
        mock_confirm.assert_called_once()


def test_local_auth_user_helpers_and_admin_response() -> None:
    subject = uuid.uuid4()
    assert _user_id_from_auth_user({"id": str(subject)}) == subject
    with pytest.raises(ValueError, match="missing id"):
        _user_id_from_auth_user({})
    assert _email_from_auth_user({"email": "A@Example.COM"}) == "a@example.com"
    assert _email_from_auth_user({}, fallback="fallback@example.local") == "fallback@example.local"
    result = _result_from_admin_user_response(
        SimpleNamespace(id=str(subject), email="a@example.local"),
        email_fallback="fallback@example.local",
    )
    assert result.user_id == subject
    with pytest.raises(ValueError, match="missing user"):
        _result_from_admin_user_response(SimpleNamespace())


def test_supabase_admin_create_user_requires_service_role_and_supports_phone() -> None:
    with pytest.raises(ValueError, match="SUPABASE_SERVICE_ROLE_KEY"):
        supabase_admin_create_user(
            supabase_url="https://example.supabase.co",
            service_role_key="",
            email="a@example.local",
            password="SecurePass1!",
            client=MagicMock(),
        )
    subject = uuid.uuid4()
    client = MagicMock()
    client.auth.admin.create_user.return_value = SimpleNamespace(
        user=SimpleNamespace(id=str(subject), email="a@example.local"),
    )
    supabase_admin_create_user(
        supabase_url="https://example.supabase.co",
        service_role_key="service-role",
        email="a@example.local",
        password="SecurePass1!",
        profile=SupabaseSignUpProfile(
            username="alice01",
            display_name="Alice",
            phone="+15551212",
        ),
        client=client,
    )
    payload = client.auth.admin.create_user.call_args.args[0]
    assert payload["phone"] == "+15551212"
    assert payload["phone_confirm"] is True
    assert payload["user_metadata"]["display_name"] == "Alice"


def test_supabase_register_user_falls_back_to_sign_up() -> None:
    subject = uuid.uuid4()
    anon = MagicMock()
    anon.auth.sign_up.return_value = SimpleNamespace(
        user=SimpleNamespace(id=str(subject), email="a@example.local"),
        session=None,
    )
    admin = MagicMock()
    result = supabase_register_user(
        supabase_url="https://example.supabase.co",
        anon_key="anon",
        email="a@example.local",
        password="SecurePass1!",
        service_role_key="service-role",
        prefer_admin_create=False,
        clients=SupabaseClientOverrides(anon=anon, admin=admin),
    )
    assert result.user_id == subject
    anon.auth.sign_up.assert_called_once()
    admin.auth.admin.create_user.assert_not_called()


def test_auth_user_email_unconfirmed_paths() -> None:
    subject = uuid.uuid4()
    admin = MagicMock()
    admin.auth.admin.get_user_by_id.return_value = SimpleNamespace(
        user=SimpleNamespace(email_confirmed_at=None),
    )
    with patch(
        "papita_txnsapi.core.supabase_auth_local.create_supabase_admin_client",
        return_value=admin,
    ):
        assert (
            _auth_user_email_unconfirmed(
                supabase_url="https://example.supabase.co",
                service_role_key="service-role",
                user_id=subject,
            )
            is True
        )
    admin.auth.admin.get_user_by_id.return_value = SimpleNamespace(
        user={"email_confirmed_at": "2026-07-30T00:00:00Z"},
    )
    with patch(
        "papita_txnsapi.core.supabase_auth_local.create_supabase_admin_client",
        return_value=admin,
    ):
        assert (
            _auth_user_email_unconfirmed(
                supabase_url="https://example.supabase.co",
                service_role_key="service-role",
                user_id=subject,
            )
            is False
        )
    admin.auth.admin.get_user_by_id.side_effect = AuthApiError("gone", 404, "user_not_found")
    with patch(
        "papita_txnsapi.core.supabase_auth_local.create_supabase_admin_client",
        return_value=admin,
    ):
        assert (
            _auth_user_email_unconfirmed(
                supabase_url="https://example.supabase.co",
                service_role_key="service-role",
                user_id=subject,
            )
            is False
        )


def test_supabase_sign_in_with_optional_auto_confirm_skips_when_disabled_or_unrelated() -> None:
    subject = uuid.uuid4()
    client = MagicMock()
    client.auth.sign_in_with_password.side_effect = AuthApiError(
        "Invalid login credentials",
        400,
        "invalid_credentials",
    )
    with pytest.raises(AuthApiError):
        supabase_sign_in_with_optional_auto_confirm(
            supabase_url="https://example.supabase.co",
            anon_key="anon",
            email="a@example.local",
            password="SecurePass1!",
            service_role_key="service-role",
            auth_user_id=subject,
            auto_confirm=False,
            client=client,
        )
    client.auth.sign_in_with_password.side_effect = AuthApiError("rate", 429, "over_email_send_rate_limit")
    with pytest.raises(AuthApiError):
        supabase_sign_in_with_optional_auto_confirm(
            supabase_url="https://example.supabase.co",
            anon_key="anon",
            email="a@example.local",
            password="SecurePass1!",
            service_role_key="service-role",
            auth_user_id=subject,
            auto_confirm=True,
            client=client,
        )


def test_supabase_sign_in_with_optional_auto_confirm_raises_when_confirm_fails() -> None:
    subject = uuid.uuid4()
    client = MagicMock()
    client.auth.sign_in_with_password.side_effect = AuthApiError(
        "Email not confirmed",
        400,
        "email_not_confirmed",
    )
    with (
        patch(
            "papita_txnsapi.core.supabase_auth_local._auth_user_email_unconfirmed",
            return_value=True,
        ),
        patch(
            "papita_txnsapi.core.supabase_auth_local.maybe_auto_confirm_auth_email",
            return_value=False,
        ),
    ):
        with pytest.raises(AuthApiError):
            supabase_sign_in_with_optional_auto_confirm(
                supabase_url="https://example.supabase.co",
                anon_key="anon",
                email="a@example.local",
                password="SecurePass1!",
                service_role_key="service-role",
                auth_user_id=subject,
                auto_confirm=True,
                client=client,
            )
