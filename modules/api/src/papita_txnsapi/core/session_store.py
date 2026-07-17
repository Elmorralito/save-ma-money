"""JWT denylist / session store for Redis (PPT-043).

Provides a Redis-backed revocation set for access tokens. When Redis is required
(``REDIS_ENABLED=true``), denylist checks **fail closed** on Redis errors so a
blip cannot resurrect a revoked token. Cache and rate-limit paths remain fail-open.

Key exports:
    SessionStoreUnavailableError: Raised when fail-closed denylist cannot consult Redis.
    SessionStore: Denylist helper with TTL aligned to JWT lifetime.
"""

from __future__ import annotations

import hashlib
import logging

from redis import Redis
from redis.exceptions import RedisError

from papita_txnsapi.core.redis_keys import redis_key

logger = logging.getLogger(__name__)


class SessionStoreUnavailableError(RuntimeError):
    """Raised when a fail-closed denylist check cannot reach Redis."""


def _token_digest(token: str) -> str:
    """Return a stable SHA-256 hex digest for a bearer token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class SessionStore:
    """Redis SET-based JWT denylist with per-token TTL.

    Args:
        client: Redis client (required for operations to succeed).
        default_ttl_seconds: TTL applied when revoking tokens.
        fail_closed: When ``True``, Redis errors during :meth:`is_revoked` raise
            :class:`SessionStoreUnavailableError` instead of treating the token as
            valid (security tradeoff vs cache/rate-limit fail-open).
    """

    def __init__(
        self,
        client: Redis | None,
        *,
        default_ttl_seconds: int,
        fail_closed: bool = False,
    ) -> None:
        self._client = client
        self._default_ttl_seconds = max(1, default_ttl_seconds)
        self._fail_closed = fail_closed

    @property
    def available(self) -> bool:
        """Whether a Redis client is configured."""
        return self._client is not None

    @property
    def fail_closed(self) -> bool:
        """Whether denylist checks reject traffic when Redis is unreachable."""
        return self._fail_closed

    def revoke(self, token: str, *, ttl_seconds: int | None = None) -> bool:
        """Add ``token`` to the denylist until TTL expires.

        Args:
            token: Raw bearer access token.
            ttl_seconds: Optional override TTL; defaults to store TTL.

        Returns:
            ``True`` when the token was recorded; ``False`` when Redis is unavailable.
        """
        if self._client is None or not token:
            return False
        ttl = self._default_ttl_seconds if ttl_seconds is None else max(1, ttl_seconds)
        key = redis_key("jwt", "denylist", _token_digest(token))
        try:
            self._client.setex(key, ttl, "1")
            return True
        except RedisError:
            logger.exception("Failed to revoke token in session store")
            return False

    def is_revoked(self, token: str) -> bool:
        """Return whether ``token`` is present in the denylist.

        Args:
            token: Raw bearer access token.

        Returns:
            ``True`` when revoked; ``False`` when not found.

        Raises:
            SessionStoreUnavailableError: When ``fail_closed`` is enabled and Redis
                is missing or errors (prefer rejecting the request with 503).
        """
        if not token:
            return False
        if self._client is None:
            if self._fail_closed:
                raise SessionStoreUnavailableError("JWT denylist Redis client unavailable")
            return False
        key = redis_key("jwt", "denylist", _token_digest(token))
        try:
            return bool(self._client.exists(key))
        except RedisError as exc:
            logger.exception("Failed to check token denylist")
            if self._fail_closed:
                raise SessionStoreUnavailableError("JWT denylist Redis check failed") from exc
            return False
