"""Security hardening regression tests for CSRF, OAuth IDOR, open redirects, headers, and SQL allowlists."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from papita_txnsapi.config.settings import Settings
from papita_txnsapi.dependencies.auth import AUTH_ACCESS_COOKIE
from papita_txnsapi.main import create_app
from papita_txnsapi.routers.v1.auth import _sanitize_return_to
from papita_txnsapi.routers.v1.ingestion import _seal_gmail_oauth_txn, _unseal_gmail_oauth_txn
from papita_txnsmodel.access.owner_period_balances.repository import _PERIOD_VIEWS, OwnerPeriodBalancesRepository
from papita_txnsmodel.access.users.dto import UsersDTO


def test_gmail_oauth_txn_cookie_prevents_owner_id_tampering() -> None:
    settings = Settings(JWT_SECRET_KEY="jwt-secret-" + uuid.uuid4().hex)
    sealed = _seal_gmail_oauth_txn(
        settings,
        owner_id=str(uuid.uuid4()),
        state="state-123",
        code_verifier="verifier-456",
        callback_uri="http://localhost:3001/api/v1/ingestion/gmail/oauth/callback",
    )
    unsealed = _unseal_gmail_oauth_txn(settings, sealed)
    assert unsealed is not None
    assert unsealed["state"] == "state-123"

    # Tampering with any byte invalidates the authenticated Fernet token
    tampered = sealed[:-4] + ("AAAA" if not sealed.endswith("AAAA") else "BBBB")
    assert _unseal_gmail_oauth_txn(settings, tampered) is None
    assert _unseal_gmail_oauth_txn(settings, str(uuid.uuid4())) is None


@pytest.mark.parametrize(
    "malicious_next",
    [
        "https://evil.example/phish",
        "//evil.example/phish",
        "/\\evil.example/phish",
        "/\r\nLocation: https://evil.example",
        "/\x00/evil.example",
        "javascript:alert(1)",
    ],
)
def test_sanitize_return_to_blocks_open_redirect_bypasses(malicious_next: str) -> None:
    assert _sanitize_return_to(malicious_next) == "/dashboard"


def test_sanitize_return_to_allows_valid_relative_paths() -> None:
    assert _sanitize_return_to("/integrations?gmail=connected") == "/integrations?gmail=connected"
    assert _sanitize_return_to("/transactions") == "/transactions"


def test_cookie_csrf_middleware_blocks_cross_site_mutations_and_sets_hardened_headers() -> None:
    settings = Settings(
        DEBUG=True,
        AUTH_PROVIDER="local",
        JWT_SECRET_KEY="csrf-test-secret-" + uuid.uuid4().hex,
        ALLOWED_ORIGINS=["http://localhost:3001"],
    )
    app = create_app(settings=settings)
    client = TestClient(app)

    # 1. Cross-site Origin with session cookie -> 403
    client.cookies.set(AUTH_ACCESS_COOKIE, "dummy-session-jwt")
    resp = client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "https://evil.example"},
    )
    assert resp.status_code == 403
    assert "CSRF" in resp.json()["detail"]

    # 2. Cross-site Fetch Metadata with session cookie -> 403
    resp_fetch = client.post(
        "/api/v1/auth/logout",
        headers={"Sec-Fetch-Site": "cross-site"},
    )
    assert resp_fetch.status_code == 403

    # 2b. Missing Origin, Referer, and X-Requested-With with session cookie -> 403
    resp_bare = client.post("/api/v1/auth/logout", json={})
    assert resp_bare.status_code == 403

    # 3. Same-origin / allowed origin passes CSRF and returns hardened security headers
    resp_ok = client.post(
        "/api/v1/auth/logout",
        json={},
        headers={
            "Origin": "http://localhost:3001",
            "Sec-Fetch-Site": "same-origin",
            "X-Forwarded-Proto": "https",
        },
    )
    assert resp_ok.status_code != 403
    assert resp_ok.headers.get("Cache-Control") == "no-store"
    assert resp_ok.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp_ok.headers.get("X-Frame-Options") == "DENY"
    assert resp_ok.headers.get("X-Permitted-Cross-Domain-Policies") == "none"
    assert "camera=()" in (resp_ok.headers.get("Permissions-Policy") or "")
    assert "max-age=31536000" in (resp_ok.headers.get("Strict-Transport-Security") or "")


def test_period_balance_repository_rejects_sql_identifier_injection() -> None:
    repo = OwnerPeriodBalancesRepository()
    fake_session = MagicMock(spec=Session)
    owner = UsersDTO.model_construct(id=uuid.uuid4(), username="owner_sec", email="owner@example.com")

    with pytest.raises(ValueError, match="Unsupported balance view"):
        repo._query_period_balances(
            _db_session=fake_session,
            view_name="accounts; DROP TABLE users;--",
            owner=owner,
            balance_year=2026,
            period_column="balance_month",
            period_value=11,
            currency="COP",
            order_by="balance_year DESC, balance_month DESC, currency",
        )

    with pytest.raises(ValueError, match="Unsupported period column"):
        repo._query_period_balances(
            _db_session=fake_session,
            view_name=_PERIOD_VIEWS[0],
            owner=owner,
            balance_year=2026,
            period_column="1=1 OR balance_month",
            period_value=11,
            currency="COP",
            order_by="balance_year DESC, balance_month DESC, currency",
        )
