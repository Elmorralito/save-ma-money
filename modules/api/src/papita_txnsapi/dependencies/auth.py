"""Authentication dependencies — Bearer JWT / BFF cookie to tenant owner.

FastAPI ``Depends`` callables that extract OAuth2 bearer tokens **or** resolve
an HttpOnly BFF session cookie (PPT-049), validate JWT claims, and resolve the
active tenant owner via ``UsersService``. Used by protected v1 routes.

In ``AUTH_PROVIDER=supabase`` mode, missing local rows are provisioned from
Auth claims (``sub`` → ``users.id``).

Key exports:
    oauth2_scheme: Optional OAuth2 bearer extractor (``auto_error=False``).
    get_auth_manager: Factory for the configured ``AuthSecurityManager``.
    get_current_owner: Require a valid token and return the tenant ``UsersDTO``.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.bff_session import (
    BFF_SESSION_COOKIE,
    BffSessionRecord,
    BffSessionStore,
    BffSessionStoreUnavailableError,
)
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.core.session_store import SessionStore, SessionStoreUnavailableError
from papita_txnsapi.core.supabase_auth import AuthApiError, AuthError, supabase_refresh_session
from papita_txnsapi.dependencies.bff_session import get_bff_session_store
from papita_txnsapi.dependencies.services import get_users_service
from papita_txnsapi.dependencies.session_store import get_session_store
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import ProviderType
from papita_txnsmodel.services.users import UsersService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}
logger = logging.getLogger(__name__)


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


def _resolve_access_token_from_bff(
    request: Request,
    settings: Settings,
    bff_store: BffSessionStore,
) -> str | None:
    """Resolve a bearer access token from the BFF session cookie when present.

    When the stored access token is near expiry and a refresh token exists
    (Supabase), rotates tokens in the session store before returning the new
    access JWT.
    """
    session_id = request.cookies.get(BFF_SESSION_COOKIE)
    if not session_id:
        return None
    record = bff_store.get(session_id)
    if record is None:
        return None

    if record.access_expired() and record.refresh_token and settings.AUTH_PROVIDER == "supabase":
        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            return None
        try:
            auth_result = supabase_refresh_session(
                supabase_url=settings.SUPABASE_URL,
                anon_key=settings.SUPABASE_ANON_KEY,
                refresh_token=record.refresh_token,
            )
            expires_in = max(1, int(auth_result.expires_in or settings.JWT_EXPIRATION_TIME_SECONDS))
            updated = BffSessionRecord(
                access_token=str(auth_result.access_token),
                refresh_token=auth_result.refresh_token or record.refresh_token,
                csrf_token=record.csrf_token,
                access_expires_at=time.time() + expires_in,
                owner_id=record.owner_id,
            )
            ttl = int(getattr(settings, "BFF_SESSION_MAX_AGE_SECONDS", 7 * 24 * 60 * 60))
            bff_store.update(session_id, updated, ttl_seconds=ttl)
            return updated.access_token
        except (AuthApiError, AuthError, ValueError) as exc:
            logger.info("BFF silent refresh failed: %s", exc)
            bff_store.delete(session_id)
            return None

    return record.access_token


def get_current_owner(  # pylint: disable=too-many-positional-arguments
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
    session_store: Annotated[SessionStore, Depends(get_session_store)],
    bff_store: Annotated[BffSessionStore, Depends(get_bff_session_store)],
) -> UsersDTO:
    """Decode bearer JWT (header or BFF cookie) and resolve the tenant owner.

    Prefer ``Authorization: Bearer`` when present (token clients / ``auth-smoke``).
    Otherwise resolve the HttpOnly BFF session cookie and attach the stored
    access token in-process (PPT-049). Local mode validates signature,
    token-type claim, and loads ``sub``. Supabase mode validates JWKS claims and
    provisions a local ``UsersDTO`` on first seen. When Redis is enabled,
    revoked access tokens in the denylist are rejected (PPT-043). Denylist
    checks **fail closed** when Redis is required.

    Args:
        request: Incoming request (BFF session cookie).
        token: Bearer token from the ``Authorization`` header (may be ``None``).
        settings: Injected API settings for JWT validation parameters.
        users_service: Injected service used to load/provision the owner.
        session_store: Optional Redis-backed JWT denylist.
        bff_store: BFF session-id → token binding store.

    Returns:
        Active ``UsersDTO`` representing the authenticated tenant owner.

    Raises:
        HTTPException: 401 when the token is missing, invalid, revoked, or the
            owner is not active; 503 when Redis denylist or BFF session store is
            required but unavailable (PPT-043 / PPT-059).
    """
    try:
        if not token:
            token = _resolve_access_token_from_bff(request, settings, bff_store)
    except BffSessionStoreUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="BFF session store unavailable",
        ) from exc

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers=_UNAUTHORIZED_HEADERS,
        )

    try:
        if settings.REDIS_ENABLED and not session_store.available:
            raise SessionStoreUnavailableError("JWT denylist Redis client unavailable")
        if session_store.is_revoked(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers=_UNAUTHORIZED_HEADERS,
            )
    except SessionStoreUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Token revocation store unavailable",
        ) from exc

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
