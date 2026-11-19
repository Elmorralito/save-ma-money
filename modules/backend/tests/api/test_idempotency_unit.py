"""Unit tests for Redis idempotency helpers (Codecov patch gaps)."""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock

from redis.exceptions import RedisError

from papita_txnsapi.core.idempotency import (
    _result_from_stored,
    begin_idempotency,
    clear_idempotency_pending,
    complete_idempotency,
    request_body_digest,
)


class TestResultFromStored:
    """Edge cases for stored Redis payloads."""

    def test_none_is_conflict(self) -> None:
        assert _result_from_stored(None).state == "conflict"

    def test_invalid_json_is_conflict(self) -> None:
        assert _result_from_stored("not-json{").state == "conflict"

    def test_non_dict_is_conflict(self) -> None:
        assert _result_from_stored(json.dumps([1, 2])).state == "conflict"

    def test_pending_is_conflict(self) -> None:
        assert _result_from_stored(json.dumps({"status": "pending"})).state == "conflict"

    def test_completed_without_dict_body_is_conflict(self) -> None:
        assert _result_from_stored(json.dumps({"status": "completed", "body": "x"})).state == "conflict"

    def test_completed_with_body_is_hit(self) -> None:
        result = _result_from_stored(json.dumps({"status": "completed", "body": {"ok": True}}))
        assert result.state == "hit"
        assert result.payload == {"ok": True}

    def test_body_digest_mismatch_is_mismatch(self) -> None:
        stored = json.dumps(
            {"status": "completed", "body": {"ok": True}, "body_digest": "aaa"},
        )
        result = _result_from_stored(stored, body_digest="bbb")
        assert result.state == "mismatch"
        assert result.payload is None

    def test_legacy_completed_without_digest_still_hits(self) -> None:
        stored = json.dumps({"status": "completed", "body": {"ok": True}})
        result = _result_from_stored(stored, body_digest="bbb")
        assert result.state == "hit"


class TestRequestBodyDigest:
    """Canonical request body hashing."""

    def test_stable_for_key_order(self) -> None:
        assert request_body_digest({"b": 1, "a": 2}) == request_body_digest({"a": 2, "b": 1})

    def test_differs_for_payload_change(self) -> None:
        assert request_body_digest({"amount": 1}) != request_body_digest({"amount": 2})


class TestBeginIdempotency:
    """Claim / race / fail-open paths."""

    def test_bypass_when_client_or_key_missing(self) -> None:
        owner_id = uuid.uuid4()
        assert begin_idempotency(None, owner_id, scope="s", key="k", ttl_seconds=60).state == "bypass"
        assert begin_idempotency(MagicMock(), owner_id, scope="s", key=None, ttl_seconds=60).state == "bypass"
        assert begin_idempotency(MagicMock(), owner_id, scope="s", key="  ", ttl_seconds=60).state == "bypass"
        assert begin_idempotency(MagicMock(), owner_id, scope="s", key="k", ttl_seconds=0).state == "bypass"

    def test_race_lost_then_hit(self, fake_redis: object) -> None:
        owner_id = uuid.uuid4()
        client = MagicMock()
        completed = json.dumps({"status": "completed", "body": {"id": "1"}})
        client.get.side_effect = [None, completed]
        client.set.return_value = False
        result = begin_idempotency(client, owner_id, scope="s", key="race", ttl_seconds=60)
        assert result.state == "hit"
        assert result.payload == {"id": "1"}

    def test_race_lost_then_key_vanished_is_miss(self) -> None:
        owner_id = uuid.uuid4()
        client = MagicMock()
        client.get.side_effect = [None, None]
        client.set.return_value = False
        assert begin_idempotency(client, owner_id, scope="s", key="race2", ttl_seconds=60).state == "miss"

    def test_redis_error_bypasses(self) -> None:
        owner_id = uuid.uuid4()
        client = MagicMock()
        client.get.side_effect = RedisError("boom")
        assert begin_idempotency(client, owner_id, scope="s", key="err", ttl_seconds=60).state == "bypass"


class TestCompleteAndClear:
    """complete_idempotency / clear_idempotency_pending edges."""

    def test_complete_noop_guards(self) -> None:
        owner_id = uuid.uuid4()
        complete_idempotency(None, owner_id, scope="s", key="k", body={}, ttl_seconds=60)
        complete_idempotency(MagicMock(), owner_id, scope="s", key=None, body={}, ttl_seconds=60)
        complete_idempotency(MagicMock(), owner_id, scope="s", key="k", body={}, ttl_seconds=0)

    def test_complete_swallows_redis_error(self) -> None:
        owner_id = uuid.uuid4()
        client = MagicMock()
        client.setex.side_effect = RedisError("boom")
        complete_idempotency(client, owner_id, scope="s", key="k", body={"a": 1}, ttl_seconds=60)

    def test_clear_pending_deletes_lock(self, fake_redis: object) -> None:
        owner_id = uuid.uuid4()
        begun = begin_idempotency(fake_redis, owner_id, scope="s", key="clear-me", ttl_seconds=60)
        assert begun.state == "miss"
        clear_idempotency_pending(fake_redis, owner_id, scope="s", key="clear-me")
        again = begin_idempotency(fake_redis, owner_id, scope="s", key="clear-me", ttl_seconds=60)
        assert again.state == "miss"

    def test_clear_noop_when_missing_or_completed(self, fake_redis: object) -> None:
        owner_id = uuid.uuid4()
        clear_idempotency_pending(None, owner_id, scope="s", key="k")
        clear_idempotency_pending(fake_redis, owner_id, scope="s", key=None)
        clear_idempotency_pending(fake_redis, owner_id, scope="s", key="absent")
        begin_idempotency(fake_redis, owner_id, scope="s", key="done", ttl_seconds=60)
        complete_idempotency(
            fake_redis, owner_id, scope="s", key="done", body={"ok": True}, ttl_seconds=60
        )
        clear_idempotency_pending(fake_redis, owner_id, scope="s", key="done")
        replay = begin_idempotency(fake_redis, owner_id, scope="s", key="done", ttl_seconds=60)
        assert replay.state == "hit"

    def test_clear_swallows_errors(self) -> None:
        owner_id = uuid.uuid4()
        client = MagicMock()
        client.get.side_effect = RedisError("boom")
        clear_idempotency_pending(client, owner_id, scope="s", key="k")

    def test_same_key_different_body_is_mismatch(self, fake_redis: object) -> None:
        owner_id = uuid.uuid4()
        digest_a = request_body_digest({"amount": 10})
        digest_b = request_body_digest({"amount": 20})
        begun = begin_idempotency(
            fake_redis,
            owner_id,
            scope="s",
            key="same-key",
            ttl_seconds=60,
            body_digest=digest_a,
        )
        assert begun.state == "miss"
        complete_idempotency(
            fake_redis,
            owner_id,
            scope="s",
            key="same-key",
            body={"id": "1"},
            ttl_seconds=60,
            body_digest=digest_a,
        )
        replay = begin_idempotency(
            fake_redis,
            owner_id,
            scope="s",
            key="same-key",
            ttl_seconds=60,
            body_digest=digest_b,
        )
        assert replay.state == "mismatch"
