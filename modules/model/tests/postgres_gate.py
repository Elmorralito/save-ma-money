"""Gate live PostgreSQL integration tests on a reachable DATABASE_URL."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

import pytest

_POSTGRES_SKIP_REASON = "DATABASE_URL must point to a reachable PostgreSQL for live integration tests"
_B1_SKIP_REASON = "DATABASE_URL must point to a reachable Supabase transaction pooler (:6543) for B1 smoke tests"


@dataclass(frozen=True)
class B1GateStatus:
    """Outcome of the B1 pooler smoke gate.

    Attributes:
        ok: True when a pooler URL is configured and accepts connections.
        message: Human-readable status (safe — no credentials).
    """

    ok: bool
    message: str


def postgres_url() -> str | None:
    """Return a PostgreSQL URL from env, or None when unset/invalid."""
    url = os.environ.get("DATABASE_URL") or os.environ.get("TEST_DATABASE_URL")
    if not url or not str(url).startswith("postgresql"):
        return None
    return str(url)


def postgres_available() -> bool:
    """Return True only when DATABASE_URL is set and the server accepts connections."""
    url = postgres_url()
    if url is None:
        return False

    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


def is_supabase_pooler_url(url: str | None) -> bool:
    """Return True when the URL targets a Supabase transaction pooler (B1)."""
    if not url:
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host == "pooler.supabase.com" or host.endswith(".pooler.supabase.com"):
        return True
    return parsed.port == 6543


def b1_gate_status() -> B1GateStatus:
    """Classify why B1 smoke can or cannot run (no secrets in the message)."""
    url = postgres_url()
    if url is None:
        return B1GateStatus(
            ok=False,
            message=(
                "B1 gate: DATABASE_URL is unset or not a postgresql* URL "
                "(export it or add it to environments/$PAPITA_ENV/.env)."
            ),
        )

    parsed = urlparse(url)
    host = parsed.hostname or "?"
    port = parsed.port
    if not is_supabase_pooler_url(url):
        return B1GateStatus(
            ok=False,
            message=(
                f"B1 gate: DATABASE_URL points at {host}:{port}, which is not a "
                "Supabase transaction pooler. Need host *.pooler.supabase.com or port 6543 "
                "(local Docker :5432/:5435 is B0 and will skip)."
            ),
        )

    if not postgres_available():
        return B1GateStatus(
            ok=False,
            message=(
                f"B1 gate: pooler URL shape OK ({host}:{port}) but SELECT 1 failed "
                "(check password, TLS/sslmode, network, or project pause)."
            ),
        )

    return B1GateStatus(ok=True, message=f"B1 gate: OK ({host}:{port})")


def supabase_b1_available() -> bool:
    """Return True when B1 pooler URL is configured and accepts connections."""
    return b1_gate_status().ok


_B1_STATUS = b1_gate_status()
requires_postgres = pytest.mark.skipif(not postgres_available(), reason=_POSTGRES_SKIP_REASON)
requires_supabase_b1 = pytest.mark.skipif(
    not _B1_STATUS.ok,
    reason=_B1_STATUS.message if not _B1_STATUS.ok else _B1_SKIP_REASON,
)
