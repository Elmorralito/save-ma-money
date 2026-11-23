"""Tests for connector discovery endpoint and sibling AuthProvider protocol."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from papita_txnsapi.config.settings import Settings
from papita_txnsapi.core.auth_health import AuthProbeDetail
from papita_txnsapi.core.auth_provider import (
    AuthProvider,
    LocalAuthProvider,
    SupabaseAuthProvider,
    build_auth_provider,
)
from papita_txnsapi.dependencies.services import get_portfolio_import_service
from papita_txnsapi.schemas.ingestion import assert_ingestion_response_allowlist
from papita_txnsmodel.services.portfolio_import import PortfolioImportResult


def test_ingestion_connectors_endpoint_returns_non_secret_manifests(
    client: TestClient,
    authed_client: tuple[TestClient, object],
) -> None:
    assert_ingestion_response_allowlist()

    unauth = client.get("/api/v1/ingestion/connectors")
    assert unauth.status_code == 401

    authed, _owner = authed_client
    resp = authed.get("/api/v1/ingestion/connectors")
    assert resp.status_code == 200
    items = resp.json()
    plugin_ids = {item["plugin_id"] for item in items}
    assert "gmail" in plugin_ids
    assert "ibkr-activity-csv" in plugin_ids
    assert "global66-email" in plugin_ids

    filtered = authed.get("/api/v1/ingestion/connectors?kind=batch_importer")
    assert filtered.status_code == 200
    assert all(item["kind"] == "batch_importer" for item in filtered.json())


def test_build_auth_provider_local_and_supabase() -> None:
    local_settings = Settings(
        AUTH_PROVIDER="local",
        JWT_SECRET_KEY="x" * 40,
        DATABASE_URL="postgresql+psycopg2://u:p@localhost:5432/db",
    )
    local_provider = build_auth_provider(local_settings)
    assert isinstance(local_provider, LocalAuthProvider)
    assert isinstance(local_provider, AuthProvider)
    assert local_provider.supports_external_sessions is False
    probe = local_provider.probe_health()
    assert probe.reachable is True
    assert probe.detail == AuthProbeDetail.SKIPPED_LOCAL

    supa_settings = Settings(
        AUTH_PROVIDER="supabase",
        SUPABASE_URL="https://example.supabase.co",
        SUPABASE_ANON_KEY="anon-key",
        DATABASE_URL="postgresql+psycopg2://u:p@localhost:5432/db",
    )
    supa_provider = build_auth_provider(supa_settings)
    assert isinstance(supa_provider, SupabaseAuthProvider)
    assert isinstance(supa_provider, AuthProvider)
    assert supa_provider.supports_external_sessions is True


def test_local_and_supabase_auth_provider_methods() -> None:
    import pytest

    from papita_txnsapi.core import auth_provider as mod
    from papita_txnsapi.core.auth_health import AuthProbeResult
    from papita_txnsapi.dependencies.auth import get_auth_provider

    local_settings = Settings(
        AUTH_PROVIDER="local",
        JWT_SECRET_KEY="x" * 40,
        DATABASE_URL="postgresql+psycopg2://u:p@localhost:5432/db",
    )
    local = get_auth_provider(local_settings)
    assert local.provider_name == "local"
    assert local.classify_error(RuntimeError("err"), fallback="fb") == (500, "err")
    assert local.admin_delete_user(user_id="u1") is None
    assert local.user_created_recently(user_id="u1") is False

    probe_fn = MagicMock(
        return_value=AuthProbeResult(
            reachable=True, latency_ms=None, detail=AuthProbeDetail.SKIPPED_LOCAL, provider="local"
        )
    )
    assert local.probe_health(probe_fn=probe_fn).reachable is True
    probe_fn.assert_called_once()

    with pytest.raises(NotImplementedError):
        local.register(email="a@b.com", password="secret")
    with pytest.raises(NotImplementedError):
        local.sign_in(email="a@b.com", password="secret")
    with pytest.raises(NotImplementedError):
        local.refresh_session(refresh_token="rt")
    with pytest.raises(NotImplementedError):
        local.sign_out(access_token="at", refresh_token="rt")
    with pytest.raises(NotImplementedError):
        local.resend_signup_confirmation(email="a@b.com")
    with pytest.raises(NotImplementedError):
        local.oauth_authorize_url(provider="google", redirect_to="http://localhost")
    with pytest.raises(NotImplementedError):
        local.exchange_code_for_session(auth_code="c", code_verifier="v")
    with pytest.raises(NotImplementedError):
        local.establish_session(access_token="at", refresh_token="rt")

    supa_settings = Settings(
        AUTH_PROVIDER="supabase",
        SUPABASE_URL="https://example.supabase.co",
        SUPABASE_ANON_KEY="anon-key",
        SUPABASE_SERVICE_ROLE_KEY="svc-key",
        DATABASE_URL="postgresql+psycopg2://u:p@localhost:5432/db",
    )
    supa = SupabaseAuthProvider(supa_settings)
    assert supa.provider_name == "supabase"

    mp = pytest.MonkeyPatch()
    try:
        sentinel = object()
        mp.setattr(mod, "supabase_register_user", MagicMock(return_value=sentinel))
        mp.setattr(mod, "supabase_sign_in_with_optional_auto_confirm", MagicMock(return_value=sentinel))
        mp.setattr(mod, "supabase_refresh_session", MagicMock(return_value=sentinel))
        mp.setattr(mod, "supabase_sign_out", MagicMock(return_value=None))
        mp.setattr(mod, "supabase_resend_signup_confirmation", MagicMock(return_value=None))
        mp.setattr(mod, "supabase_oauth_authorize_url", MagicMock(return_value=sentinel))
        mp.setattr(mod, "supabase_exchange_code_for_session", MagicMock(return_value=sentinel))
        mp.setattr(mod, "supabase_establish_session", MagicMock(return_value=sentinel))
        mp.setattr(mod, "classify_supabase_auth_error", MagicMock(return_value=(400, "bad")))
        mp.setattr(mod, "supabase_admin_delete_user", MagicMock(return_value=None))
        mp.setattr(mod, "supabase_auth_user_created_recently", MagicMock(return_value=True))

        assert supa.register(email="a@b.com", password="pw") is sentinel
        assert supa.sign_in(email="a@b.com", password="pw") is sentinel
        assert supa.refresh_session(refresh_token="rt") is sentinel
        supa.sign_out(access_token="at", refresh_token="rt")
        supa.resend_signup_confirmation(email="a@b.com")
        assert supa.oauth_authorize_url(provider="google", redirect_to="http://x") is sentinel
        assert supa.exchange_code_for_session(auth_code="c", code_verifier="v") is sentinel
        assert supa.establish_session(access_token="at", refresh_token="rt") is sentinel
        assert supa.classify_error(RuntimeError("x"), fallback="fb") == (400, "bad")
        supa.admin_delete_user(user_id="u1")
        assert supa.user_created_recently(user_id="u1") is True
    finally:
        mp.undo()

    with pytest.raises(ValueError, match="non-empty"):
        mod.register_auth_provider("  ", LocalAuthProvider)
    with pytest.raises(ValueError, match="Duplicate"):
        mod.register_auth_provider("local", LocalAuthProvider)


def test_generic_statement_importer_endpoint_dispatches_via_registry(
    authed_client: tuple[TestClient, object],
) -> None:
    authed, _owner = authed_client

    not_found = authed.post(
        "/api/v1/ingestion/statements/unknown-broker-csv",
        json={"csv_content": "a,b,c"},
    )
    assert not_found.status_code == 404

    invalid = authed.post(
        "/api/v1/ingestion/statements/ibkr-activity-csv",
        json={"csv_content": "not,an,ibkr,statement"},
    )
    assert invalid.status_code == 422

    mock_svc = MagicMock()
    mock_svc.import_batch.return_value = PortfolioImportResult(
        account_code="U9999999",
        fx_rate=4000.0,
        base_currency="COP",
        total_portfolio_value=5_000_000.0,
    )
    authed.app.dependency_overrides[get_portfolio_import_service] = lambda: mock_svc  # type: ignore[attr-defined]
    try:
        sample_csv = "\n".join(
            [
                "Account Information,Header,Field Name,Field Value",
                "Account Information,Data,Account,U9999999",
                "Open Positions,Header,DataDiscriminator,Asset Category,Currency,Symbol,Quantity,Cost Price,Close Price,Value,Unrealized P/L",
                "Open Positions,Data,Summary,Stocks,USD,VOO,1,450,500,500,50",
            ]
        )
        ok = authed.post(
            "/api/v1/ingestion/statements/ibkr-activity-csv",
            json={"csv_content": sample_csv, "fx_rate": 4000.0, "base_currency": "COP"},
        )
        assert ok.status_code == 200
        assert ok.json()["account_code"] == "U9999999"
        mock_svc.import_batch.assert_called_once()
    finally:
        authed.app.dependency_overrides.pop(get_portfolio_import_service, None)  # type: ignore[attr-defined]
