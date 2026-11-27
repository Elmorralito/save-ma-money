"""Short-lived server-side OAuth PKCE transaction store (in-memory, single-use)."""

from __future__ import annotations

import secrets
import time
from threading import Lock

_LOCK = Lock()
_TXNS: dict[str, tuple[float, dict[str, str]]] = {}
_MAX_ENTRIES = 1024


def new_oauth_txn_id() -> str:
    """Return a fresh opaque single-use OAuth PKCE transaction ticket ID."""
    return secrets.token_urlsafe(24)


def store_oauth_txn(txn_id: str, payload: dict[str, str], *, ttl_seconds: int = 600) -> None:
    """Persist an OAuth PKCE transaction server-side under a pre-generated ticket ID."""
    now = time.monotonic()
    expires_at = now + max(60, ttl_seconds)
    with _LOCK:
        expired = [k for k, (exp, _val) in _TXNS.items() if exp <= now]
        for key in expired:
            _TXNS.pop(key, None)
        while len(_TXNS) >= _MAX_ENTRIES:
            oldest = next(iter(_TXNS))
            _TXNS.pop(oldest, None)
        _TXNS[txn_id] = (expires_at, dict(payload))


def create_oauth_txn(payload: dict[str, str], *, ttl_seconds: int = 600) -> str:
    """Persist an OAuth PKCE transaction server-side and return an opaque ticket ID."""
    txn_id = new_oauth_txn_id()
    store_oauth_txn(txn_id, payload, ttl_seconds=ttl_seconds)
    return txn_id


def consume_oauth_txn(txn_id: str | None) -> dict[str, str] | None:
    """Consume (one-time) and return a valid non-expired OAuth PKCE transaction."""
    if not txn_id or not isinstance(txn_id, str):
        return None
    now = time.monotonic()
    with _LOCK:
        entry = _TXNS.pop(txn_id.strip(), None)
    if entry is None:
        return None
    expires_at, payload = entry
    if expires_at <= now:
        return None
    return payload
