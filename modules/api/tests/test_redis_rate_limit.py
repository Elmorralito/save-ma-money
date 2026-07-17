"""Tests for Redis distributed rate limiting (PPT-043)."""

from __future__ import annotations

from papita_txnsapi.core.rate_limit import RedisRateLimiter
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
