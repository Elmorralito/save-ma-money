"""Redis idempotency helpers for mutating API routes (PPT-043).

Stores completed response payloads keyed by tenant + client ``Idempotency-Key``
so retries replay the same result without double-creating ledger rows.

Key exports:
    IdempotencyResult: Outcome of begin/complete helpers.
    begin_idempotency: Claim or replay a key.
    complete_idempotency: Persist the successful response body.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Literal, Mapping
from uuid import UUID

from redis import Redis
from redis.exceptions import RedisError

from papita_txnsapi.core.redis_keys import redis_key

logger = logging.getLogger(__name__)

_PENDING = {"status": "pending"}


@dataclass(frozen=True, slots=True)
class IdempotencyResult:
    """Outcome of an idempotency begin check.

    Attributes:
        state: ``bypass`` (no Redis/key), ``miss`` (claimed), ``hit`` (replay),
            or ``conflict`` (another request still pending).
        payload: Cached completed response body when ``state`` is ``hit``.
    """

    state: Literal["bypass", "miss", "hit", "conflict"]
    payload: dict[str, Any] | None = None


def _idempotency_redis_key(owner_id: UUID | str, scope: str, key: str) -> str:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return redis_key(owner_id, "idem", scope, digest)


def _result_from_stored(raw: str | bytes | None) -> IdempotencyResult:
    """Map a stored Redis value to hit/conflict (never miss)."""
    if raw is None:
        return IdempotencyResult(state="conflict")
    try:
        loaded = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return IdempotencyResult(state="conflict")
    if not isinstance(loaded, dict):
        return IdempotencyResult(state="conflict")
    if loaded.get("status") == "pending":
        return IdempotencyResult(state="conflict")
    body = loaded.get("body")
    if isinstance(body, dict):
        return IdempotencyResult(state="hit", payload=body)
    return IdempotencyResult(state="conflict")


def begin_idempotency(
    client: Redis | None,
    owner_id: UUID | str,
    *,
    scope: str,
    key: str | None,
    ttl_seconds: int,
) -> IdempotencyResult:
    """Claim an idempotency key or return a prior completed payload.

    Args:
        client: Redis client, or ``None`` to bypass.
        owner_id: Tenant primary key.
        scope: Logical operation scope (e.g. ``transactions:create``).
        key: Client-supplied ``Idempotency-Key``; blank/None bypasses.
        ttl_seconds: Expiration for lock and completed records.

    Returns:
        :class:`IdempotencyResult` describing whether to proceed, replay, or conflict.
    """
    if client is None or key is None or not str(key).strip() or ttl_seconds <= 0:
        return IdempotencyResult(state="bypass")

    storage_key = _idempotency_redis_key(owner_id, scope, str(key).strip())
    try:
        existing = client.get(storage_key)
        if existing is not None:
            return _result_from_stored(existing)

        acquired = client.set(storage_key, json.dumps(_PENDING, separators=(",", ":")), nx=True, ex=ttl_seconds)
        if acquired:
            return IdempotencyResult(state="miss")

        # Lost the race — re-read; treat vanished key as a fresh miss.
        raced = client.get(storage_key)
        if raced is None:
            return IdempotencyResult(state="miss")
        return _result_from_stored(raced)
    except RedisError:
        logger.exception("Idempotency begin failed; proceeding without lock")
        return IdempotencyResult(state="bypass")


def complete_idempotency(
    client: Redis | None,
    owner_id: UUID | str,
    *,
    scope: str,
    key: str | None,
    body: Mapping[str, Any],
    ttl_seconds: int,
    http_status: int = 201,
) -> None:
    """Persist a completed response for later idempotent replays.

    Args:
        client: Redis client, or ``None`` to no-op.
        owner_id: Tenant primary key.
        scope: Logical operation scope matching :func:`begin_idempotency`.
        key: Client-supplied ``Idempotency-Key``.
        body: JSON-serializable response body.
        ttl_seconds: Expiration for the completed record.
        http_status: HTTP status stored alongside the body (informational).
    """
    if client is None or key is None or not str(key).strip() or ttl_seconds <= 0:
        return
    storage_key = _idempotency_redis_key(owner_id, scope, str(key).strip())
    try:
        payload = {"status": "completed", "http_status": http_status, "body": dict(body)}
        client.setex(storage_key, ttl_seconds, json.dumps(payload, default=str, separators=(",", ":")))
    except (TypeError, RedisError):
        logger.exception("Idempotency complete failed")


def clear_idempotency_pending(
    client: Redis | None,
    owner_id: UUID | str,
    *,
    scope: str,
    key: str | None,
) -> None:
    """Drop a pending lock after a failed create so the client may retry.

    Args:
        client: Redis client, or ``None`` to no-op.
        owner_id: Tenant primary key.
        scope: Logical operation scope.
        key: Client-supplied ``Idempotency-Key``.
    """
    if client is None or key is None or not str(key).strip():
        return
    storage_key = _idempotency_redis_key(owner_id, scope, str(key).strip())
    try:
        raw = client.get(storage_key)
        if raw is None:
            return
        loaded = json.loads(raw)
        if isinstance(loaded, dict) and loaded.get("status") == "pending":
            client.delete(storage_key)
    except (TypeError, json.JSONDecodeError, RedisError):
        logger.exception("Idempotency pending clear failed")
