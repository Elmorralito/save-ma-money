"""Tests for Redis key namespacing (PPT-043 hardening)."""

from __future__ import annotations

import pytest

from papita_txnsapi.config.settings import get_settings
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
