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
