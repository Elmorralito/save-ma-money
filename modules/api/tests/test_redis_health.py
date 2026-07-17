"""Tests for Redis health probes (PPT-043)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from papita_txnsapi.core.auth_health import AuthProbeDetail, AuthProbeResult
from papita_txnsapi.core.db_health import DatabaseProbeDetail, DatabaseProbeResult
from papita_txnsapi.core.redis import RedisProbeDetail, RedisProbeResult
from papita_txnsapi.main import create_app


def _connected_db() -> DatabaseProbeResult:
    return DatabaseProbeResult(connected=True, latency_ms=1.0, detail=DatabaseProbeDetail.HEALTHY)


def _auth_skipped() -> AuthProbeResult:
    return AuthProbeResult(
        reachable=True,
        latency_ms=None,
        detail=AuthProbeDetail.SKIPPED_LOCAL,
        provider="local",
    )


class TestRedisHealth:
    """Redis component of health / ready probes."""

    def test_redis_health_skipped_when_disabled(self, client: TestClient) -> None:
        response = client.get("/api/v1/health/redis")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "healthy"
        assert payload["reachable"] is True
        assert payload["required"] is False
        assert payload["detail"] == RedisProbeDetail.DISABLED

    @patch("papita_txnsapi.routers.v1.health.probe_database", return_value=_connected_db())
    @patch("papita_txnsapi.routers.v1.health.probe_supabase_auth", return_value=_auth_skipped())
    @patch(
        "papita_txnsapi.routers.v1.health.ping_redis",
        return_value=RedisProbeResult(
            connected=False,
            latency_ms=None,
            detail=RedisProbeDetail.PROBE_FAILED,
            required=True,
        ),
    )
    def test_ready_503_when_redis_required_and_down(
        self,
        _mock_redis: object,
        _mock_auth: object,
        _mock_db: object,
        monkeypatch: object,
    ) -> None:
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        from papita_txnsapi.config.settings import get_settings

        get_settings.cache_clear()
        with patch("papita_txnsapi.main.init_redis", return_value=MagicMock()):
            with TestClient(create_app()) as client:
                response = client.get("/api/v1/health/ready")
        get_settings.cache_clear()
        monkeypatch.setenv("REDIS_ENABLED", "false")
        assert response.status_code == 503
        assert response.json() == {"ready": False}

    @patch(
        "papita_txnsapi.routers.v1.health.ping_redis",
        return_value=RedisProbeResult(
            connected=True,
            latency_ms=0.5,
            detail=RedisProbeDetail.HEALTHY,
            required=True,
        ),
    )
    def test_redis_health_connected_when_enabled(
        self,
        _mock_redis: object,
        monkeypatch: object,
    ) -> None:
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        from papita_txnsapi.config.settings import get_settings

        get_settings.cache_clear()
        with patch("papita_txnsapi.main.init_redis", return_value=MagicMock()):
            with TestClient(create_app()) as client:
                response = client.get("/api/v1/health/redis")
        get_settings.cache_clear()
        monkeypatch.setenv("REDIS_ENABLED", "false")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "healthy"
        assert payload["latency_ms"] == 0.5
        assert payload["detail"] == RedisProbeDetail.HEALTHY
        assert "checked_at" in payload
        datetime.fromisoformat(payload["checked_at"].replace("Z", "+00:00"))

    @patch("papita_txnsapi.routers.v1.health.probe_database", return_value=_connected_db())
    @patch("papita_txnsapi.routers.v1.health.probe_supabase_auth", return_value=_auth_skipped())
    @patch(
        "papita_txnsapi.routers.v1.health.ping_redis",
        return_value=RedisProbeResult(
            connected=False,
            latency_ms=None,
            detail=RedisProbeDetail.PROBE_FAILED,
            required=True,
        ),
    )
    def test_composite_health_degraded_when_redis_down(
        self,
        _mock_redis: object,
        _mock_auth: object,
        _mock_db: object,
        monkeypatch: object,
    ) -> None:
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        from papita_txnsapi.config.settings import get_settings

        get_settings.cache_clear()
        with patch("papita_txnsapi.main.init_redis", return_value=MagicMock()):
            with TestClient(create_app()) as client:
                response = client.get("/api/v1/health")
        get_settings.cache_clear()
        monkeypatch.setenv("REDIS_ENABLED", "false")
        assert response.status_code == 200
        assert response.json()["status"] == "degraded"
        assert response.json()["redis"] == "disconnected"
