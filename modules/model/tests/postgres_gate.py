"""Gate live PostgreSQL integration tests on a reachable DATABASE_URL."""

from __future__ import annotations

import os

import pytest

_POSTGRES_SKIP_REASON = "DATABASE_URL must point to a reachable PostgreSQL for live integration tests"


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


requires_postgres = pytest.mark.skipif(not postgres_available(), reason=_POSTGRES_SKIP_REASON)
