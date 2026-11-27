"""Authentication request and response schemas for ``/api/v1/auth/*``.

Defines JSON bodies for registration, session refresh/logout, Google OAuth
(PKCE) start/callback, plus the public user profile and OAuth2-compatible token
payload returned by auth endpoints.

Passwords are accepted on write paths only and are never serialized on
``UserResponse``. Email is the canonical client login identity;
``users.username`` is a derived handle for the schema unique constraint.
Self-hosted ``AUTH_PROVIDER=local`` issues HS256 access tokens.

Key exports:
    AuthProviderType: Wire literal for credential store (``local`` | legacy ``supabase``).
    RegisterRequest: ``POST /auth/register`` body.
    RefreshRequest / LogoutRequest: Session rotation and revoke bodies.
    OAuthStartResponse / OAuthCodeExchangeRequest / SsoSessionRequest: OAuth/SSO.
    UserResponse / TokenResponse: Public profile and OAuth2 token envelopes.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.contstants import PASSWORD_REGEX
from papita_txnsmodel.model.enums import ProviderType

_PASSWORD_RE = re.compile(PASSWORD_REGEX)

# Wire label for where credentials live (legacy ``supabase`` retained for old rows).
AuthProviderType = Literal["local", "supabase"]


class RegisterRequest(BaseModel):
    """JSON body for ``POST /auth/register``.

    Creates a local password row in ``papita_transactions.users``. Password
    signup is email-only; Google must use the OAuth PKCE routes.

    Attributes:
        email: Contact email and canonical login identifier; 5–255 characters.
        password: Plain-text password; 8–128 characters (never echoed back).
        display_name: Optional human-readable name shown in the app.
        phone: Optional E.164-style phone number.
        provider: Password signup channel (``email`` only).
        username: Optional handle override; when omitted, derived from email.
    """

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, min_length=7, max_length=32)
    provider: Literal["email"] = ProviderType.EMAIL.value
    username: str | None = Field(default=None, min_length=6, max_length=255)

    @field_validator("password")
    @classmethod
    def _validate_password_complexity(cls, value: str) -> str:
        """Enforce password complexity at the API boundary without leaking input."""
        if not _PASSWORD_RE.match(value):
            raise ValueError(
                "Password must be 8-128 characters long, include at least one uppercase letter, "
                "one lowercase letter, one number, and one special character."
            )
        return value

    @property
    def provider_type(self) -> ProviderType:
        """Resolve the wire ``provider`` string to ``ProviderType``.

        Returns:
            ``ProviderType.EMAIL`` for the only allowed register ``provider``.
        """
        return ProviderType(self.provider)


class ResendConfirmationRequest(BaseModel):
    """JSON body for ``POST /auth/resend-confirmation`` and BFF twin (PPT-068).

    Attributes:
        email: Address that may still need signup confirmation.
        email_redirect_to: Optional same-origin confirm landing URL (allowlisted).
    """

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    email_redirect_to: str | None = Field(default=None, max_length=2048)


class RefreshRequest(BaseModel):
    """JSON body for ``POST /auth/refresh`` (deferred under self-hosted HS256).

    Self-hosted local mode returns 501 (no external refresh-token store).

    Attributes:
        refresh_token: Opaque refresh token from a prior session (unused locally).
    """

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1, max_length=4096)


class LogoutRequest(BaseModel):
    """JSON body for ``POST /auth/logout`` (session cookie clear / revoke).

    Self-hosted mode clears the HttpOnly access cookie and returns 501 for
    external refresh-token revoke. ``access_token`` may also arrive via
    ``Authorization: Bearer``.

    Attributes:
        refresh_token: Refresh token placeholder (unused locally).
        access_token: Optional access JWT for precise session revoke / denylist.
    """

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1, max_length=4096)
    access_token: str | None = Field(default=None, min_length=1, max_length=8192)


class OAuthStartResponse(BaseModel):
    """Authorize URL and PKCE verifier from ``GET /auth/oauth/{provider}``.

    Clients open ``url`` in a browser (or use ``follow=true`` for cookie-based
    PKCE). ``code_verifier`` must be sent back on ``POST /auth/oauth/callback``
    unless the browser cookie flow is used.

    Attributes:
        provider: OAuth channel (``google`` or ``github`` only).
        url: Google / IdP authorize URL including the PKCE challenge.
        code_verifier: PKCE verifier the client must retain for code exchange.
    """

    provider: ProviderType
    url: str = Field(min_length=8, max_length=4096)
    code_verifier: str = Field(min_length=16, max_length=128)

    @field_validator("provider")
    @classmethod
    def _oauth_only(cls, value: ProviderType) -> ProviderType:
        if not value.is_oauth():
            raise ValueError(f"provider must be one of {[m.value for m in ProviderType.oauth_members()]}")
        return value


class OAuthCodeExchangeRequest(BaseModel):
    """JSON body for ``POST /auth/oauth/callback`` (legacy PKCE code exchange).

    Browser PKCE completes via ``GET /auth/oauth/callback``. This POST body is
    retained for older clients and returns 501 under self-hosted Google OAuth.

    Attributes:
        provider: OAuth provider (``google`` or ``github``).
        auth_code: Authorization ``code`` from the OAuth redirect query string.
        code_verifier: PKCE verifier from ``GET /auth/oauth/{provider}``.
        redirect_to: Optional redirect URI that must match the authorize step.
        display_name: Optional profile override when IdP metadata is incomplete.
    """

    model_config = ConfigDict(extra="forbid")

    provider: ProviderType = ProviderType.GOOGLE
    auth_code: str = Field(min_length=1, max_length=2048)
    code_verifier: str = Field(min_length=16, max_length=128)
    redirect_to: str | None = Field(default=None, min_length=8, max_length=2048)
    display_name: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("provider")
    @classmethod
    def _oauth_only(cls, value: ProviderType) -> ProviderType:
        if not value.is_oauth():
            raise ValueError(f"provider must be one of {[m.value for m in ProviderType.oauth_members()]}")
        return value


class SsoSessionRequest(BaseModel):
    """JSON body for ``POST /auth/sso`` (deprecated external SSO handoff).

    Prefer ``GET /auth/oauth/google?follow=true`` for direct Google OAuth PKCE.
    This endpoint returns 501 under self-hosted auth.

    Attributes:
        provider: OAuth provider (``google`` or ``github``).
        access_token: External access JWT from a client-side OAuth session.
        refresh_token: External refresh token from a client-side OAuth session.
        display_name: Optional profile override when IdP metadata is incomplete.
    """

    model_config = ConfigDict(extra="forbid")

    provider: ProviderType = ProviderType.GOOGLE
    access_token: str = Field(min_length=1, max_length=8192)
    refresh_token: str = Field(min_length=1, max_length=4096)
    display_name: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("provider")
    @classmethod
    def _oauth_only(cls, value: ProviderType) -> ProviderType:
        if not value.is_oauth():
            raise ValueError(f"provider must be one of {[m.value for m in ProviderType.oauth_members()]}")
        return value


class UserResponse(BaseModel):
    """Public user profile returned by register and ``GET /auth/me``.

    Never includes password or other secrets. ``provider`` is the signup channel
    (email/Google/GitHub); ``auth_provider`` is the credential store label
    (``local``, or legacy ``supabase``).

    Attributes:
        id: Tenant user id (JWT ``sub``).
        username: Unique handle (often derived from email).
        email: Canonical login email.
        display_name: Optional human-readable name.
        phone: Optional phone from profile.
        provider: Signup / identity channel (``ProviderType``).
        auth_provider: Credential store label (``local`` or legacy ``supabase``).
        created_at: Row creation timestamp (required on the DTO).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    display_name: str | None = None
    phone: str | None = None
    provider: ProviderType = ProviderType.EMAIL
    auth_provider: AuthProviderType = "local"
    created_at: datetime

    @classmethod
    def from_dto(cls, user: UsersDTO) -> UserResponse:
        """Build an API response from a model ``UsersDTO``.

        Maps ``provider_type`` (including legacy ``phone`` → ``email``) and
        normalizes ``auth_provider`` to the wire literal. Unknown values map to
        ``local`` (self-hosted default).

        Args:
            user: Persisted tenant user from ``UsersService``.

        Returns:
            Public profile suitable for JSON serialization.

        Raises:
            ValueError: When ``user.created_at`` is missing.
        """
        if user.created_at is None:
            raise ValueError("User record is missing created_at")
        if isinstance(user.provider_type, ProviderType):
            provider = user.provider_type
        else:
            raw = (user.provider_type or ProviderType.EMAIL.value).lower()
            try:
                provider = ProviderType.EMAIL if raw == "phone" else ProviderType(raw)
            except ValueError:
                provider = ProviderType.EMAIL
        auth_provider: AuthProviderType = "supabase" if user.auth_provider == "supabase" else "local"
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            phone=user.phone,
            provider=provider,
            auth_provider=auth_provider,
            created_at=user.created_at,
        )


class RegisterResponse(UserResponse):
    """Public register result with optional email-confirmation pending signal (PPT-068).

    Self-hosted local register always issues a usable account immediately, so
    ``email_confirmation_required`` stays ``False``. The flag remains on the
    wire for older SPA clients.
    """

    email_confirmation_required: bool = False

    @classmethod
    def from_dto(
        cls,
        user: UsersDTO,
        *,
        email_confirmation_required: bool = False,
    ) -> RegisterResponse:
        """Build a register response from a model ``UsersDTO``.

        Args:
            user: Persisted tenant user from ``UsersService``.
            email_confirmation_required: True when the client must confirm email
                before a usable session can be issued.

        Returns:
            Public register payload including the pending-confirmation flag.
        """
        base = UserResponse.from_dto(user)
        return cls(
            **base.model_dump(),
            email_confirmation_required=email_confirmation_required,
        )


class TokenResponse(BaseModel):
    """OAuth2-compatible access token payload for login, refresh, OAuth, and SSO.

    Self-hosted HS256 login sets ``refresh_token`` to ``None`` (no external
    refresh-token store).

    Attributes:
        access_token: Bearer JWT for protected API routes.
        token_type: Always ``bearer`` for clients that expect OAuth2 shape.
        expires_in: Access-token lifetime in seconds (``>= 1``).
        refresh_token: Optional refresh token (always ``None`` for self-hosted HS256).
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(ge=1)
    refresh_token: str | None = None
