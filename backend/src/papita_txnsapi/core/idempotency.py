"""Redis idempotency helpers for mutating API routes (PPT-043).

Stores completed response payloads keyed by tenant + client ``Idempotency-Key``
so retries replay the same result without double-creating ledger rows. Request
body digests prevent silent replay when the same key is reused with a different
payload.

Key exports:
    IdempotencyResult: Outcome of begin/complete helpers.
    begin_idempotency: Claim or replay a key.
    complete_idempotency: Persist the successful response body.
    request_body_digest: Canonical SHA-256 digest of a JSON body.
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


@dataclass(frozen=True, slots=True)
class IdempotencyResult:
    """Outcome of an idempotency begin check.

    Attributes:
        state: ``bypass`` (no Redis/key), ``miss`` (claimed), ``hit`` (replay),
            ``conflict`` (another request still pending), or ``mismatch`` (same key,
            different request body digest).
        payload: Cached completed response body when ``state`` is ``hit``.
    """

    state: Literal["bypass", "miss", "hit", "conflict", "mismatch"]
    payload: dict[str, Any] | None = None


def request_body_digest(body: Mapping[str, Any] | None) -> str:
    """Return a stable SHA-256 hex digest for a JSON-serializable request body.

    Args:
        body: Request payload mapping, or ``None`` (treated as empty object).

    Returns:
        Hex digest of the canonical JSON encoding.
    """
    canonical = json.dumps(body or {}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _idempotency_redis_key(owner_id: UUID | str, scope: str, key: str) -> str:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return redis_key(owner_id, "idem", scope, digest)


def _digests_conflict(stored_digest: object, expected_digest: str | None) -> bool:
    """True when both digests are present and differ."""
    if expected_digest is None or not isinstance(stored_digest, str) or not stored_digest:
        return False
    return stored_digest != expected_digest


def _result_from_stored(raw: str | bytes | None, *, body_digest: str | None = None) -> IdempotencyResult:
    """Map a stored Redis value to hit/conflict/mismatch (never miss)."""
    loaded: object = None
    if raw is not None:
        try:
            loaded = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            loaded = None
    if not isinstance(loaded, dict):
        return IdempotencyResult(state="conflict")
    if _digests_conflict(loaded.get("body_digest"), body_digest):
        return IdempotencyResult(state="mismatch")
    body = loaded.get("body")
    if loaded.get("status") != "pending" and isinstance(body, dict):
        return IdempotencyResult(state="hit", payload=body)
    return IdempotencyResult(state="conflict")


def begin_idempotency(
    client: Redis | None,
    owner_id: UUID | str,
    *,
    scope: str,
    key: str | None,
    ttl_seconds: int,
    body_digest: str | None = None,
) -> IdempotencyResult:
    """Claim an idempotency key or return a prior completed payload.

    Args:
        client: Redis client, or ``None`` to bypass.
        owner_id: Tenant primary key.
        scope: Logical operation scope (e.g. ``transactions:create``).
        key: Client-supplied ``Idempotency-Key``; blank/None bypasses.
        ttl_seconds: Expiration for lock and completed records.
        body_digest: Optional SHA-256 of the request body; when present and the
            stored record has a different digest, returns ``mismatch``.

    Returns:
        :class:`IdempotencyResult` describing whether to proceed, replay, conflict,
        or reject a body mismatch.
    """
    if client is None or key is None or not str(key).strip() or ttl_seconds <= 0:
        return IdempotencyResult(state="bypass")

    storage_key = _idempotency_redis_key(owner_id, scope, str(key).strip())
    try:
        existing = client.get(storage_key)
        if existing is not None:
            return _result_from_stored(existing, body_digest=body_digest)

        pending_payload: dict[str, Any] = {"status": "pending"}
        if body_digest is not None:
            pending_payload["body_digest"] = body_digest
        acquired = client.set(
            storage_key,
            json.dumps(pending_payload, separators=(",", ":")),
            nx=True,
            ex=ttl_seconds,
        )
        if acquired:
            return IdempotencyResult(state="miss")

        # Lost the race — re-read; treat vanished key as a fresh miss.
        raced = client.get(storage_key)
        if raced is None:
            return IdempotencyResult(state="miss")
        return _result_from_stored(raced, body_digest=body_digest)
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
    body_digest: str | None = None,
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
        body_digest: Optional request-body digest stored for mismatch checks.
    """
    if client is None or key is None or not str(key).strip() or ttl_seconds <= 0:
        return
    storage_key = _idempotency_redis_key(owner_id, scope, str(key).strip())
    try:
        payload: dict[str, Any] = {
            "status": "completed",
            "http_status": http_status,
            "body": dict(body),
        }
        if body_digest is not None:
            payload["body_digest"] = body_digest
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
