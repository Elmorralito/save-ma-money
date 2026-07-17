"""Tests for Redis distributed rate limiting (PPT-043)."""

from __future__ import annotations

from unittest.mock import MagicMock

from redis.exceptions import RedisError

from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.core.rate_limit import (
    InMemoryRateLimiter,
    RedisRateLimiter,
    get_rate_limiter_for_request,
)
from papita_txnsapi.core.redis_keys import redis_key


class TestRedisRateLimiter:
    """Atomic Lua sliding-window limiter shared via FakeRedis."""

    def test_shared_counter_across_limiter_instances(self, fake_redis: object) -> None:
        limiter_a = RedisRateLimiter(fake_redis)
        limiter_b = RedisRateLimiter(fake_redis)
        key = "auth-login:127.0.0.1"

        first = limiter_a.check(key, limit=2, window_seconds=60)
        second = limiter_b.check(key, limit=2, window_seconds=60)
        blocked = limiter_a.check(key, limit=2, window_seconds=60)

        assert first.allowed is True
        assert second.allowed is True
        assert blocked.allowed is False
        assert blocked.remaining == 0
        assert blocked.limit == 2
        assert fake_redis.exists(redis_key("ratelimit", key)) == 1

    def test_non_positive_limit_always_allows(self, fake_redis: object) -> None:
        limiter = RedisRateLimiter(fake_redis)
        result = limiter.check("auth-login:1.1.1.1", limit=0, window_seconds=60)
        assert result.allowed is True

    def test_fail_open_on_redis_error(self) -> None:
        client = MagicMock()
        client.register_script.return_value = MagicMock(side_effect=RedisError("connection lost"))
        limiter = RedisRateLimiter(client)
        result = limiter.check("api:owner:min", limit=10, window_seconds=60)
        assert result.allowed is True
        assert result.remaining == 10

    def test_evalsha_noscript_falls_back_to_eval(self) -> None:
        client = MagicMock()
        script = MagicMock(side_effect=RedisError("NOSCRIPT No matching script"))
        client.register_script.return_value = script
        client.eval.return_value = [1, 1, 1.0]
        limiter = RedisRateLimiter(client)
        result = limiter.check("api:owner:min", limit=5, window_seconds=60)
        assert result.allowed is True
        client.eval.assert_called_once()

    def test_inmemory_non_positive_limit(self) -> None:
        result = InMemoryRateLimiter().check("k", limit=0, window_seconds=60)
        assert result.allowed is True

    def test_get_rate_limiter_for_request_uses_redis(self, fake_redis: object, monkeypatch) -> None:
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("REDIS_RATE_LIMIT_ENABLED", "true")
        get_settings.cache_clear()
        settings = get_settings()
        request = MagicMock()
        request.app.state.redis = fake_redis
        limiter = get_rate_limiter_for_request(request, settings)
        assert isinstance(limiter, RedisRateLimiter)
        get_settings.cache_clear()
        monkeypatch.setenv("REDIS_ENABLED", "false")
        monkeypatch.setenv("REDIS_RATE_LIMIT_ENABLED", "false")

    def test_get_rate_limiter_falls_back_when_client_not_redis(self, monkeypatch) -> None:
        monkeypatch.setenv("REDIS_ENABLED", "true")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("REDIS_RATE_LIMIT_ENABLED", "true")
        get_settings.cache_clear()
        settings = get_settings()
        request = MagicMock()
        request.app.state.redis = object()  # not a Redis instance
        limiter = get_rate_limiter_for_request(request, settings)
        assert isinstance(limiter, InMemoryRateLimiter)
        get_settings.cache_clear()
        monkeypatch.setenv("REDIS_ENABLED", "false")
        monkeypatch.setenv("REDIS_RATE_LIMIT_ENABLED", "false")
