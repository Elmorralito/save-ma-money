"""FastAPI dependencies for optional Redis client access (PPT-043)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from redis import Redis

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.redis import get_redis_from_app


def get_optional_redis(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Redis | None:
    """Return the app Redis client when enabled; otherwise ``None``.

    Args:
        request: Incoming request (``app.state.redis``).
        settings: Application settings controlling ``REDIS_ENABLED``.

    Returns:
        ``Redis`` client or ``None`` when Redis is disabled or not initialized.
    """
    if not settings.REDIS_ENABLED:
        return None
    return get_redis_from_app(request.app)
