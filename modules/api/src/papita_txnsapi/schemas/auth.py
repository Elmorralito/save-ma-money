"""Authentication request and response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from papita_txnsmodel.access.users.dto import UsersDTO


class RegisterRequest(BaseModel):
    """JSON body for ``POST /auth/register``."""

    username: str = Field(min_length=6, max_length=255)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    """Public user profile — never includes password."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    created_at: datetime

    @classmethod
    def from_dto(cls, user: UsersDTO) -> UserResponse:
        """Build an API response from a model ``UsersDTO``."""
        if user.created_at is None:
            raise ValueError("User record is missing created_at")
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at,
        )


class TokenResponse(BaseModel):
    """OAuth2-compatible access token payload."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(ge=1)
