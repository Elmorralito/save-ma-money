"""Tests for Redis key namespacing (PPT-043 hardening)."""

from __future__ import annotations

import pytest

from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.core.broker import BrokerSettings, RedisBroker
from papita_txnsapi.core.cache import CacheNamespace, ttl_for_namespace
from papita_txnsapi.core.redis_keys import redis_key, redis_key_prefix


class TestRedisKeys:
    """``papita:{env}:…`` prefix helpers."""

    def test_prefix_follows_papita_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PAPITA_ENV", "staging")
        assert redis_key_prefix() == "papita:staging:"
        assert redis_key("ratelimit", "auth-login:1.1.1.1").startswith("papita:staging:")

    def test_explicit_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PAPITA_ENV", "local")
        assert redis_key("a", "b", env="production") == "papita:production:a:b"

    def test_local_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PAPITA_ENV", raising=False)
        assert redis_key_prefix() == "papita:local:"


class TestPerRouteTtls:
    """Per-namespace cache TTLs (not a single global default)."""

    def test_namespace_defaults(self) -> None:
        settings = get_settings()
        assert ttl_for_namespace(settings, CacheNamespace.ACCOUNTS) == 60
        assert ttl_for_namespace(settings, CacheNamespace.CATEGORIES) == 300
        assert 120 <= ttl_for_namespace(settings, CacheNamespace.REPORTS) <= 300
        assert ttl_for_namespace(settings, CacheNamespace.TRANSACTIONS) == 15


class TestBrokerKeyPrefix:
    """Broker scaffold uses env-prefixed keys."""

    def test_enqueue_uses_papita_env_prefix(self, fake_redis: object, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PAPITA_ENV", "local")
        broker = RedisBroker(fake_redis, BrokerSettings(enabled=True))
        assert broker.enqueue("job-1") is True
        assert fake_redis.llen(redis_key("jobs")) == 1

    def test_publish_prefixes_channel(self, fake_redis: object, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PAPITA_ENV", "local")
        broker = RedisBroker(fake_redis, BrokerSettings(enabled=True))
        assert broker.publish("invalidate", "accounts") is True
        assert broker.publish("papita:local:channel:custom", "msg") is True

    def test_disabled_and_redis_errors(self) -> None:
        from unittest.mock import MagicMock

        from redis.exceptions import RedisError

        assert RedisBroker(None, BrokerSettings(enabled=True)).enqueue("x") is False
        assert RedisBroker(MagicMock(), BrokerSettings(enabled=False)).publish("c", "m") is False
        client = MagicMock()
        client.lpush.side_effect = RedisError("boom")
        client.publish.side_effect = RedisError("boom")
        broker = RedisBroker(client, BrokerSettings(enabled=True))
        assert broker.enqueue("x") is False
        assert broker.publish("c", "m") is False
