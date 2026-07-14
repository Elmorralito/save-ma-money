"""Authentication routes — register, login, and deferred refresh/logout.

Exposes identity endpoints under ``/auth``. Behavior depends on
``Settings.AUTH_PROVIDER``:

* ``supabase`` — register/login via Supabase Auth (`sign_up` / `sign_in_with_password`);
  protected routes verify access JWTs with JWKS.
* ``local`` — register/login against ``UsersService`` and issue HS256 JWTs (tests / B0).

Profile read (``/auth/me``) requires a valid JWT in both modes.

Routes:
    ``POST /auth/register`` — create user (Supabase Auth or local).
    ``POST /auth/login`` — OAuth2 password flow; returns Auth or local access JWT.
    ``GET /auth/me`` — authenticated profile smoke test.
    ``POST /auth/refresh`` — deferred (501).
    ``POST /auth/logout`` — deferred (501).
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.core.supabase_auth import AuthApiError, AuthError, supabase_sign_in, supabase_sign_up
from papita_txnsapi.dependencies.auth import get_auth_manager, get_current_owner
from papita_txnsapi.dependencies.rate_limit import enforce_auth_login_rate_limit, enforce_auth_register_rate_limit
from papita_txnsapi.dependencies.services import get_users_service
from papita_txnsapi.schemas.auth import RegisterRequest, TokenResponse, UserResponse
from papita_txnsapi.schemas.common import DeferredResponse
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.users import UsersService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

_AUTH_DEFERRED = DeferredResponse(deferred_reason="FR-11 refresh/logout deferred — stateless JWT MVP")
_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}
_SUPABASE_AUTH_REQUIRED = "AUTH_PROVIDER=supabase requires SUPABASE_URL and SUPABASE_ANON_KEY for register/login"


def _require_supabase_auth_settings(settings: Settings) -> None:
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_SUPABASE_AUTH_REQUIRED)


def _auth_error_detail(exc: Exception, *, fallback: str) -> str:
    message = getattr(exc, "message", None) or str(exc) or fallback
    return str(message)


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register_user(
    body: RegisterRequest,
    _rate_limit: Annotated[None, Depends(enforce_auth_register_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
) -> UserResponse:
    """Register a new user via Supabase Auth (or local UsersService).

    Supabase mode calls ``auth.sign_up``, then provisions a local ``users`` row
    with ``id = Auth sub``. Local mode persists credentials in Postgres only.

    Args:
        body: Username, email, and password for the new account.
        _rate_limit: Side-effect dependency enforcing registration rate limits.
        settings: Application settings selecting Auth provider.
        users_service: Injected users service for local persistence / provisioning.

    Returns:
        Public user profile without secrets.

    Raises:
        HTTPException: 503 when Supabase Auth is misconfigured; 400 on Auth errors.
        ValueError: Propagated from the service layer on duplicate username/email.
    """
    if settings.AUTH_PROVIDER == "supabase":
        _require_supabase_auth_settings(settings)
        try:
            auth_result = supabase_sign_up(
                supabase_url=settings.SUPABASE_URL or "",
                anon_key=settings.SUPABASE_ANON_KEY or "",
                email=body.email,
                password=body.password,
                username=body.username,
            )
            user = users_service.ensure_from_auth_subject(
                subject=auth_result.user_id,
                email=auth_result.email,
                username=body.username,
            )
        except (AuthApiError, AuthError) as exc:
            detail = _auth_error_detail(exc, fallback="Supabase Auth registration failed")
            logger.info("Supabase sign_up failed: %s", detail)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
        except ValueError as exc:
            logger.exception("Supabase signup provision error")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        return UserResponse.from_dto(user)

    user = users_service.register(username=body.username, email=body.email, password=body.password)
    return UserResponse.from_dto(user)


@router.post("/login", response_model=TokenResponse)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    _rate_limit: Annotated[None, Depends(enforce_auth_login_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
    auth_manager: Annotated[AuthSecurityManager, Depends(get_auth_manager)],
) -> TokenResponse:
    """OAuth2 password flow — Supabase Auth sign-in or local credential verify.

    Supabase mode requires email in the ``username`` form field and returns the
    Auth access token. Local mode accepts email or username and mints HS256.

    Args:
        form: Standard OAuth2 password grant fields (``username``, ``password``).
        _rate_limit: Side-effect dependency enforcing login rate limits.
        settings: Application settings supplying token type and Auth provider.
        users_service: Injected users service for credential verification / provision.
        auth_manager: Local JWT encoder (unused when ``AUTH_PROVIDER=supabase``).

    Returns:
        Bearer access token with expiry metadata for API authorization.

    Raises:
        HTTPException: 401 when credentials do not match; 503 when Auth misconfigured.
    """
    if settings.AUTH_PROVIDER == "supabase":
        _require_supabase_auth_settings(settings)
        email = form.username.strip()
        if "@" not in email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Supabase Auth login requires email in the username field",
                headers=_UNAUTHORIZED_HEADERS,
            )
        try:
            auth_result = supabase_sign_in(
                supabase_url=settings.SUPABASE_URL or "",
                anon_key=settings.SUPABASE_ANON_KEY or "",
                email=email,
                password=form.password,
            )
            users_service.ensure_from_auth_subject(
                subject=auth_result.user_id,
                email=auth_result.email,
            )
            expires_in = int(auth_result.expires_in or settings.JWT_EXPIRATION_TIME_SECONDS)
            return TokenResponse(
                access_token=str(auth_result.access_token),
                token_type=settings.JWT_TOKEN_TYPE,
                expires_in=max(expires_in, 1),
            )
        except (AuthApiError, AuthError) as exc:
            logger.info("Supabase sign_in failed: %s", _auth_error_detail(exc, fallback="login failed"))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers=_UNAUTHORIZED_HEADERS,
            ) from exc
        except ValueError as exc:
            logger.exception("Supabase login provision error")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    user = users_service.verify_credentials(form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers=_UNAUTHORIZED_HEADERS,
        )

    token = auth_manager.generate_token(str(user.id))
    return TokenResponse(
        access_token=token,
        token_type=settings.JWT_TOKEN_TYPE,
        expires_in=settings.JWT_EXPIRATION_TIME_SECONDS,
    )


@router.get("/me", response_model=UserResponse)
def get_current_user(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
) -> UserResponse:
    """Return the authenticated user profile (protected route smoke test).

    Args:
        owner: Authenticated user resolved from the bearer JWT.

    Returns:
        Public profile for the current session user.
    """
    return UserResponse.from_dto(owner)


@router.post("/refresh", status_code=status.HTTP_501_NOT_IMPLEMENTED, response_model=DeferredResponse)
def refresh_token() -> DeferredResponse:
    """Refresh access token — deferred post-MVP (FR-11).

    Returns:
        Deferred response explaining that refresh is not implemented in the stateless
        JWT MVP.
    """
    return _AUTH_DEFERRED


@router.post("/logout", status_code=status.HTTP_501_NOT_IMPLEMENTED, response_model=DeferredResponse)
def logout() -> DeferredResponse:
    """Logout — deferred post-MVP (FR-11).

    Returns:
        Deferred response explaining that server-side logout is not implemented in the
        stateless JWT MVP.
    """
    return _AUTH_DEFERRED
