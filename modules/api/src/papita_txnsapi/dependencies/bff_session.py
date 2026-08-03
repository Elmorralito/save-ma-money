"""FastAPI dependencies for the BFF session binding store (PPT-049)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.bff_session import DEFAULT_BFF_SESSION_MAX_AGE_SECONDS, BffSessionStore
from papita_txnsapi.core.redis import get_redis_from_app


def get_bff_session_store(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> BffSessionStore:
    """Return the BFF session map (Redis when enabled, else process memory).

    When ``REDIS_ENABLED`` is true, the store is **fail-closed** (PPT-059): Redis
    errors and a missing client raise :class:`BffSessionStoreUnavailableError`
    instead of falling back to process memory.

    Args:
        request: Incoming request (``app.state.redis``).
        settings: Application settings (Redis flags and session TTL).

    Returns:
        ``BffSessionStore`` suitable for cookie session create/lookup/delete.
    """
    client = get_redis_from_app(request.app) if settings.REDIS_ENABLED else None
    ttl = getattr(settings, "BFF_SESSION_MAX_AGE_SECONDS", DEFAULT_BFF_SESSION_MAX_AGE_SECONDS)
    return BffSessionStore(
        client,
        default_ttl_seconds=int(ttl),
        fail_closed=settings.REDIS_ENABLED,
    )
