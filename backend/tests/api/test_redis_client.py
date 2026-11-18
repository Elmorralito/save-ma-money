"""Unit tests for Redis client lifecycle and probes (Codecov patch gaps)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from redis.exceptions import RedisError

from papita_txnsapi.core.redis import (
    RedisProbeDetail,
    _safe_latency_ms,
    close_redis,
    get_redis_from_app,
    init_redis,
    ping_redis,
)


class TestSafeLatency:
    """Finite latency clamping."""

    def test_normal_and_clamped(self) -> None:
        assert _safe_latency_ms(0.001) == 1.0
        assert _safe_latency_ms(-1.0) == 0.0
        assert _safe_latency_ms(float("nan")) == 0.0
        assert _safe_latency_ms(100.0) == 60_000.0  # capped at _MAX_LATENCY_MS


class TestInitAndClose:
    """init_redis / close_redis branches."""

    def test_disabled_returns_none(self) -> None:
        settings = MagicMock(REDIS_ENABLED=False)
        assert init_redis(settings) is None

    def test_enabled_without_url_raises(self) -> None:
        settings = MagicMock(REDIS_ENABLED=True, REDIS_URL="")
        with pytest.raises(ValueError, match="REDIS_URL"):
            init_redis(settings)

    def test_enabled_pings_and_returns_client(self) -> None:
        settings = MagicMock(REDIS_ENABLED=True, REDIS_URL="redis://localhost:6379/0", REDIS_MAX_CONNECTIONS=5)
        fake_client = MagicMock()
        with (
            patch("papita_txnsapi.core.redis.ConnectionPool.from_url") as from_url,
            patch("papita_txnsapi.core.redis.Redis", return_value=fake_client) as redis_cls,
        ):
            from_url.return_value = MagicMock()
            client = init_redis(settings)
        assert client is fake_client
        fake_client.ping.assert_called_once()
        redis_cls.assert_called_once()

    def test_close_none_is_noop(self) -> None:
        close_redis(None)

    def test_close_disconnects_pool(self) -> None:
        pool = MagicMock()
        client = MagicMock()
        client.connection_pool = pool
        close_redis(client)
        client.close.assert_called_once()
        pool.disconnect.assert_called_once()

    def test_close_swallows_errors(self) -> None:
        client = MagicMock()
        client.close.side_effect = RuntimeError("close failed")
        close_redis(client)


class TestPingRedis:
    """ping_redis detail paths."""

    def test_disabled_when_optional_and_no_client(self) -> None:
        result = ping_redis(None, required=False)
        assert result.connected is True
        assert result.detail is RedisProbeDetail.DISABLED

    def test_client_unavailable_when_required(self) -> None:
        result = ping_redis(None, required=True)
        assert result.connected is False
        assert result.detail is RedisProbeDetail.CLIENT_UNAVAILABLE
        assert result.required is True

    def test_healthy_ping(self) -> None:
        client = MagicMock()
        with patch("papita_txnsapi.core.redis.time.perf_counter", side_effect=[1.0, 1.002]):
            result = ping_redis(client, required=True)
        assert result.connected is True
        assert result.detail is RedisProbeDetail.HEALTHY
        assert result.latency_ms == 2.0

    def test_probe_failed_on_redis_error(self) -> None:
        client = MagicMock()
        client.ping.side_effect = RedisError("down")
        result = ping_redis(client, required=True)
        assert result.connected is False
        assert result.detail is RedisProbeDetail.PROBE_FAILED


class TestGetRedisFromApp:
    """App state helper."""

    def test_reads_app_state(self) -> None:
        app = MagicMock()
        app.state.redis = "client"
        assert get_redis_from_app(app) == "client"
