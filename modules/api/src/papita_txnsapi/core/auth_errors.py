"""Allowlisted public Auth / provision error details (PPT-044 / PR-4).

Routers must not echo raw Supabase, GoTrue, or IdP exception text to clients.
Map known domain messages through these helpers; everything else becomes a
generic fallback.
"""

from __future__ import annotations

PUBLIC_AUTH_DETAILS = frozenset(
    {
        "Email already registered",
        "Username already registered",
        "User is inactive or deleted",
        "Auth subject is missing email",
        "Incorrect username or password",
        "Login requires email (OAuth2 username field)",
        "Too many authentication attempts. Try again later.",
        "Authentication request failed",
        "Missing OAuth authorization code",
        "Unsupported OAuth provider",
        "OAuth SSO requires AUTH_PROVIDER=supabase",
        "Missing OAuth PKCE cookie; restart with GET /auth/oauth/{provider}?follow=true",
        "Missing OAuth provider cookie; restart with GET /auth/oauth/{provider}?follow=true",
    }
)


def auth_error_detail(exc: Exception, *, fallback: str) -> str:
    """Return an allowlisted public Auth error detail (never raw provider text).

    Args:
        exc: Raised Auth or wrapper exception.
        fallback: Detail when the exception message is not allowlisted.

    Returns:
        Non-empty detail string suitable for ``HTTPException.detail``.
    """
    message = str(getattr(exc, "message", None) or exc or fallback).strip()
    if message in PUBLIC_AUTH_DETAILS:
        return message
    return fallback


def public_value_error_detail(exc: ValueError, *, fallback: str) -> str:
    """Map domain ``ValueError`` text to an allowlisted client detail.

    Args:
        exc: Raised during provision or Auth-adjacent validation.
        fallback: Detail when ``str(exc)`` is not allowlisted.

    Returns:
        Allowlisted message or ``fallback``.
    """
    message = str(exc).strip()
    if message in PUBLIC_AUTH_DETAILS:
        return message
    return fallback
