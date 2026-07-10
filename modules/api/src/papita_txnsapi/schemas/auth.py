"""Authentication request and response schemas.

Defines JSON bodies for registration and token issuance plus the public user
profile returned by auth endpoints. Passwords are accepted on write paths only
and are never serialized on ``UserResponse``.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from papita_txnsmodel.access.users.dto import UsersDTO


class RegisterRequest(BaseModel):
    """JSON body for ``POST /auth/register``.

    Attributes:
        username: Unique login name; 6–255 characters.
        email: Contact email; 5–255 characters.
        password: Plain-text password for hashing by the auth service; 8–128 characters.
    """

    username: str = Field(min_length=6, max_length=255)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    """Public user profile — never includes password.

    Attributes:
        id: Stable user identifier (UUID).
        username: Login name.
        email: Registered email address.
        created_at: UTC timestamp when the user record was created.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    created_at: datetime

    @classmethod
    def from_dto(cls, user: UsersDTO) -> UserResponse:
        """Build an API response from a model ``UsersDTO``.

        Args:
            user: Persisted user row from the model layer.

        Returns:
            Sanitized profile suitable for JSON serialization.

        Raises:
            ValueError: When ``user.created_at`` is missing.
        """
        if user.created_at is None:
            raise ValueError("User record is missing created_at")
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at,
        )


class TokenResponse(BaseModel):
    """OAuth2-compatible access token payload.

    Attributes:
        access_token: Signed JWT issued by ``AuthSecurityManager``.
        token_type: Token scheme; always ``bearer`` for this API.
        expires_in: Token lifetime in seconds (must be positive).
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(ge=1)
