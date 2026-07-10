"""Shared auth test helpers (not collected by pytest)."""

from __future__ import annotations

from datetime import datetime, timezone

from papita_txnsmodel.access.users.dto import UsersDTO

VALID_PASSWORD = "SecurePass1!"


def make_user(
    username: str = "johndoe",
    email: str = "john@example.local",
    *,
    active: bool = True,
    deleted_at: datetime | None = None,
) -> UsersDTO:
    """Build a valid UsersDTO for auth tests."""
    user = UsersDTO(username=username, email=email, password=VALID_PASSWORD)
    user.created_at = datetime.now(timezone.utc)
    user.active = active
    user.deleted_at = deleted_at
    return user
