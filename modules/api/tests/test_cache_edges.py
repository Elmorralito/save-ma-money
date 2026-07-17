"""Edge / fail-open paths for Redis cache helpers (Codecov patch gaps)."""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock

from redis.exceptions import RedisError

from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.core.cache import (
    CacheNamespace,
    bump_cache_versions,
    cache_get_json,
    cache_set_json,
    get_cache_version,
    get_versioned_cached_json,
    set_versioned_cached_json,
    ttl_for_namespace,
)


class TestCacheFailOpen:
    """RedisError and invalid payload paths."""

    def test_get_version_none_client(self) -> None:
        assert get_cache_version(None, uuid.uuid4(), CacheNamespace.ACCOUNTS) == 0

    def test_get_version_redis_error(self) -> None:
        client = MagicMock()
        client.get.side_effect = RedisError("boom")
        assert get_cache_version(client, uuid.uuid4(), CacheNamespace.ACCOUNTS) == 0

    def test_get_version_invalid_int(self, fake_redis: object) -> None:
        owner_id = uuid.uuid4()
        from papita_txnsapi.core.cache import version_key

        fake_redis.set(version_key(owner_id, CacheNamespace.ACCOUNTS), "not-int")
        assert get_cache_version(fake_redis, owner_id, CacheNamespace.ACCOUNTS) == 0

    def test_bump_noop_and_error(self) -> None:
        bump_cache_versions(None, uuid.uuid4(), CacheNamespace.ACCOUNTS)
        bump_cache_versions(MagicMock(), None, CacheNamespace.ACCOUNTS)
        bump_cache_versions(MagicMock(), uuid.uuid4())
        client = MagicMock()
        client.pipeline.side_effect = RedisError("boom")
        bump_cache_versions(client, uuid.uuid4(), CacheNamespace.ACCOUNTS)

    def test_cache_get_edges(self, fake_redis: object) -> None:
        assert cache_get_json(None, "k") is None
        client = MagicMock()
        client.get.side_effect = RedisError("boom")
        assert cache_get_json(client, "k") is None
        fake_redis.set("bad-json", "{")
        assert cache_get_json(fake_redis, "bad-json") is None
        fake_redis.set("list-json", json.dumps([1]))
        assert cache_get_json(fake_redis, "list-json") is None

    def test_cache_set_edges(self) -> None:
        assert cache_set_json(None, "k", {"a": 1}, ttl_seconds=60) is False
        assert cache_set_json(MagicMock(), "k", {"a": 1}, ttl_seconds=0) is False
        client = MagicMock()
        client.setex.side_effect = RedisError("boom")
        assert cache_set_json(client, "k", {"a": 1}, ttl_seconds=60) is False

    def test_versioned_bypass_and_set_none(self) -> None:
        owner_id = uuid.uuid4()
        payload, status = get_versioned_cached_json(None, owner_id, CacheNamespace.ACCOUNTS, "r")
        assert payload is None and status == "BYPASS"
        assert (
            set_versioned_cached_json(
                None,
                owner_id,
                CacheNamespace.ACCOUNTS,
                "r",
                {},
                value={"x": 1},
                ttl_seconds=60,
            )
            is False
        )

    def test_ttl_defaults_without_settings(self) -> None:
        assert ttl_for_namespace(None, "transactions") == 15
        assert ttl_for_namespace(None, CacheNamespace.REPORTS) == 180
        settings = get_settings()
        assert ttl_for_namespace(settings, "accounts") == settings.REDIS_CACHE_TTL_ACCOUNTS_SECONDS
