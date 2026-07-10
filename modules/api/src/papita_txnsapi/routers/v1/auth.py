"""Authentication routes — register, login, and deferred refresh/logout."""

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
    """Register a new user. Does not issue a JWT — client must call ``/auth/login``."""
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
    """OAuth2 password flow — form field ``username`` accepts email or username."""
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
    """Return the authenticated user profile (protected route smoke test)."""
    return UserResponse.from_dto(owner)


@router.post("/refresh", status_code=status.HTTP_501_NOT_IMPLEMENTED, response_model=DeferredResponse)
def refresh_token() -> DeferredResponse:
    """Refresh access token — deferred post-MVP (FR-11)."""
    return _AUTH_DEFERRED


@router.post("/logout", status_code=status.HTTP_501_NOT_IMPLEMENTED, response_model=DeferredResponse)
def logout() -> DeferredResponse:
    """Logout — deferred post-MVP (FR-11)."""
    return _AUTH_DEFERRED
