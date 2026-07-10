"""Authentication dependencies — Bearer JWT to tenant owner."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.dependencies.services import get_users_service
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.users import UsersService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


def get_auth_manager(settings: Annotated[Settings, Depends(get_settings)]) -> AuthSecurityManager:
    """Return the singleton JWT manager configured from Settings."""
    return AuthSecurityManager(settings)


def get_current_owner(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
) -> UsersDTO:
    """Decode Bearer JWT and resolve the tenant ``UsersDTO`` for protected routes."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers=_UNAUTHORIZED_HEADERS,
        )

    auth_manager = AuthSecurityManager(settings)
    payload = auth_manager.decode_token(token, expected_type=settings.JWT_TOKEN_TYPE)
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

    owner = users_service.get_owner(owner_id)
    if owner is None or not owner.active or owner.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers=_UNAUTHORIZED_HEADERS,
        )
    return owner
