"""Request/response schemas for ``/api/v1/bff/auth/*`` (PPT-049).

BFF responses never include access or refresh JWTs — those stay server-side in
the session binding store. The SPA receives only the public user profile and a
CSRF token for mutation headers.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from papita_txnsapi.schemas.auth import RegisterRequest, ResendConfirmationRequest, UserResponse


class BffLoginRequest(BaseModel):
    """JSON body for ``POST /bff/auth/login``.

    Attributes:
        email: Canonical login identity (OAuth2 ``username`` field for token login).
        password: Plain-text password (never logged or echoed).
    """

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)


class BffRegisterRequest(RegisterRequest):
    """JSON body for ``POST /bff/auth/register`` (same fields as ``/auth/register``)."""


class BffResendConfirmationRequest(ResendConfirmationRequest):
    """JSON body for ``POST /bff/auth/resend-confirmation`` (same fields as Bearer twin)."""


class BffSessionResponse(BaseModel):
    """Public BFF session probe / login response (no JWTs).

    Attributes:
        authenticated: Whether a valid session cookie was resolved.
        user: Public profile when authenticated.
        csrf_token: Value for ``X-Papita-CSRF`` on cookie-authenticated mutations.
        session_backend: ``redis`` or ``memory`` (ops visibility; not a secret).
        access_expires_at: Unix timestamp (seconds) when the server-held access JWT
            expires. Never includes the JWT itself — SPA countdown / refresh UX only.
    """

    model_config = ConfigDict(extra="forbid")

    authenticated: bool
    user: UserResponse | None = None
    csrf_token: str | None = None
    session_backend: str | None = None
    access_expires_at: float | None = None
