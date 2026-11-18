"""Unit tests for BFF session store serialization and Redis fail policies (PPT-049 / PPT-059)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from redis.exceptions import RedisError

from papita_txnsapi.core.bff_session import (
    BffSessionRecord,
    BffSessionStore,
    BffSessionStoreUnavailableError,
    clear_memory_bff_sessions,
    parse_owner_id_hint,
)


@pytest.fixture(autouse=True)
def _clear_memory() -> None:
    clear_memory_bff_sessions()
    yield
    clear_memory_bff_sessions()


class TestBffSessionRecord:
    """JSON round-trip and expiry helpers."""

    def test_round_trip(self) -> None:
        record = BffSessionRecord(
            access_token="a",
            refresh_token="r",
            csrf_token="c",
            access_expires_at=1.5,
            owner_id="o",
        )
        parsed = BffSessionRecord.from_json(record.to_json())
        assert parsed.access_token == "a"
        assert parsed.refresh_token == "r"
        assert parsed.csrf_token == "c"
        assert parsed.access_expires_at == 1.5
        assert parsed.owner_id == "o"

    def test_from_json_rejects_malformed(self) -> None:
        with pytest.raises(ValueError, match="invalid BFF session"):
            BffSessionRecord.from_json("{not-json")
        with pytest.raises(ValueError, match="invalid BFF session"):
            BffSessionRecord.from_json('{"access_token":"a"}')

    def test_access_expired_respects_skew(self) -> None:
        record = BffSessionRecord(
            access_token="a",
            refresh_token=None,
            csrf_token="c",
            access_expires_at=0.0,
        )
        assert record.access_expired() is True


class TestBffSessionStoreMemory:
    """Process-local map behavior (fail_closed=false)."""

    def test_create_get_update_delete(self) -> None:
        store = BffSessionStore(None, default_ttl_seconds=120)
        assert store.backend == "memory"
        assert store.fail_closed is False
        sid, record = store.create(
            access_token="access",
            refresh_token=None,
            expires_in=60,
            owner_id="owner-1",
        )
        assert store.get(sid) is not None
        assert store.get("") is None
        updated = BffSessionRecord(
            access_token="rotated",
            refresh_token=record.refresh_token,
            csrf_token=record.csrf_token,
            access_expires_at=record.access_expires_at,
            owner_id=record.owner_id,
        )
        store.update(sid, updated)
        assert store.get(sid).access_token == "rotated"
        store.update("", updated)
        store.delete(sid)
        assert store.get(sid) is None
        store.delete("")

    def test_corrupt_payload_is_dropped(self) -> None:
        store = BffSessionStore(None, default_ttl_seconds=120)
        sid, _ = store.create(access_token="a", refresh_token=None, expires_in=30)
        # Poison the memory map with invalid JSON under the same key.
        from papita_txnsapi.core import bff_session as mod

        with mod._memory_lock:
            mod._memory_sessions[sid] = "{bad"
        assert store.get(sid) is None

    def test_fail_closed_without_client_raises(self) -> None:
        store = BffSessionStore(None, default_ttl_seconds=120, fail_closed=True)
        with pytest.raises(BffSessionStoreUnavailableError, match="unavailable"):
            store.create(access_token="a", refresh_token=None, expires_in=30)
        with pytest.raises(BffSessionStoreUnavailableError, match="unavailable"):
            store.get("any-session-id")
        with pytest.raises(BffSessionStoreUnavailableError, match="unavailable"):
            store.delete("any-session-id")
        with pytest.raises(BffSessionStoreUnavailableError, match="unavailable"):
            store.update(
                "any-session-id",
                BffSessionRecord(
                    access_token="a",
                    refresh_token=None,
                    csrf_token="c",
                    access_expires_at=9_999_999_999.0,
                ),
            )


class TestBffSessionStoreRedis:
    """Redis client success and fail-open / fail-closed RedisError paths."""

    def test_redis_set_get_delete(self) -> None:
        client = MagicMock()
        client.get.return_value = None
        store = BffSessionStore(client, default_ttl_seconds=120, fail_closed=True)
        assert store.backend == "redis"
        assert store.fail_closed is True
        sid, record = store.create(access_token="a", refresh_token="r", expires_in=30)
        client.setex.assert_called()
        client.get.return_value = record.to_json().encode("utf-8")
        assert store.get(sid) is not None
        store.delete(sid)
        client.delete.assert_called()

    def test_redis_errors_fall_back_to_memory_when_open(self) -> None:
        client = MagicMock()
        client.setex.side_effect = RedisError("down")
        client.get.side_effect = RedisError("down")
        client.delete.side_effect = RedisError("down")
        store = BffSessionStore(client, default_ttl_seconds=120, fail_closed=False)
        sid, _ = store.create(access_token="a", refresh_token=None, expires_in=30)
        # setex failed → memory fallback; get Redis fails → memory hit.
        assert store.get(sid) is not None
        store.delete(sid)

    def test_redis_errors_fail_closed(self) -> None:
        client = MagicMock()
        client.setex.side_effect = RedisError("down")
        client.get.side_effect = RedisError("down")
        client.delete.side_effect = RedisError("down")
        store = BffSessionStore(client, default_ttl_seconds=120, fail_closed=True)
        with pytest.raises(BffSessionStoreUnavailableError, match="write failed"):
            store.create(access_token="a", refresh_token=None, expires_in=30)
        with pytest.raises(BffSessionStoreUnavailableError, match="read failed"):
            store.get("any-session-id")
        with pytest.raises(BffSessionStoreUnavailableError, match="delete failed"):
            store.delete("any-session-id")

    def test_redis_miss_checks_memory_when_open(self) -> None:
        client = MagicMock()
        client.get.return_value = None
        store = BffSessionStore(client, default_ttl_seconds=120, fail_closed=False)
        from papita_txnsapi.core import bff_session as mod

        record = BffSessionRecord(
            access_token="mem",
            refresh_token=None,
            csrf_token="c",
            access_expires_at=9_999_999_999.0,
        )
        with mod._memory_lock:
            mod._memory_sessions["sid-mem"] = record.to_json()
        assert store.get("sid-mem") is not None

    def test_redis_miss_does_not_use_memory_when_fail_closed(self) -> None:
        client = MagicMock()
        client.get.return_value = None
        store = BffSessionStore(client, default_ttl_seconds=120, fail_closed=True)
        from papita_txnsapi.core import bff_session as mod

        record = BffSessionRecord(
            access_token="mem",
            refresh_token=None,
            csrf_token="c",
            access_expires_at=9_999_999_999.0,
        )
        with mod._memory_lock:
            mod._memory_sessions["sid-mem"] = record.to_json()
        assert store.get("sid-mem") is None


def test_parse_owner_id_hint() -> None:
    assert parse_owner_id_hint(None) is None
    assert parse_owner_id_hint("abc") == "abc"
