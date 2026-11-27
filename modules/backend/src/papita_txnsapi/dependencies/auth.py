"""Authentication dependencies — Stateless Bearer JWT to tenant owner.

FastAPI ``Depends`` callables that extract OAuth2 bearer tokens, validate HS256 JWT
claims, and resolve the active tenant owner via ``UsersService``.
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.auth_provider import AuthProvider, build_auth_provider
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.dependencies.services import get_users_service
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.users import UsersService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

AUTH_ACCESS_COOKIE = "papita_access_token"
AUTH_COOKIE_PATH = "/api"

_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}
logger = logging.getLogger(__name__)


def get_auth_manager(settings: Annotated[Settings, Depends(get_settings)]) -> AuthSecurityManager:
    """Return the singleton JWT manager configured from application settings."""
    return AuthSecurityManager(settings)


def get_auth_provider(settings: Annotated[Settings, Depends(get_settings)]) -> AuthProvider:
    """Return the configured self-hosted ``AuthProvider``."""
    return build_auth_provider(settings)


def get_current_owner(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
) -> UsersDTO:
    """Decode stateless Bearer JWT (header or HttpOnly cookie) and resolve the tenant owner."""
    resolved_token = token or (request.cookies.get(AUTH_ACCESS_COOKIE) or "").strip() or None
    if not resolved_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers=_UNAUTHORIZED_HEADERS,
        )

    auth_manager = AuthSecurityManager(settings)
    payload = auth_manager.decode_token(resolved_token, expected_type=settings.JWT_TOKEN_TYPE)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers=_UNAUTHORIZED_HEADERS,
        )

    try:
        owner_id = uuid.UUID(str(payload["sub"]))
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers=_UNAUTHORIZED_HEADERS,
        ) from exc

    resolved = users_service.get_owner(owner_id)
    if resolved is None or not resolved.active or resolved.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers=_UNAUTHORIZED_HEADERS,
        )
    return resolved
