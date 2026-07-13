"""Authentication routes — register, login, and deferred refresh/logout.

Exposes identity endpoints under ``/auth``. Behavior depends on
``Settings.AUTH_PROVIDER``:

* ``local`` — register / login against ``UsersService`` and issue HS256 JWTs.
* ``supabase`` — optional Auth API pass-through (requires ``SUPABASE_ANON_KEY``);
  preferred path is client → Supabase Auth, then Bearer on this API.

Profile read (``/auth/me``) requires a valid JWT in both modes.

Routes:
    ``POST /auth/register`` — create user (local DB or Supabase signup).
    ``POST /auth/login`` — OAuth2 password flow; issues/returns access JWT.
    ``GET /auth/me`` — authenticated profile smoke test.
    ``POST /auth/refresh`` — deferred (501).
    ``POST /auth/logout`` — deferred (501).
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.core.supabase_auth import supabase_password_grant, supabase_sign_up
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
_SUPABASE_PROXY_REQUIRED = (
    "AUTH_PROVIDER=supabase requires SUPABASE_URL and SUPABASE_ANON_KEY for "
    "API register/login pass-through; or obtain tokens from Supabase Auth directly"
)


def _supabase_user_id(payload: dict[str, Any]) -> uuid.UUID:
    """Extract the Auth user UUID from a Supabase Auth JSON body."""
    user = payload.get("user") if isinstance(payload.get("user"), dict) else payload
    raw = (user or {}).get("id")
    if raw is None:
        raise ValueError("Supabase Auth response missing user id")
    return uuid.UUID(str(raw))


def _supabase_email(payload: dict[str, Any], fallback: str) -> str:
    """Extract email from Auth JSON, falling back to the request email."""
    user = payload.get("user") if isinstance(payload.get("user"), dict) else payload
    email = (user or {}).get("email") or fallback
    return str(email).strip().lower()


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register_user(
    body: RegisterRequest,
    _rate_limit: Annotated[None, Depends(enforce_auth_register_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
) -> UserResponse:
    """Register a new user.

    Local mode persists via ``UsersService`` (no JWT). Supabase mode signs up via
    Auth then provisions a local ``users`` row with ``id = Auth sub``.

    Args:
        body: Username, email, and password for the new account.
        _rate_limit: Side-effect dependency enforcing registration rate limits.
        settings: Application settings selecting Auth provider.
        users_service: Injected users service for credential hashing and persistence.

    Returns:
        Public user profile without secrets.

    Raises:
        HTTPException: 503 when Supabase proxy is misconfigured; 401/400 on Auth errors.
        ValueError: Propagated from the service layer on duplicate username/email.
    """
    if settings.AUTH_PROVIDER == "supabase":
        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_SUPABASE_PROXY_REQUIRED)
        try:
            auth_body = supabase_sign_up(
                supabase_url=settings.SUPABASE_URL,
                anon_key=settings.SUPABASE_ANON_KEY,
                email=body.email,
                password=body.password,
            )
            subject = _supabase_user_id(auth_body)
            email = _supabase_email(auth_body, body.email)
            user = users_service.ensure_from_auth_subject(
                subject=subject,
                email=email,
                username=body.username,
            )
        except httpx.HTTPStatusError as exc:
            detail = "Supabase Auth registration failed"
            try:
                body_json = exc.response.json()
                detail = body_json.get("msg") or body_json.get("error_description") or detail
            except Exception:  # noqa: BLE001 — keep generic Auth failure detail
                pass
            logger.info("Supabase signup failed: %s", exc)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
        except (httpx.HTTPError, ValueError) as exc:
            logger.exception("Supabase signup transport/provision error")
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
    """OAuth2 password flow — form field ``username`` accepts email or username.

    Local mode verifies against ``UsersService`` and mints an HS256 JWT. Supabase
    mode proxies the password grant (email login) and returns the Auth access token.

    Args:
        form: Standard OAuth2 password grant fields (``username``, ``password``).
        _rate_limit: Side-effect dependency enforcing login rate limits.
        settings: Application settings supplying token type and Auth provider.
        users_service: Injected users service for credential verification.
        auth_manager: JWT encoder bound to the configured secret and algorithm.

    Returns:
        Bearer access token with expiry metadata for API authorization.

    Raises:
        HTTPException: 401 when credentials do not match; 503 when proxy misconfigured.
    """
    if settings.AUTH_PROVIDER == "supabase":
        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_SUPABASE_PROXY_REQUIRED)
        email = form.username.strip()
        if "@" not in email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Supabase Auth login requires email in the username field",
                headers=_UNAUTHORIZED_HEADERS,
            )
        try:
            token_body = supabase_password_grant(
                supabase_url=settings.SUPABASE_URL,
                anon_key=settings.SUPABASE_ANON_KEY,
                email=email,
                password=form.password,
            )
            access_token = token_body.get("access_token")
            if not access_token:
                raise ValueError("Supabase Auth response missing access_token")
            subject = _supabase_user_id(token_body)
            users_service.ensure_from_auth_subject(
                subject=subject,
                email=_supabase_email(token_body, email),
            )
            expires_in = int(token_body.get("expires_in") or settings.JWT_EXPIRATION_TIME_SECONDS)
            return TokenResponse(
                access_token=str(access_token),
                token_type=settings.JWT_TOKEN_TYPE,
                expires_in=max(expires_in, 1),
            )
        except httpx.HTTPStatusError as exc:
            logger.info("Supabase login failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers=_UNAUTHORIZED_HEADERS,
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            logger.exception("Supabase login transport/provision error")
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
