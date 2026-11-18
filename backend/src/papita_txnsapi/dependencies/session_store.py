"""FastAPI dependencies for Redis session / JWT denylist store (PPT-043)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.redis import get_redis_from_app
from papita_txnsapi.core.session_store import SessionStore


def get_session_store(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionStore:
    """Return a JWT denylist store backed by Redis when enabled.

    When ``REDIS_ENABLED`` is true, the store uses **fail-closed** denylist checks
    so Redis errors cannot resurrect a revoked token (503 at the auth dependency).

    Args:
        request: Incoming request (``app.state.redis``).
        settings: Application settings (Redis flags and JWT TTL).

    Returns:
        ``SessionStore``; ``available`` is ``False`` when Redis is disabled.
    """
    client = get_redis_from_app(request.app) if settings.REDIS_ENABLED else None
    return SessionStore(
        client,
        default_ttl_seconds=settings.JWT_EXPIRATION_TIME_SECONDS,
        fail_closed=settings.REDIS_ENABLED,
    )
