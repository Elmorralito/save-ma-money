"""Tests for health endpoints."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Health probe contract tests."""

    def test_live_returns_alive(self, client: TestClient) -> None:
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.json() == {"alive": True}

    @patch("papita_txnsapi.routers.v1.health.check_database_ready", return_value=True)
    def test_ready_returns_200_when_db_up(self, _mock_ready: object, client: TestClient) -> None:
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        assert response.json() == {"ready": True}

    @patch("papita_txnsapi.routers.v1.health.check_database_ready", return_value=False)
    def test_ready_returns_503_when_db_down(self, _mock_ready: object, client: TestClient) -> None:
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        assert response.json() == {"ready": False}

    @patch("papita_txnsapi.routers.v1.health.check_database_ready", return_value=True)
    def test_health_includes_version_and_database(self, _mock_ready: object, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "healthy"
        assert payload["database"] == "connected"
        assert "version" in payload
        assert "timestamp" in payload


class TestOpenAPI:
    """OpenAPI surface smoke tests."""

    def test_openapi_json_available(self, client: TestClient) -> None:
        response = client.get("/api/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Save Ma Money API"
        assert "/api/v1/health" in schema["paths"]
        assert "/api/v1/auth/register" in schema["paths"]
        assert "/api/v1/auth/me" in schema["paths"]
