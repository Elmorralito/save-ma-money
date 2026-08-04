"""Authentication request and response schemas for ``/api/v1/auth/*``.

Defines JSON bodies for registration, Supabase session refresh/logout, OAuth
(PKCE) start/callback and SSO token handoff, plus the public user profile and
OAuth2-compatible token payload returned by auth endpoints.

Passwords are accepted on write paths only and are never serialized on
``UserResponse``. Email is the canonical client login identity;
``users.username`` is a derived handle for the schema unique constraint.
``AUTH_PROVIDER=local`` (tests) uses HS256 tokens; production uses Supabase Auth.

Key exports:
    AuthProviderType: Wire literal for credential store (``supabase`` | ``local``).
    RegisterRequest: ``POST /auth/register`` body.
    RefreshRequest / LogoutRequest: Session rotation and revoke bodies.
    OAuthStartResponse / OAuthCodeExchangeRequest / SsoSessionRequest: OAuth/SSO.
    UserResponse / TokenResponse: Public profile and OAuth2 token envelopes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import ProviderType

# Wire label for where credentials live: Supabase Auth vs local test hashes.
AuthProviderType = Literal["supabase", "local"]


class RegisterRequest(BaseModel):
    """JSON body for ``POST /auth/register``.

    Creates an Auth user (Supabase) or local password row, then provisions
    ``papita_transactions.users``. Password signup is email-only; Google/GitHub
    must use the OAuth/SSO routes.

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
    """JSON body for ``POST /auth/refresh`` (Supabase Auth session rotation).

    Local Auth mode does not accept this body meaningfully (route returns 501).

    Attributes:
        refresh_token: Opaque Supabase refresh token from login/OAuth/SSO.
    """

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1, max_length=4096)


class LogoutRequest(BaseModel):
    """JSON body for ``POST /auth/logout`` (session revoke).

    Under Supabase, ``refresh_token`` is required for GoTrue ``sign_out``.
    ``access_token`` may also be supplied via ``Authorization: Bearer`` on the
    route when omitted here. When Redis is enabled, the access JWT is denylisted.

    Attributes:
        refresh_token: Refresh token to invalidate at Supabase Auth.
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
        url: Supabase / IdP authorize URL including the PKCE challenge.
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
    """JSON body for ``POST /auth/oauth/callback`` (Supabase PKCE code exchange).

    Completes OAuth when the client holds the authorization ``code`` and the
    PKCE verifier from the authorize step. Prefer this over ``SsoSessionRequest``
    when the redirect yields a ``code``.

    Attributes:
        provider: OAuth provider (``google`` or ``github``).
        auth_code: Authorization ``code`` from the OAuth redirect query string.
        code_verifier: PKCE verifier from ``GET /auth/oauth/{provider}``.
        redirect_to: Optional redirect URI that must match the authorize step.
        display_name: Optional profile override when Auth metadata is incomplete.
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
    """JSON body for ``POST /auth/sso`` after client-side Supabase OAuth tokens.

    Use when the SPA already obtained an Auth session (e.g. fragment/hash flow).
    Prefer ``POST /auth/oauth/callback`` (authorization code + PKCE) when the
    redirect yields a ``code``.

    Attributes:
        provider: OAuth provider (``google`` or ``github``).
        access_token: Supabase access JWT from the OAuth session.
        refresh_token: Supabase refresh token from the OAuth session.
        display_name: Optional profile override when Auth metadata is incomplete.
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
    (email/Google/GitHub); ``auth_provider`` is where credentials are stored
    (``supabase`` vs local tests).

    Attributes:
        id: Tenant user id (Auth ``sub`` when ``auth_provider`` is ``supabase``).
        username: Unique handle (often derived from email).
        email: Canonical login email.
        display_name: Optional human-readable name.
        phone: Optional phone from Auth/profile.
        provider: Signup / identity channel (``ProviderType``).
        auth_provider: Credential store label (``supabase`` or ``local``).
        created_at: Row creation timestamp (required on the DTO).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    display_name: str | None = None
    phone: str | None = None
    provider: ProviderType = ProviderType.EMAIL
    auth_provider: AuthProviderType = "supabase"
    created_at: datetime

    @classmethod
    def from_dto(cls, user: UsersDTO) -> UserResponse:
        """Build an API response from a model ``UsersDTO``.

        Maps ``provider_type`` (including legacy ``phone`` → ``email``) and
        normalizes ``auth_provider`` to the wire literal. Any non-local
        ``auth_provider`` value is treated as ``supabase``.

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
        auth_provider: AuthProviderType = "local" if user.auth_provider == "local" else "supabase"
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

    When Supabase Confirm email is on and Admin auto-confirm is off, Auth may
    create the user without issuing a session. ``email_confirmation_required``
    tells the SPA to show check-email UX instead of prompting an immediate login.
    Local Auth and Admin auto-confirm paths leave the flag ``False``.
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

    Local login sets ``refresh_token`` to ``None``. Supabase paths populate both
    access and refresh tokens when Auth issues a session.

    Attributes:
        access_token: Bearer JWT for protected API routes.
        token_type: Always ``bearer`` for clients that expect OAuth2 shape.
        expires_in: Access-token lifetime in seconds (``>= 1``).
        refresh_token: Optional Supabase refresh token for rotation/logout.
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(ge=1)
    refresh_token: str | None = None
