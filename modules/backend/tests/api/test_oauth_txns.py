"""Unit tests for the short-lived server-side OAuth PKCE transaction store."""

from __future__ import annotations

import pytest

from papita_txnsapi.core import oauth_txns


def test_store_new_and_consume_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stored transaction payloads are single-use and returned cleanly."""
    now = [100.0]
    monkeypatch.setattr(oauth_txns.time, "monotonic", lambda: now[0])
    oauth_txns._TXNS.clear()  # noqa: SLF001

    handle = oauth_txns.new_oauth_txn_id()
    oauth_txns.store_oauth_txn(handle, {"code_verifier": "v1", "state": "s1"}, ttl_seconds=120)
    assert oauth_txns.consume_oauth_txn(f"  {handle}  ") == {"code_verifier": "v1", "state": "s1"}
    assert oauth_txns.consume_oauth_txn(handle) is None


def test_consume_invalid_and_expired_transactions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Blank/missing/expired transactions return None and purge stale entries."""
    now = [500.0]
    monkeypatch.setattr(oauth_txns.time, "monotonic", lambda: now[0])
    oauth_txns._TXNS.clear()  # noqa: SLF001

    assert oauth_txns.consume_oauth_txn(None) is None
    assert oauth_txns.consume_oauth_txn("") is None

    tid = oauth_txns.create_oauth_txn({"state": "expired"}, ttl_seconds=60)
    now[0] = 600.0
    assert oauth_txns.consume_oauth_txn(tid) is None

    # Storing a new entry purges expired ones cleanly.
    stale = oauth_txns.create_oauth_txn({"state": "stale"}, ttl_seconds=60)
    now[0] = 700.0
    fresh = oauth_txns.create_oauth_txn({"state": "fresh"}, ttl_seconds=60)
    assert oauth_txns.consume_oauth_txn(stale) is None
    assert oauth_txns.consume_oauth_txn(fresh) == {"state": "fresh"}


def test_store_evicts_oldest_when_full(monkeypatch: pytest.MonkeyPatch) -> None:
    """Store enforces _MAX_ENTRIES capacity by evicting oldest handles."""
    now = [1000.0]
    monkeypatch.setattr(oauth_txns.time, "monotonic", lambda: now[0])
    oauth_txns._TXNS.clear()  # noqa: SLF001

    monkeypatch.setattr(oauth_txns, "_MAX_ENTRIES", 3)
    first = oauth_txns.create_oauth_txn({"k": "1"})
    second = oauth_txns.create_oauth_txn({"k": "2"})
    third = oauth_txns.create_oauth_txn({"k": "3"})
    fourth = oauth_txns.create_oauth_txn({"k": "4"})

    assert oauth_txns.consume_oauth_txn(first) is None
    assert oauth_txns.consume_oauth_txn(second) == {"k": "2"}
    assert oauth_txns.consume_oauth_txn(third) == {"k": "3"}
    assert oauth_txns.consume_oauth_txn(fourth) == {"k": "4"}
