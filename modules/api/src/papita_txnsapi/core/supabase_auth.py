"""Supabase Auth HTTP helpers for optional register/login pass-through.

When ``AUTH_PROVIDER=supabase``, clients should prefer talking to Supabase Auth
directly. These helpers enable a thin API proxy so existing OpenAPI flows and
smoke tests can still ``POST /auth/login`` and ``POST /auth/register``.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def _auth_headers(anon_key: str) -> dict[str, str]:
    return {
        "apikey": anon_key,
        "Authorization": f"Bearer {anon_key}",
        "Content-Type": "application/json",
    }


def supabase_sign_up(
    *,
    supabase_url: str,
    anon_key: str,
    email: str,
    password: str,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """Create a user via Supabase Auth ``/auth/v1/signup``.

    Args:
        supabase_url: Project URL (no trailing slash).
        anon_key: Supabase anon (publishable) key.
        email: User email.
        password: Plain-text password.
        timeout: HTTP timeout seconds.

    Returns:
        Parsed JSON body from Supabase.

    Raises:
        httpx.HTTPStatusError: When Supabase returns a non-success status.
        httpx.HTTPError: On transport failures.
    """
    url = f"{supabase_url.rstrip('/')}/auth/v1/signup"
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            url,
            headers=_auth_headers(anon_key),
            json={"email": email, "password": password},
        )
        response.raise_for_status()
        return response.json()


def supabase_password_grant(
    *,
    supabase_url: str,
    anon_key: str,
    email: str,
    password: str,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """Exchange email/password for tokens via Supabase Auth password grant.

    Args:
        supabase_url: Project URL (no trailing slash).
        anon_key: Supabase anon (publishable) key.
        email: Login email (OAuth2 ``username`` when it contains ``@``).
        password: Plain-text password.
        timeout: HTTP timeout seconds.

    Returns:
        Parsed JSON including ``access_token`` / ``expires_in``.

    Raises:
        httpx.HTTPStatusError: When credentials are rejected or Auth errors.
        httpx.HTTPError: On transport failures.
    """
    url = f"{supabase_url.rstrip('/')}/auth/v1/token"
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            url,
            headers=_auth_headers(anon_key),
            params={"grant_type": "password"},
            json={"email": email, "password": password},
        )
        response.raise_for_status()
        return response.json()
