"""Authentication routes — register, login, and deferred refresh/logout.

Exposes identity endpoints under ``/auth``. Registration and login are public but
rate-limited; profile read requires a valid JWT. Token refresh and logout are
stubbed with 501 responses per FR-11 (stateless JWT MVP).

Routes:
    ``POST /auth/register`` — create user via :class:`~papita_txnsmodel.services.users.UsersService`.
    ``POST /auth/login`` — OAuth2 password flow; issues JWT via
        :class:`~papita_txnsapi.core.security.AuthSecurityManager`.
    ``GET /auth/me`` — authenticated profile smoke test.
    ``POST /auth/refresh`` — deferred (501).
    ``POST /auth/logout`` — deferred (501).

Tenant scoping:
    ``/auth/me`` resolves the owner from the bearer token. Register and login operate
    on the global users table without an ``owner`` filter; subsequent API calls scope
    data through the authenticated user's id.

Service delegation:
    User persistence and credential verification delegate to ``UsersService``; JWT
    encoding is handled by ``AuthSecurityManager`` with settings from ``get_settings``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.dependencies.auth import get_auth_manager, get_current_owner
from papita_txnsapi.dependencies.rate_limit import enforce_auth_login_rate_limit, enforce_auth_register_rate_limit
from papita_txnsapi.dependencies.services import get_users_service
from papita_txnsapi.schemas.auth import RegisterRequest, TokenResponse, UserResponse
from papita_txnsapi.schemas.common import DeferredResponse
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.users import UsersService

router = APIRouter(prefix="/auth", tags=["Authentication"])

_AUTH_DEFERRED = DeferredResponse(deferred_reason="FR-11 refresh/logout deferred — stateless JWT MVP")
_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register_user(
    body: RegisterRequest,
    _rate_limit: Annotated[None, Depends(enforce_auth_register_rate_limit)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
) -> UserResponse:
    """Register a new user. Does not issue a JWT — client must call ``/auth/login``.

    Args:
        body: Username, email, and password for the new account.
        _rate_limit: Side-effect dependency enforcing registration rate limits.
        users_service: Injected users service for credential hashing and persistence.

    Returns:
        Public user profile without secrets.

    Raises:
        ValueError: Propagated from the service layer on duplicate username/email or
            invalid input.
    """
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

    Args:
        form: Standard OAuth2 password grant fields (``username``, ``password``).
        _rate_limit: Side-effect dependency enforcing login rate limits.
        settings: Application settings supplying token type and expiry metadata.
        users_service: Injected users service for credential verification.
        auth_manager: JWT encoder bound to the configured secret and algorithm.

    Returns:
        Bearer access token with expiry metadata for API authorization.

    Raises:
        HTTPException: 401 when credentials do not match a stored user.
    """
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
