"""Unit tests covering direct Google OAuth PKCE and Gmail OAuth/disconnect routes."""

from __future__ import annotations

import io
import json
import urllib.parse
import uuid
from typing import Any

import pytest
from auth_helpers import make_user
from fastapi.testclient import TestClient

from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.core import oauth_txns
from papita_txnsapi.routers.v1 import auth as auth_router
from papita_txnsapi.routers.v1 import ingestion as ingestion_router


def test_google_oauth_unconfigured_and_post_callback_501(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Direct OAuth returns 503 when Google creds are absent, and POST /oauth/callback returns 501."""
    monkeypatch.setattr(auth_router, "_has_direct_google_oauth", lambda _settings: False)

    res_start = client.get("/api/v1/auth/oauth/google")
    assert res_start.status_code == 503

    res_bad = client.get("/api/v1/auth/oauth/unknown")
    assert res_bad.status_code == 404

    res_post = client.post(
        "/api/v1/auth/oauth/callback",
        json={"auth_code": "code1234", "code_verifier": "v" * 24},
    )
    assert res_post.status_code == 501


def test_google_oauth_start_and_callback_roundtrip(
    users_client: tuple[TestClient, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Start Google OAuth PKCE with follow=true and complete GET /oauth/callback cleanly."""
    test_client, mock_users = users_client
    oauth_txns._TXNS.clear()  # noqa: SLF001

    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("AUTH_PROVIDER", "local")
    get_settings.cache_clear()

    # Non-follow mode returns OAuthStartResponse JSON
    json_start = test_client.get("/api/v1/auth/oauth/google")
    assert json_start.status_code == 200
    assert "accounts.google.com" in json_start.json()["url"]

    # Follow mode sets opaque cookie and redirects to Google with sanitized return_to
    follow_start = test_client.get(
        "/api/v1/auth/oauth/google?follow=true&return_to=/settings?tab=integrations&evil=1",
        follow_redirects=False,
    )
    assert follow_start.status_code == 302
    loc = follow_start.headers["location"]
    parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query)
    state = parsed_qs["state"][0]
    assert "papita_oauth_cv" in follow_start.cookies

    # Callback rejects state mismatch cleanly
    bad_cb = test_client.get("/api/v1/auth/oauth/callback?code=c&state=wrong", follow_redirects=False)
    assert bad_cb.status_code == 302
    assert bad_cb.headers["location"] == "/login?oauth_error=1"

    # Re-issue handshake for happy path
    follow2 = test_client.get(
        "/api/v1/auth/oauth/google?follow=true&return_to=/reports",
        follow_redirects=False,
    )
    state2 = urllib.parse.parse_qs(urllib.parse.urlparse(follow2.headers["location"]).query)["state"][0]

    monkeypatch.setattr(
        auth_router,
        "_exchange_google_code",
        lambda **kwargs: {
            "email": "oauth.user@example.com",
            "email_verified": True,
            "name": "OAuth User",
            "sub": "google-sub-123",
        },
    )
    created_user = make_user(email="oauth.user@example.com")
    mock_users.get_by_email.return_value = None
    mock_users.ensure_from_auth_subject.return_value = created_user

    ok_cb = test_client.get(
        f"/api/v1/auth/oauth/callback?code=auth-code-1&state={state2}",
        follow_redirects=False,
    )
    assert ok_cb.status_code == 302
    assert ok_cb.headers["location"] == "/reports"
    assert "papita_access_token" in ok_cb.cookies
    assert state != state2

    # Unverified Google email redirects to /login?oauth_error=1
    follow3 = test_client.get("/api/v1/auth/oauth/google?follow=true", follow_redirects=False)
    state3 = urllib.parse.parse_qs(urllib.parse.urlparse(follow3.headers["location"]).query)["state"][0]
    monkeypatch.setattr(
        auth_router,
        "_exchange_google_code",
        lambda **kwargs: {"email": "bad@example.com", "email_verified": False},
    )
    unverified_cb = test_client.get(
        f"/api/v1/auth/oauth/callback?code=c&state={state3}",
        follow_redirects=False,
    )
    assert unverified_cb.status_code == 302
    assert unverified_cb.headers["location"] == "/login?oauth_error=1"


def test_gmail_oauth_start_callback_and_disconnect(
    ingestion_client: tuple[TestClient, Any, Any, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Start Gmail OAuth, complete callback saving encrypted token, and disconnect cleanly."""
    test_client, owner, mock_conns, _mock_runs = ingestion_client
    oauth_txns._TXNS.clear()  # noqa: SLF001

    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-for-gmail-tests-012345")
    get_settings.cache_clear()

    from papita_txnsapi.dependencies.services import get_users_service

    mock_users = type("U", (), {"get_owner": staticmethod(lambda uid: owner if uid == owner.id else None)})()
    test_client.app.dependency_overrides[get_users_service] = lambda: mock_users  # type: ignore[union-attr]

    start = test_client.get("/api/v1/ingestion/gmail/oauth/start", follow_redirects=False)
    assert start.status_code == 302
    assert "papita_gmail_state" in start.cookies
    gmail_state = urllib.parse.parse_qs(urllib.parse.urlparse(start.headers["location"]).query)["state"][0]

    # Bad state redirects to error
    bad = test_client.get("/api/v1/ingestion/gmail/oauth/callback?code=c&state=nope", follow_redirects=False)
    assert bad.status_code == 302
    assert bad.headers["location"] == "/settings?tab=integrations&gmail=error"

    # Restart for happy callback
    start2 = test_client.get("/api/v1/ingestion/gmail/oauth/start", follow_redirects=False)
    gmail_state2 = urllib.parse.parse_qs(urllib.parse.urlparse(start2.headers["location"]).query)["state"][0]

    class _FakeHttpResp:
        def __init__(self, payload: dict[str, Any]) -> None:
            self._buf = io.BytesIO(json.dumps(payload).encode("utf-8"))

        def read(self) -> bytes:
            return self._buf.read()

        def __enter__(self) -> _FakeHttpResp:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def fake_urlopen(req: Any, timeout: float = 15) -> _FakeHttpResp:
        del timeout
        if "oauth2.googleapis.com/token" in req.full_url:
            return _FakeHttpResp({"access_token": "at-1", "refresh_token": "rt-fixture-val"})
        return _FakeHttpResp({"email": "gmail.user@gmail.com"})

    monkeypatch.setattr(ingestion_router.urllib.request, "urlopen", fake_urlopen)
    ok = test_client.get(
        f"/api/v1/ingestion/gmail/oauth/callback?code=c1&state={gmail_state2}",
        follow_redirects=False,
    )
    assert ok.status_code == 302
    assert ok.headers["location"] == "/settings?tab=integrations&gmail=connected"
    mock_conns.set_gmail_credentials.assert_called_once()
    assert gmail_state != gmail_state2

    # Disconnect flow revokes token and clears DB credentials
    from types import SimpleNamespace

    encrypted_rt = ingestion_router._fernet_for_settings(get_settings()).encrypt(b"rt-fixture-val").decode("ascii")  # noqa: SLF001
    existing_conn = SimpleNamespace(
        id=uuid.uuid4(),
        owner_id=owner.id,
        provider="email",
        flow_name="papita-email-ingestion",
        deployment_name="email-ingest",
        enabled=True,
        lookback_hours=72,
        email_senders=[],
        email_subjects=[],
        email_source_label="inbox",
        email_query="",
        parsing_rules=[],
        gmail_refresh_token_enc=encrypted_rt,
        gmail_connected_email="gmail.user@gmail.com",
        gmail_access_enabled=True,
        gmail_connected_at=None,
        created_at=None,
        updated_at=None,
    )
    mock_conns.get_connection_by_natural_key.return_value = existing_conn
    cleared_conn = SimpleNamespace(
        **{**vars(existing_conn), "gmail_refresh_token_enc": None, "gmail_access_enabled": False}
    )
    mock_conns.set_gmail_credentials.return_value = cleared_conn
    monkeypatch.setattr(ingestion_router.urllib.request, "urlopen", lambda req, timeout=10: _FakeHttpResp({}))

    disc = test_client.post("/api/v1/ingestion/gmail/disconnect", headers={"Origin": "http://testserver"})
    assert disc.status_code == 200
