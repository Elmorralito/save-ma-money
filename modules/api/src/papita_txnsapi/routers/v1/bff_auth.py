"""BFF cookie session routes — login/register/session/refresh/logout (PPT-049).

Thin session boundary inside ``papita_txnsapi``. Wraps the same Supabase / local
credential paths as ``/api/v1/auth/*`` but stores JWTs server-side and sets an
HttpOnly session-id cookie. Direct token clients keep using ``/auth/*``.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.auth_errors import auth_error_detail, public_value_error_detail
from papita_txnsapi.core.bff_session import (
    BFF_COOKIE_PATH,
    BFF_SESSION_COOKIE,
    DEFAULT_BFF_SESSION_MAX_AGE_SECONDS,
    BffSessionRecord,
    BffSessionStore,
    new_session_id,
    parse_owner_id_hint,
)
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.core.session_store import SessionStore
from papita_txnsapi.core.supabase_auth import (
    AuthApiError,
    AuthError,
    SupabaseSignUpProfile,
    classify_supabase_auth_error,
    supabase_refresh_session,
    supabase_sign_in,
    supabase_sign_out,
    supabase_sign_up,
)
from papita_txnsapi.dependencies.auth import get_auth_manager, get_current_owner, oauth2_scheme
from papita_txnsapi.dependencies.bff_session import get_bff_session_store
from papita_txnsapi.dependencies.rate_limit import (
    enforce_auth_login_rate_limit,
    enforce_auth_oauth_rate_limit,
    enforce_auth_register_rate_limit,
)
from papita_txnsapi.dependencies.services import get_users_service
from papita_txnsapi.dependencies.session_store import get_session_store
from papita_txnsapi.routers.v1.auth import (
    _UNAUTHORIZED_HEADERS,
    _cleanup_orphan_auth_user,
    _http_status_for_provision_error,
    _require_supabase_auth_settings,
    _token_response_from_auth,
)
from papita_txnsapi.schemas.auth import UserResponse
from papita_txnsapi.schemas.bff_auth import BffLoginRequest, BffRegisterRequest, BffSessionResponse
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.users import UsersService

logger = logging.getLogger(__name__)

# Opaque ids from ``secrets.token_urlsafe`` (and length bound for Set-Cookie safety).
_BFF_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")

router = APIRouter(prefix="/bff/auth", tags=["BFF Authentication"])


def _session_max_age(settings: Settings) -> int:
    """Return the BFF session cookie max-age from settings."""
    return int(getattr(settings, "BFF_SESSION_MAX_AGE_SECONDS", DEFAULT_BFF_SESSION_MAX_AGE_SECONDS))


def _set_session_cookie(response: Response, *, session_id: str, settings: Settings) -> None:
    """Attach the HttpOnly ``papita_sid`` cookie to ``response``.

    ``session_id`` must be server-generated opaque entropy (see ``new_session_id``),
    never a client-supplied value. Callers must not pass ``request.cookies`` values.
    """
    if _BFF_SESSION_ID_RE.fullmatch(session_id) is None:
        raise ValueError("invalid BFF session id for Set-Cookie")
    response.set_cookie(
        key=BFF_SESSION_COOKIE,
        value=session_id,
        max_age=_session_max_age(settings),
        httponly=True,
        samesite="lax",
        secure=settings.oauth_cookie_secure(),
        path=BFF_COOKIE_PATH,
    )


def _clear_session_cookie(response: Response) -> None:
    """Clear the BFF session cookie (logout / invalid session)."""
    response.delete_cookie(key=BFF_SESSION_COOKIE, path=BFF_COOKIE_PATH)


def _session_response(
    *,
    user: UsersDTO,
    csrf_token: str | None,
    backend: str,
) -> BffSessionResponse:
    """Build an authenticated BFF session JSON body (never includes JWTs)."""
    return BffSessionResponse(
        authenticated=True,
        user=UserResponse.from_dto(user),
        csrf_token=csrf_token,
        session_backend=backend,
    )


def _issue_local_tokens(
    *,
    users_service: UsersService,
    auth_manager: AuthSecurityManager,
    settings: Settings,
    email_or_username: str,
    password: str,
) -> tuple[str, str | None, int, UsersDTO]:
    """Verify local credentials and return access token fields plus owner DTO."""
    user = users_service.verify_credentials(email_or_username, password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers=_UNAUTHORIZED_HEADERS,
        )
    token = auth_manager.generate_token(str(user.id))
    return token, None, settings.JWT_EXPIRATION_TIME_SECONDS, user


def _issue_supabase_tokens(
    *,
    settings: Settings,
    users_service: UsersService,
    email: str,
    password: str,
) -> tuple[str, str | None, int, UsersDTO]:
    """Sign in via Supabase Auth and ensure the Papita tenant row exists."""
    _require_supabase_auth_settings(settings)
    auth_result = None
    try:
        auth_result = supabase_sign_in(
            supabase_url=settings.SUPABASE_URL or "",
            anon_key=settings.SUPABASE_ANON_KEY or "",
            email=email,
            password=password,
        )
        user = users_service.ensure_from_auth_subject(
            subject=auth_result.user_id,
            email=auth_result.email,
        )
        token = _token_response_from_auth(
            access_token=str(auth_result.access_token),
            refresh_token=auth_result.refresh_token,
            expires_in=auth_result.expires_in,
            settings=settings,
        )
        return token.access_token, token.refresh_token, token.expires_in, user
    except (AuthApiError, AuthError) as exc:
        http_status, detail = classify_supabase_auth_error(exc, fallback="login failed")
        if http_status == 401:
            detail = "Incorrect username or password"
        raise HTTPException(
            status_code=http_status if http_status in {401, 429} else status.HTTP_401_UNAUTHORIZED,
            detail=detail if http_status in {401, 429} else "Incorrect username or password",
            headers=_UNAUTHORIZED_HEADERS,
        ) from exc
    except ValueError as exc:
        if auth_result is not None and str(exc) != "User is inactive or deleted":
            _cleanup_orphan_auth_user(
                settings=settings,
                user_id=auth_result.user_id,
                reason="bff-login",
                require_recent=True,
            )
        raise HTTPException(
            status_code=_http_status_for_provision_error(exc),
            detail=public_value_error_detail(exc, fallback="Login failed"),
            headers=_UNAUTHORIZED_HEADERS if str(exc) == "User is inactive or deleted" else None,
        ) from exc


def _refresh_record(
    *,
    settings: Settings,
    record: BffSessionRecord,
) -> BffSessionRecord:
    """Rotate Supabase tokens in-place; local sessions cannot refresh."""
    if settings.AUTH_PROVIDER != "supabase":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="BFF refresh requires AUTH_PROVIDER=supabase",
        )
    if not record.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has no refresh token",
            headers=_UNAUTHORIZED_HEADERS,
        )
    _require_supabase_auth_settings(settings)
    try:
        auth_result = supabase_refresh_session(
            supabase_url=settings.SUPABASE_URL or "",
            anon_key=settings.SUPABASE_ANON_KEY or "",
            refresh_token=record.refresh_token,
        )
        token = _token_response_from_auth(
            access_token=str(auth_result.access_token),
            refresh_token=auth_result.refresh_token or record.refresh_token,
            expires_in=auth_result.expires_in,
            settings=settings,
        )
    except (AuthApiError, AuthError) as exc:
        detail = auth_error_detail(exc, fallback="Invalid or expired refresh token")
        logger.info("BFF refresh failed: %s", detail)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers=_UNAUTHORIZED_HEADERS,
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=public_value_error_detail(exc, fallback="Invalid or expired refresh token"),
        ) from exc

    return BffSessionRecord(
        access_token=token.access_token,
        refresh_token=token.refresh_token,
        csrf_token=record.csrf_token,
        access_expires_at=time.time() + max(1, token.expires_in),
        owner_id=record.owner_id,
    )


@router.post("/login", response_model=BffSessionResponse)
def bff_login(  # pylint: disable=too-many-positional-arguments
    body: BffLoginRequest,
    response: Response,
    _rate_limit: Annotated[None, Depends(enforce_auth_login_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
    auth_manager: Annotated[AuthSecurityManager, Depends(get_auth_manager)],
    bff_store: Annotated[BffSessionStore, Depends(get_bff_session_store)],
) -> BffSessionResponse:
    """Authenticate and set an HttpOnly session-id cookie (JWTs stay server-side)."""
    if settings.AUTH_PROVIDER == "supabase":
        access, refresh, expires_in, user = _issue_supabase_tokens(
            settings=settings,
            users_service=users_service,
            email=body.email.strip(),
            password=body.password,
        )
    else:
        access, refresh, expires_in, user = _issue_local_tokens(
            users_service=users_service,
            auth_manager=auth_manager,
            settings=settings,
            email_or_username=body.email.strip(),
            password=body.password,
        )

    session_id, record = bff_store.create(
        access_token=access,
        refresh_token=refresh,
        expires_in=expires_in,
        owner_id=parse_owner_id_hint(user.id),
        ttl_seconds=_session_max_age(settings),
    )
    _set_session_cookie(response, session_id=session_id, settings=settings)
    return _session_response(user=user, csrf_token=record.csrf_token, backend=bff_store.backend)


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def bff_register(
    body: BffRegisterRequest,
    _rate_limit: Annotated[None, Depends(enforce_auth_register_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
) -> UserResponse:
    """Register via the same Auth/UsersService path as ``POST /auth/register``.

    Does not create a BFF session — clients should call ``POST /bff/auth/login`` next.
    """
    resolved_username = body.username or UsersService.username_from_email(body.email)

    if settings.AUTH_PROVIDER == "supabase":
        _require_supabase_auth_settings(settings)
        auth_result = None
        try:
            auth_result = supabase_sign_up(
                supabase_url=settings.SUPABASE_URL or "",
                anon_key=settings.SUPABASE_ANON_KEY or "",
                email=body.email,
                password=body.password,
                profile=SupabaseSignUpProfile(
                    username=resolved_username,
                    display_name=body.display_name,
                    phone=body.phone,
                    provider=body.provider_type,
                ),
            )
            user = users_service.ensure_from_auth_subject(
                subject=auth_result.user_id,
                email=auth_result.email,
                username=resolved_username,
                display_name=body.display_name,
                phone=body.phone,
                provider_type=body.provider_type,
            )
        except (AuthApiError, AuthError) as exc:
            http_status, detail = classify_supabase_auth_error(exc, fallback="Supabase Auth registration failed")
            raise HTTPException(status_code=http_status, detail=detail) from exc
        except ValueError as exc:
            if auth_result is not None:
                _cleanup_orphan_auth_user(
                    settings=settings,
                    user_id=auth_result.user_id,
                    reason="bff-register",
                    require_recent=False,
                )
            raise HTTPException(
                status_code=_http_status_for_provision_error(exc),
                detail=public_value_error_detail(exc, fallback="Registration failed"),
                headers=_UNAUTHORIZED_HEADERS if str(exc) == "User is inactive or deleted" else None,
            ) from exc
        return UserResponse.from_dto(user)

    user = users_service.register(
        email=body.email,
        password=body.password,
        username=resolved_username,
        display_name=body.display_name,
        phone=body.phone,
        provider_type=body.provider_type,
    )
    return UserResponse.from_dto(user)


@router.get("/session", response_model=BffSessionResponse)
def bff_session(  # pylint: disable=too-many-positional-arguments
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
    bff_store: Annotated[BffSessionStore, Depends(get_bff_session_store)],
    session_store: Annotated[SessionStore, Depends(get_session_store)],
) -> BffSessionResponse:
    """Probe BFF session for SPA bootstrap.

    Returns ``authenticated: false`` (200) when no valid cookie/Bearer — avoids
    treating anonymous bootstrap as an error. When authenticated via cookie,
    includes ``csrf_token`` for mutation headers.
    """
    try:
        owner = get_current_owner(
            request=request,
            token=token,
            settings=settings,
            users_service=users_service,
            session_store=session_store,
            bff_store=bff_store,
        )
    except HTTPException as exc:
        if exc.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_503_SERVICE_UNAVAILABLE}:
            return BffSessionResponse(authenticated=False, session_backend=bff_store.backend)
        raise

    csrf_token: str | None = None
    session_id = request.cookies.get(BFF_SESSION_COOKIE)
    if session_id:
        record = bff_store.get(session_id)
        if record is not None:
            csrf_token = record.csrf_token
    return _session_response(user=owner, csrf_token=csrf_token, backend=bff_store.backend)


@router.post("/refresh", response_model=BffSessionResponse)
def bff_refresh(
    request: Request,
    response: Response,
    _rate_limit: Annotated[None, Depends(enforce_auth_oauth_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
    bff_store: Annotated[BffSessionStore, Depends(get_bff_session_store)],
) -> BffSessionResponse:
    """Rotate tokens inside the BFF session store (cookie required)."""
    session_id = request.cookies.get(BFF_SESSION_COOKIE)
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing BFF session cookie",
            headers=_UNAUTHORIZED_HEADERS,
        )
    record = bff_store.get(session_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired BFF session",
            headers=_UNAUTHORIZED_HEADERS,
        )

    updated = _refresh_record(settings=settings, record=record)
    # Rotate the opaque cookie id so Set-Cookie never echoes a client-supplied value.
    rotated_id = new_session_id()
    bff_store.delete(session_id)
    bff_store.update(rotated_id, updated, ttl_seconds=_session_max_age(settings))
    _set_session_cookie(response, session_id=rotated_id, settings=settings)

    auth_manager = AuthSecurityManager(settings)
    expected_type = settings.JWT_TOKEN_TYPE if settings.AUTH_PROVIDER == "local" else None
    payload = auth_manager.decode_token(updated.access_token, expected_type=expected_type)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers=_UNAUTHORIZED_HEADERS,
        )
    owner = users_service.get_owner(payload["sub"]) if settings.AUTH_PROVIDER == "local" else None
    if settings.AUTH_PROVIDER == "supabase":
        owner = users_service.ensure_from_auth_subject(
            subject=uuid.UUID(str(payload["sub"])),
            email=str(payload.get("email") or "").strip(),
        )
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers=_UNAUTHORIZED_HEADERS,
        )
    return _session_response(user=owner, csrf_token=updated.csrf_token, backend=bff_store.backend)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def bff_logout(
    request: Request,
    response: Response,
    _rate_limit: Annotated[None, Depends(enforce_auth_oauth_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    bff_store: Annotated[BffSessionStore, Depends(get_bff_session_store)],
    session_store: Annotated[SessionStore, Depends(get_session_store)],
) -> Response:
    """Clear BFF session cookie, revoke at IdP when possible, denylist access JWT."""
    session_id = request.cookies.get(BFF_SESSION_COOKIE)
    record = bff_store.get(session_id) if session_id else None

    if record is not None and settings.AUTH_PROVIDER == "supabase" and record.refresh_token:
        try:
            _require_supabase_auth_settings(settings)
            supabase_sign_out(
                supabase_url=settings.SUPABASE_URL or "",
                anon_key=settings.SUPABASE_ANON_KEY or "",
                access_token=record.access_token,
                refresh_token=record.refresh_token,
            )
        except (AuthApiError, AuthError, ValueError, HTTPException) as exc:
            logger.info("BFF Supabase sign_out best-effort failed: %s", exc)

    if record is not None and session_store.available:
        session_store.revoke(record.access_token, ttl_seconds=settings.JWT_EXPIRATION_TIME_SECONDS)

    if session_id:
        bff_store.delete(session_id)
    _clear_session_cookie(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
