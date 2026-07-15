"""Authentication dependencies — Bearer JWT to tenant owner.

FastAPI ``Depends`` callables that extract OAuth2 bearer tokens, validate JWT
claims, and resolve the active tenant owner via ``UsersService``. Used by
protected v1 routes.

In ``AUTH_PROVIDER=supabase`` mode, missing local rows are provisioned from
Auth claims (``sub`` → ``users.id``).

Key exports:
    oauth2_scheme: Optional OAuth2 bearer extractor (``auto_error=False``).
    get_auth_manager: Factory for the configured ``AuthSecurityManager``.
    get_current_owner: Require a valid token and return the tenant ``UsersDTO``.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.dependencies.services import get_users_service
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import ProviderType
from papita_txnsmodel.services.users import UsersService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


def _profile_from_supabase_claims(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract optional Papita profile fields from a Supabase access-token payload.

    Missing keys are omitted so ``ensure_from_auth_subject`` leaves stored values
    unchanged. ``provider_type`` is taken from ``app_metadata.provider`` when it
    matches a known ``ProviderType``.
    """
    profile: dict[str, Any] = {}
    meta = payload.get("user_metadata")
    if isinstance(meta, dict):
        for key in ("display_name", "full_name", "name"):
            value = meta.get(key)
            if isinstance(value, str) and value.strip():
                profile["display_name"] = value.strip()
                break
        phone = meta.get("phone")
        if isinstance(phone, str) and phone.strip():
            profile["phone"] = phone.strip()
    claim_phone = payload.get("phone")
    if "phone" not in profile and isinstance(claim_phone, str) and claim_phone.strip():
        profile["phone"] = claim_phone.strip()

    app_meta = payload.get("app_metadata")
    if isinstance(app_meta, dict):
        raw_provider = app_meta.get("provider")
        if isinstance(raw_provider, str):
            try:
                profile["provider_type"] = ProviderType(raw_provider.lower())
            except ValueError:
                pass
    return profile


def get_auth_manager(settings: Annotated[Settings, Depends(get_settings)]) -> AuthSecurityManager:
    """Return the singleton JWT manager configured from application settings.

    Args:
        settings: Injected API settings (provider, secret, Supabase URL).

    Returns:
        Shared ``AuthSecurityManager`` instance bound to ``settings``.
    """
    return AuthSecurityManager(settings)


def get_current_owner(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
) -> UsersDTO:
    """Decode bearer JWT and resolve the active tenant owner for protected routes.

    Local mode validates signature, token-type claim, and loads ``sub``. Supabase
    mode validates JWKS claims and provisions a local ``UsersDTO`` on first seen.

    Args:
        token: Bearer token from the ``Authorization`` header (may be ``None``).
        settings: Injected API settings for JWT validation parameters.
        users_service: Injected service used to load/provision the owner.

    Returns:
        Active ``UsersDTO`` representing the authenticated tenant owner.

    Raises:
        HTTPException: 401 when the token is missing, invalid, or the owner is not active.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers=_UNAUTHORIZED_HEADERS,
        )

    auth_manager = AuthSecurityManager(settings)
    expected_type = settings.JWT_TOKEN_TYPE if settings.AUTH_PROVIDER == "local" else None
    payload = auth_manager.decode_token(token, expected_type=expected_type)
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

    if settings.AUTH_PROVIDER == "supabase":
        email = str(payload.get("email") or "").strip()
        profile = _profile_from_supabase_claims(payload)
        try:
            owner = users_service.ensure_from_auth_subject(
                subject=owner_id,
                email=email,
                display_name=profile.get("display_name"),
                phone=profile.get("phone"),
                provider_type=profile.get("provider_type"),
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers=_UNAUTHORIZED_HEADERS,
            ) from exc
        return owner

    resolved = users_service.get_owner(owner_id)
    if resolved is None or not resolved.active or resolved.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers=_UNAUTHORIZED_HEADERS,
        )
    return resolved
