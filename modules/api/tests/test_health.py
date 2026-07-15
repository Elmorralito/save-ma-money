"""Tests for health endpoints and database/Auth probe hardening."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from papita_txnsapi.core.auth_health import AuthProbeDetail, AuthProbeResult, probe_supabase_auth
from papita_txnsapi.core.db_health import DatabaseProbeDetail, DatabaseProbeResult, probe_database


def _connected_probe(latency_ms: float = 1.25) -> DatabaseProbeResult:
    return DatabaseProbeResult(
        connected=True,
        latency_ms=latency_ms,
        detail=DatabaseProbeDetail.HEALTHY,
    )


def _disconnected_probe(
    detail: DatabaseProbeDetail = DatabaseProbeDetail.CONNECTOR_NOT_INITIALIZED,
) -> DatabaseProbeResult:
    return DatabaseProbeResult(connected=False, latency_ms=None, detail=detail)


def _auth_ok(latency_ms: float | None = 4.2) -> AuthProbeResult:
    return AuthProbeResult(
        reachable=True,
        latency_ms=latency_ms,
        detail=AuthProbeDetail.HEALTHY,
        provider="supabase",
    )


def _auth_skipped() -> AuthProbeResult:
    return AuthProbeResult(
        reachable=True,
        latency_ms=None,
        detail=AuthProbeDetail.SKIPPED_LOCAL,
        provider="local",
    )


def _auth_down() -> AuthProbeResult:
    return AuthProbeResult(
        reachable=False,
        latency_ms=None,
        detail=AuthProbeDetail.UNREACHABLE,
        provider="supabase",
    )


_XSS_PAYLOAD = '<script>alert("xss")</script>'
_SQL_PAYLOAD = "1; DROP TABLE users;--"


class TestHealthEndpoints:
    """Health probe contract tests."""

    def test_live_returns_alive(self, client: TestClient) -> None:
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.json() == {"alive": True}
        assert "application/json" in response.headers["content-type"]

    @patch("papita_txnsapi.routers.v1.health.probe_database", return_value=_connected_probe())
    @patch("papita_txnsapi.routers.v1.health.probe_supabase_auth", return_value=_auth_skipped())
    def test_ready_returns_200_when_db_up(self, _mock_auth: object, _mock_probe: object, client: TestClient) -> None:
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        assert response.json() == {"ready": True}

    @patch("papita_txnsapi.routers.v1.health.probe_database", return_value=_disconnected_probe())
    @patch("papita_txnsapi.routers.v1.health.probe_supabase_auth", return_value=_auth_skipped())
    def test_ready_returns_503_when_db_down(self, _mock_auth: object, _mock_probe: object, client: TestClient) -> None:
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        assert response.json() == {"ready": False}
        assert "application/json" in response.headers["content-type"]

    @patch("papita_txnsapi.routers.v1.health.probe_database", return_value=_connected_probe())
    @patch("papita_txnsapi.routers.v1.health.probe_supabase_auth", return_value=_auth_down())
    def test_ready_returns_503_when_auth_down(self, _mock_auth: object, _mock_db: object, client: TestClient) -> None:
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        assert response.json() == {"ready": False}

    @patch("papita_txnsapi.routers.v1.health.probe_database", return_value=_connected_probe(2.5))
    @patch("papita_txnsapi.routers.v1.health.probe_supabase_auth", return_value=_auth_skipped())
    def test_health_includes_version_and_database(
        self, _mock_auth: object, _mock_probe: object, client: TestClient
    ) -> None:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "healthy"
        assert payload["database"] == "connected"
        assert payload["database_latency_ms"] == 2.5
        assert payload["auth"] == "skipped"
        assert payload["auth_detail"] == AuthProbeDetail.SKIPPED_LOCAL
        assert "version" in payload
        assert "timestamp" in payload

    @patch("papita_txnsapi.routers.v1.health.probe_database", return_value=_disconnected_probe())
    @patch("papita_txnsapi.routers.v1.health.probe_supabase_auth", return_value=_auth_skipped())
    def test_health_degraded_when_db_down(self, _mock_auth: object, _mock_probe: object, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "degraded"
        assert payload["database"] == "disconnected"
        assert payload["database_latency_ms"] is None

    @patch("papita_txnsapi.routers.v1.health.probe_database", return_value=_connected_probe(1.0))
    @patch("papita_txnsapi.routers.v1.health.probe_supabase_auth", return_value=_auth_down())
    def test_health_degraded_when_auth_down(self, _mock_auth: object, _mock_db: object, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "degraded"
        assert payload["auth"] == "disconnected"
        assert payload["auth_detail"] == AuthProbeDetail.UNREACHABLE

    @patch("papita_txnsapi.routers.v1.health.probe_database", return_value=_connected_probe(3.1))
    def test_database_health_returns_latency_when_up(self, _mock_probe: object, client: TestClient) -> None:
        response = client.get("/api/v1/health/database")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "healthy"
        assert payload["connected"] is True
        assert payload["latency_ms"] == 3.1
        assert payload["detail"] == DatabaseProbeDetail.HEALTHY
        assert "checked_at" in payload

    @patch(
        "papita_txnsapi.routers.v1.health.probe_database",
        return_value=_disconnected_probe(DatabaseProbeDetail.PROBE_FAILED),
    )
    def test_database_health_returns_503_when_down(self, _mock_probe: object, client: TestClient) -> None:
        response = client.get("/api/v1/health/database")
        assert response.status_code == 503
        payload = response.json()
        assert payload["status"] == "unhealthy"
        assert payload["connected"] is False
        assert payload["latency_ms"] is None
        assert payload["detail"] == DatabaseProbeDetail.PROBE_FAILED
        assert "application/json" in response.headers["content-type"]

    @patch(
        "papita_txnsapi.routers.v1.health.probe_database",
        return_value=_disconnected_probe(DatabaseProbeDetail.PROBE_FAILED),
    )
    def test_database_health_ignores_injection_query_params(self, _mock_probe: object, client: TestClient) -> None:
        """Query/body injection attempts must not change allowlisted probe output."""
        response = client.get(
            "/api/v1/health/database",
            params={"q": _SQL_PAYLOAD, "detail": _XSS_PAYLOAD, "sql": _SQL_PAYLOAD},
        )
        assert response.status_code == 503
        payload = response.json()
        body = response.text
        assert payload["detail"] == DatabaseProbeDetail.PROBE_FAILED
        assert _XSS_PAYLOAD not in body
        assert _SQL_PAYLOAD not in body
        assert "<script>" not in body

    @patch("papita_txnsapi.routers.v1.health.probe_supabase_auth", return_value=_auth_ok(5.5))
    def test_auth_health_returns_latency_when_up(self, _mock_auth: object, client: TestClient) -> None:
        response = client.get("/api/v1/health/auth")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "healthy"
        assert payload["reachable"] is True
        assert payload["provider"] == "supabase"
        assert payload["latency_ms"] == 5.5
        assert payload["detail"] == AuthProbeDetail.HEALTHY

    @patch("papita_txnsapi.routers.v1.health.probe_supabase_auth", return_value=_auth_down())
    def test_auth_health_returns_503_when_down(self, _mock_auth: object, client: TestClient) -> None:
        response = client.get("/api/v1/health/auth")
        assert response.status_code == 503
        payload = response.json()
        assert payload["status"] == "unhealthy"
        assert payload["reachable"] is False
        assert payload["detail"] == AuthProbeDetail.UNREACHABLE
        assert _XSS_PAYLOAD not in response.text


class TestProbeDatabaseHardening:
    """Unit tests that probe failures never reflect exception/SQL/XSS payloads."""

    def test_probe_never_echoes_exception_message_with_xss(self) -> None:
        connector = MagicMock()
        connector.connected.return_value = True
        engine = MagicMock()
        connector.engine = engine

        xss_error = RuntimeError(f"db boom {_XSS_PAYLOAD} {_SQL_PAYLOAD}")
        session_cm = MagicMock()
        session_cm.__enter__.return_value.connection.return_value.execute.side_effect = xss_error
        session_cm.__exit__.return_value = False

        with patch("papita_txnsapi.core.db_health.Session", return_value=session_cm):
            result = probe_database(connector)

        assert result.connected is False
        assert result.detail is DatabaseProbeDetail.PROBE_FAILED
        assert result.detail == "probe failed"
        assert _XSS_PAYLOAD not in result.detail
        assert _SQL_PAYLOAD not in result.detail

    def test_probe_detail_values_are_allowlisted_only(self) -> None:
        allowed = {member.value for member in DatabaseProbeDetail}
        assert allowed == {
            "api-database link healthy",
            "connector not initialized",
            "database engine unavailable",
            "probe failed",
        }

    def test_database_health_schema_rejects_arbitrary_detail(self) -> None:
        from pydantic import ValidationError

        from papita_txnsapi.schemas.health import DatabaseHealthResponse

        with pytest.raises(ValidationError):
            DatabaseHealthResponse(
                status="unhealthy",
                connected=False,
                latency_ms=None,
                checked_at=datetime.now(timezone.utc),
                detail=_XSS_PAYLOAD,  # type: ignore[arg-type]
            )


class TestProbeSupabaseAuth:
    """Unit tests for the Supabase Auth health probe."""

    def test_local_provider_skips_network(self) -> None:
        client = MagicMock()
        result = probe_supabase_auth(
            auth_provider="local",
            supabase_url="https://example.supabase.co",
            anon_key="anon",
            client=client,
        )
        assert result.reachable is True
        assert result.detail is AuthProbeDetail.SKIPPED_LOCAL
        client.get.assert_not_called()

    def test_missing_config_is_not_configured(self) -> None:
        result = probe_supabase_auth(auth_provider="supabase", supabase_url=None, anon_key=None)
        assert result.reachable is False
        assert result.detail is AuthProbeDetail.NOT_CONFIGURED

    def test_http_200_is_healthy(self) -> None:
        client = MagicMock()
        client.get.return_value = httpx.Response(200, json={"version": "v2"})
        result = probe_supabase_auth(
            auth_provider="supabase",
            supabase_url="https://example.supabase.co",
            anon_key="anon",
            client=client,
        )
        assert result.reachable is True
        assert result.detail is AuthProbeDetail.HEALTHY
        assert result.latency_ms is not None
        called_url = client.get.call_args.args[0]
        assert called_url == "https://example.supabase.co/auth/v1/health"

    def test_http_error_is_unreachable_without_echo(self) -> None:
        client = MagicMock()
        client.get.side_effect = httpx.ConnectError(f"boom {_XSS_PAYLOAD}")
        result = probe_supabase_auth(
            auth_provider="supabase",
            supabase_url="https://example.supabase.co",
            anon_key="anon",
            client=client,
        )
        assert result.reachable is False
        assert result.detail is AuthProbeDetail.UNREACHABLE
        assert _XSS_PAYLOAD not in result.detail


class TestOpenAPI:
    """OpenAPI surface smoke tests."""

    def test_openapi_json_available(self, client: TestClient) -> None:
        response = client.get("/api/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Save Ma Money API"
        assert "/api/v1/health" in schema["paths"]
        assert "/api/v1/health/database" in schema["paths"]
        assert "/api/v1/health/auth" in schema["paths"]
        assert "/api/v1/auth/register" in schema["paths"]
        assert "/api/v1/auth/me" in schema["paths"]
