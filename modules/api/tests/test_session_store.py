"""Tests for Redis session store denylist (PPT-043)."""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock

import pytest
from redis.exceptions import RedisError

from papita_txnsapi.core.redis_keys import redis_key
from papita_txnsapi.core.session_store import SessionStore, SessionStoreUnavailableError


class TestSessionStore:
    """JWT denylist SET with TTL and fail-closed policy."""

    def test_revoke_and_check(self, fake_redis: object) -> None:
        store = SessionStore(fake_redis, default_ttl_seconds=3600)
        token = "eyJhbGciOiJIUzI1NiJ9.example"
        assert store.is_revoked(token) is False
        assert store.revoke(token) is True
        assert store.is_revoked(token) is True
        digest = hashlib.sha256(token.encode()).hexdigest()
        assert fake_redis.exists(redis_key("jwt", "denylist", digest)) == 1

    def test_unavailable_without_client_fail_open(self) -> None:
        store = SessionStore(None, default_ttl_seconds=60, fail_closed=False)
        assert store.available is False
        assert store.revoke("token") is False
        assert store.is_revoked("token") is False

    def test_fail_closed_without_client(self) -> None:
        store = SessionStore(None, default_ttl_seconds=60, fail_closed=True)
        with pytest.raises(SessionStoreUnavailableError):
            store.is_revoked("token")

    def test_fail_closed_on_redis_error(self) -> None:
        client = MagicMock()
        client.exists.side_effect = RedisError("boom")
        store = SessionStore(client, default_ttl_seconds=60, fail_closed=True)
        with pytest.raises(SessionStoreUnavailableError):
            store.is_revoked("token")

    def test_fail_open_on_redis_error(self) -> None:
        client = MagicMock()
        client.exists.side_effect = RedisError("boom")
        store = SessionStore(client, default_ttl_seconds=60, fail_closed=False)
        assert store.is_revoked("token") is False
