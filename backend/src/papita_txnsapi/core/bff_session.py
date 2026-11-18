"""BFF browser session binding store (PPT-049 / PPT-059).

Maps an opaque session id (HttpOnly cookie) to server-side access/refresh tokens.
This is **not** the JWT denylist (:class:`~papita_txnsapi.core.session_store.SessionStore`).

When Redis is unavailable/disabled, an in-memory map is used (B0/dev only — not
shared across uvicorn workers). When Redis is required (``fail_closed=True`` /
``REDIS_ENABLED``), Redis errors and a missing client **fail closed** — no silent
process-memory fallback (PPT-059).

Key exports:
    BFF_SESSION_COOKIE: Cookie name for the opaque session id.
    BFF_CSRF_HEADER: Required header on cookie-authenticated mutations.
    BffSessionRecord: Stored binding (tokens + CSRF + access expiry).
    BffSessionStore: Redis or memory session map.
    BffSessionStoreUnavailableError: Raised when fail-closed store cannot use Redis.
    clear_memory_bff_sessions: Test helper to reset the process-local map.
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from papita_txnsapi.core.redis_keys import redis_key

logger = logging.getLogger(__name__)

BFF_SESSION_COOKIE = "papita_sid"
BFF_CSRF_HEADER = "X-Papita-CSRF"
BFF_COOKIE_PATH = "/api"
# Default cookie lifetime (refresh can extend the binding while the cookie lives).
DEFAULT_BFF_SESSION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60

_memory_lock = threading.RLock()
_memory_sessions: dict[str, str] = {}


class BffSessionStoreUnavailableError(RuntimeError):
    """Raised when a fail-closed BFF session store cannot consult Redis."""


def clear_memory_bff_sessions() -> None:
    """Clear the process-local BFF session map (tests / worker restart)."""
    with _memory_lock:
        _memory_sessions.clear()


def new_session_id() -> str:
    """Return a high-entropy opaque session identifier."""
    return secrets.token_urlsafe(32)


def new_csrf_token() -> str:
    """Return a high-entropy CSRF token for the double-submit header."""
    return secrets.token_urlsafe(32)


@dataclass(slots=True)
class BffSessionRecord:
    """Server-side binding for one browser BFF session.

    Attributes:
        access_token: Bearer JWT attached in-process for protected v1 routes.
        refresh_token: Optional Supabase refresh token (``None`` for local HS256).
        csrf_token: Value the SPA must send as ``X-Papita-CSRF`` on mutations.
        access_expires_at: Unix timestamp when the access token should be treated expired.
        owner_id: Optional tenant user id string for diagnostics (not authorization).
    """

    access_token: str
    refresh_token: str | None
    csrf_token: str
    access_expires_at: float
    owner_id: str | None = None

    def to_json(self) -> str:
        """Serialize the record for Redis / memory storage."""
        return json.dumps(asdict(self), separators=(",", ":"))

    @classmethod
    def from_json(cls, raw: str) -> BffSessionRecord:
        """Deserialize a record from storage JSON.

        Args:
            raw: JSON object previously produced by :meth:`to_json`.

        Returns:
            Parsed session record.

        Raises:
            ValueError: When the payload is malformed.
        """
        try:
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid BFF session payload") from exc
        try:
            return cls(
                access_token=str(data["access_token"]),
                refresh_token=data.get("refresh_token"),
                csrf_token=str(data["csrf_token"]),
                access_expires_at=float(data["access_expires_at"]),
                owner_id=data.get("owner_id"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid BFF session payload") from exc

    def access_expired(self, *, skew_seconds: float = 30.0) -> bool:
        """Return whether the access token should be refreshed.

        Args:
            skew_seconds: Refresh slightly before absolute expiry.
        """
        return time.time() >= (self.access_expires_at - skew_seconds)


class BffSessionStore:
    """Session-id → token binding store (Redis when available, else memory).

    Args:
        client: Optional Redis client. When ``None`` and not fail-closed, uses process memory.
        default_ttl_seconds: TTL applied to new/updated session keys.
        fail_closed: When ``True``, missing Redis or Redis errors raise
            :class:`BffSessionStoreUnavailableError` instead of falling back to memory
            (PPT-059; wire from ``REDIS_ENABLED``).
    """

    def __init__(
        self,
        client: Redis | None,
        *,
        default_ttl_seconds: int,
        fail_closed: bool = False,
    ) -> None:
        self._client = client
        self._default_ttl_seconds = max(60, default_ttl_seconds)
        self._fail_closed = fail_closed

    @property
    def backend(self) -> str:
        """``redis`` or ``memory``."""
        return "redis" if self._client is not None else "memory"

    @property
    def fail_closed(self) -> bool:
        """Whether Redis is required (no process-memory fallback)."""
        return self._fail_closed

    def create(
        self,
        *,
        access_token: str,
        refresh_token: str | None,
        expires_in: int,
        owner_id: str | None = None,
        ttl_seconds: int | None = None,
    ) -> tuple[str, BffSessionRecord]:
        """Create a new session binding.

        Returns:
            ``(session_id, record)`` including a fresh CSRF token.

        Raises:
            BffSessionStoreUnavailableError: When fail-closed and Redis cannot persist.
        """
        session_id = new_session_id()
        record = BffSessionRecord(
            access_token=access_token,
            refresh_token=refresh_token,
            csrf_token=new_csrf_token(),
            access_expires_at=time.time() + max(1, expires_in),
            owner_id=owner_id,
        )
        self._set(session_id, record, ttl_seconds=ttl_seconds)
        return session_id, record

    def get(self, session_id: str) -> BffSessionRecord | None:
        """Load a session by id, or ``None`` when missing/invalid.

        Raises:
            BffSessionStoreUnavailableError: When fail-closed and Redis cannot be read.
        """
        if not session_id:
            return None
        raw = self._get_raw(session_id)
        if raw is None:
            return None
        try:
            return BffSessionRecord.from_json(raw)
        except ValueError:
            # Log only a truncated digest — never raw cookie/session material (log injection).
            digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:12]
            logger.warning("Dropping corrupt BFF session id_digest=%s", digest)
            self.delete(session_id)
            return None

    def update(self, session_id: str, record: BffSessionRecord, *, ttl_seconds: int | None = None) -> None:
        """Overwrite an existing session binding (e.g. after refresh).

        Raises:
            BffSessionStoreUnavailableError: When fail-closed and Redis cannot persist.
        """
        if not session_id:
            return
        self._set(session_id, record, ttl_seconds=ttl_seconds)

    def delete(self, session_id: str) -> None:
        """Remove a session binding.

        Raises:
            BffSessionStoreUnavailableError: When fail-closed and Redis delete fails
                or the Redis client is missing.
        """
        if not session_id:
            return
        if self._client is None:
            if self._fail_closed:
                raise BffSessionStoreUnavailableError("BFF session Redis client unavailable")
            with _memory_lock:
                _memory_sessions.pop(session_id, None)
            return
        key = redis_key("bff", "session", session_id)
        try:
            self._client.delete(key)
        except RedisError as exc:
            logger.exception("Failed to delete BFF session from Redis")
            if self._fail_closed:
                raise BffSessionStoreUnavailableError("BFF session Redis delete failed") from exc

    def _set(self, session_id: str, record: BffSessionRecord, *, ttl_seconds: int | None) -> None:
        """Persist ``record`` under ``session_id`` (Redis preferred; memory only when open)."""
        ttl = self._default_ttl_seconds if ttl_seconds is None else max(60, ttl_seconds)
        payload = record.to_json()
        if self._client is None:
            if self._fail_closed:
                raise BffSessionStoreUnavailableError("BFF session Redis client unavailable")
            with _memory_lock:
                _memory_sessions[session_id] = payload
            return
        key = redis_key("bff", "session", session_id)
        try:
            self._client.setex(key, ttl, payload)
        except RedisError as exc:
            logger.exception("Failed to persist BFF session to Redis")
            if self._fail_closed:
                raise BffSessionStoreUnavailableError("BFF session Redis write failed") from exc
            logger.warning("Falling back to memory BFF session (fail_closed=false)")
            with _memory_lock:
                _memory_sessions[session_id] = payload

    def _get_raw(self, session_id: str) -> str | None:
        """Return the raw JSON payload for ``session_id``, or ``None``."""
        if self._client is None:
            if self._fail_closed:
                raise BffSessionStoreUnavailableError("BFF session Redis client unavailable")
            with _memory_lock:
                return _memory_sessions.get(session_id)
        key = redis_key("bff", "session", session_id)
        try:
            value = self._client.get(key)
        except RedisError as exc:
            logger.exception("Failed to read BFF session from Redis")
            if self._fail_closed:
                raise BffSessionStoreUnavailableError("BFF session Redis read failed") from exc
            with _memory_lock:
                return _memory_sessions.get(session_id)
        if value is None:
            if self._fail_closed:
                return None
            with _memory_lock:
                return _memory_sessions.get(session_id)
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)


def parse_owner_id_hint(subject: uuid.UUID | str | None) -> str | None:
    """Normalize an optional owner id for session diagnostics."""
    if subject is None:
        return None
    return str(subject)
