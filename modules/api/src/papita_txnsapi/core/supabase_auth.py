"""Supabase Auth helpers for register/login via the official Python client.

When ``AUTH_PROVIDER=supabase``, API ``/auth/register`` and ``/auth/login`` delegate
to Supabase Auth (``sign_up`` / ``sign_in_with_password``). JWT verification on
protected routes still uses JWKS in :mod:`papita_txnsapi.core.security`.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, cast

from supabase import Client, create_client
from supabase_auth.errors import AuthApiError, AuthError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SupabaseAuthResult:
    """Normalized Auth outcome for Papita register/login provisioning."""

    user_id: uuid.UUID
    email: str
    access_token: str | None = None
    expires_in: int | None = None
    raw: Any = None


def create_supabase_auth_client(*, supabase_url: str, anon_key: str) -> Client:
    """Build a Supabase client scoped for Auth API calls.

    Args:
        supabase_url: Project URL (e.g. ``https://xyz.supabase.co``).
        anon_key: Supabase anon (publishable) key.

    Returns:
        Configured ``supabase.Client``.
    """
    return create_client(supabase_url.rstrip("/"), anon_key)


def _user_id_from_auth_user(user: Any) -> uuid.UUID:
    raw_id = getattr(user, "id", None)
    if raw_id is None and isinstance(user, dict):
        raw_id = user.get("id")
    if raw_id is None:
        raise ValueError("Supabase Auth response missing user id")
    return uuid.UUID(str(raw_id))


def _email_from_auth_user(user: Any, fallback: str) -> str:
    email = getattr(user, "email", None)
    if email is None and isinstance(user, dict):
        email = user.get("email")
    return str(email or fallback).strip().lower()


def _session_token_fields(session: Any) -> tuple[str | None, int | None]:
    if session is None:
        return None, None
    access_token = getattr(session, "access_token", None)
    if access_token is None and isinstance(session, dict):
        access_token = session.get("access_token")
    expires_in = getattr(session, "expires_in", None)
    if expires_in is None and isinstance(session, dict):
        expires_in = session.get("expires_in")
    if expires_in is not None:
        expires_in = int(expires_in)
    return (str(access_token) if access_token else None), expires_in


def supabase_sign_up(
    *,
    supabase_url: str,
    anon_key: str,
    email: str,
    password: str,
    username: str | None = None,
    client: Client | None = None,
) -> SupabaseAuthResult:
    """Create a user via Supabase Auth ``sign_up``.

    Args:
        supabase_url: Project URL.
        anon_key: Anon key.
        email: User email.
        password: Plain-text password.
        username: Stored in Auth ``user_metadata`` when provided.
        client: Optional pre-built client (tests).

    Returns:
        Normalized Auth result (session may be ``None`` when email confirm is on).

    Raises:
        AuthApiError / AuthError: Supabase Auth rejected the signup.
        ValueError: Response missing user id.
    """
    auth_client = client or create_supabase_auth_client(supabase_url=supabase_url, anon_key=anon_key)
    payload: dict[str, Any] = {"email": email, "password": password}
    if username:
        payload["options"] = {"data": {"username": username}}
    response = auth_client.auth.sign_up(cast(Any, payload))
    user = getattr(response, "user", None)
    if user is None:
        raise ValueError("Supabase Auth signup returned no user")
    access_token, expires_in = _session_token_fields(getattr(response, "session", None))
    result = SupabaseAuthResult(
        user_id=_user_id_from_auth_user(user),
        email=_email_from_auth_user(user, email),
        access_token=access_token,
        expires_in=expires_in,
        raw=response,
    )
    logger.debug("Supabase sign_up ok user_id=%s has_session=%s", result.user_id, access_token is not None)
    return result


def supabase_sign_in(
    *,
    supabase_url: str,
    anon_key: str,
    email: str,
    password: str,
    client: Client | None = None,
) -> SupabaseAuthResult:
    """Sign in via Supabase Auth ``sign_in_with_password``.

    Args:
        supabase_url: Project URL.
        anon_key: Anon key.
        email: Login email.
        password: Plain-text password.
        client: Optional pre-built client (tests).

    Returns:
        Normalized Auth result including access token.

    Raises:
        AuthApiError / AuthError: Invalid credentials or Auth failure.
        ValueError: Response missing user id or access token.
    """
    auth_client = client or create_supabase_auth_client(supabase_url=supabase_url, anon_key=anon_key)
    response = auth_client.auth.sign_in_with_password({"email": email, "password": password})
    user = getattr(response, "user", None)
    if user is None:
        raise ValueError("Supabase Auth login returned no user")
    access_token, expires_in = _session_token_fields(getattr(response, "session", None))
    if not access_token:
        raise ValueError("Supabase Auth login response missing access_token")
    result = SupabaseAuthResult(
        user_id=_user_id_from_auth_user(user),
        email=_email_from_auth_user(user, email),
        access_token=access_token,
        expires_in=expires_in,
        raw=response,
    )
    logger.debug("Supabase sign_in ok user_id=%s", result.user_id)
    return result


__all__ = [
    "AuthApiError",
    "AuthError",
    "SupabaseAuthResult",
    "create_supabase_auth_client",
    "supabase_sign_in",
    "supabase_sign_up",
]
