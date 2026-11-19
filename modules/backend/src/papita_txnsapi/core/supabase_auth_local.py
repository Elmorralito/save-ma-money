"""Local/B0 Supabase Auth helpers: Admin register and optional email auto-confirm.

Kept separate from :mod:`papita_txnsapi.core.supabase_auth` so the core Auth
client module stays under the pylint module-length budget while local DX can
grow (``AUTH_AUTO_CONFIRM_EMAIL``, Admin ``create_user`` without SMTP).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, cast

from supabase import Client
from supabase_auth.errors import AuthApiError, AuthError

from papita_txnsapi.core.supabase_auth import (
    SupabaseAuthResult,
    SupabaseSignUpProfile,
    create_supabase_admin_client,
    is_email_not_confirmed_error,
    is_invalid_credentials_error,
    maybe_auto_confirm_auth_email,
    supabase_sign_in,
    supabase_sign_up,
)

logger = logging.getLogger(__name__)


def _user_id_from_auth_user(user: Any) -> uuid.UUID:
    """Extract Auth subject UUID from an SDK user object or dict."""
    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    if user_id is None:
        raise ValueError("Supabase Auth user missing id")
    return uuid.UUID(str(user_id))


def _email_from_auth_user(user: Any, fallback: str = "") -> str:
    """Extract normalized email from an SDK user object or dict."""
    email = getattr(user, "email", None)
    if email is None and isinstance(user, dict):
        email = user.get("email")
    return str(email or fallback).strip().lower()


def _signup_user_metadata(profile: SupabaseSignUpProfile) -> dict[str, Any]:
    """Build Auth ``user_metadata`` from an optional signup profile."""
    provider_value = getattr(profile.provider, "value", profile.provider)
    metadata: dict[str, Any] = {"provider": provider_value}
    if profile.username:
        metadata["username"] = profile.username
    if profile.display_name:
        metadata["display_name"] = profile.display_name
        metadata["full_name"] = profile.display_name
    if profile.phone:
        metadata["phone"] = profile.phone
    return metadata


def _result_from_admin_user_response(response: Any, *, email_fallback: str = "") -> SupabaseAuthResult:
    """Normalize Admin ``create_user`` / ``get_user_by_id`` style responses (no session)."""
    user = getattr(response, "user", None)
    if user is None and getattr(response, "id", None) is not None:
        user = response
    if user is None:
        raise ValueError("Supabase Auth admin response missing user")
    return SupabaseAuthResult(
        user_id=_user_id_from_auth_user(user),
        email=_email_from_auth_user(user, email_fallback),
        access_token=None,
        refresh_token=None,
        expires_in=None,
        raw=response,
    )


def supabase_admin_create_user(
    *,
    supabase_url: str,
    service_role_key: str,
    email: str,
    password: str,
    profile: SupabaseSignUpProfile | None = None,
    client: Client | None = None,
) -> SupabaseAuthResult:
    """Create a confirmed Auth user via Admin API (does **not** send email).

    Prefer this for local/B0 registration when ``AUTH_AUTO_CONFIRM_EMAIL`` is on —
    anon ``sign_up`` triggers confirmation emails and hits Supabase SMTP rate limits.

    Args:
        supabase_url: Project URL.
        service_role_key: Service role key (server-only).
        email: User email.
        password: Plain-text password.
        profile: Optional username / display metadata.
        client: Optional pre-built admin client (tests).

    Returns:
        Normalized Auth result without session tokens (caller signs in next).

    Raises:
        ValueError: Missing service role key.
        AuthApiError: Supabase Auth rejected the create.
        AuthError: Non-API Auth failure from the SDK.
    """
    if not service_role_key or not str(service_role_key).strip():
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required for admin create_user")
    sign_up_profile = profile or SupabaseSignUpProfile()
    admin_client = client or create_supabase_admin_client(
        supabase_url=supabase_url, service_role_key=service_role_key.strip()
    )
    metadata = _signup_user_metadata(sign_up_profile)
    payload: dict[str, Any] = {
        "email": email,
        "password": password,
        "email_confirm": True,
        "user_metadata": metadata,
    }
    if sign_up_profile.phone:
        payload["phone"] = sign_up_profile.phone
        payload["phone_confirm"] = True
    response = admin_client.auth.admin.create_user(cast(Any, payload))
    result = _result_from_admin_user_response(response, email_fallback=email)
    logger.info("Supabase admin create_user ok user_id=%s (no confirmation email)", result.user_id)
    return result


@dataclass(frozen=True, slots=True)
class SupabaseClientOverrides:
    """Optional pre-built Supabase clients for tests (keeps register kwargs ≤ 8)."""

    anon: Client | None = None
    admin: Client | None = None


def supabase_register_user(
    *,
    supabase_url: str,
    anon_key: str,
    email: str,
    password: str,
    profile: SupabaseSignUpProfile | None = None,
    service_role_key: str | None = None,
    prefer_admin_create: bool = False,
    clients: SupabaseClientOverrides | None = None,
) -> SupabaseAuthResult:
    """Register via Admin ``create_user`` when preferred, else anon ``sign_up``.

    Admin create marks email confirmed and skips SMTP — avoids
    ``over_email_send_rate_limit`` during local smoke when Confirm email is on.

    Args:
        supabase_url: Project URL.
        anon_key: Anon key (``sign_up`` path).
        email: User email.
        password: Plain-text password.
        profile: Optional Auth metadata.
        service_role_key: Required for Admin create path.
        prefer_admin_create: When True and service role is set, use Admin create.
        clients: Optional anon/admin client overrides (tests).

    Returns:
        Normalized Auth result from the chosen create path.
    """
    overrides = clients or SupabaseClientOverrides()
    if prefer_admin_create and service_role_key and str(service_role_key).strip():
        return supabase_admin_create_user(
            supabase_url=supabase_url,
            service_role_key=service_role_key,
            email=email,
            password=password,
            profile=profile,
            client=overrides.admin,
        )
    return supabase_sign_up(
        supabase_url=supabase_url,
        anon_key=anon_key,
        email=email,
        password=password,
        profile=profile,
        client=overrides.anon,
    )


def _auth_user_email_unconfirmed(
    *,
    supabase_url: str,
    service_role_key: str,
    user_id: uuid.UUID | str,
) -> bool:
    """Return True when Admin Auth shows the subject has no confirmed email."""
    try:
        admin = create_supabase_admin_client(supabase_url=supabase_url, service_role_key=service_role_key.strip())
        response = admin.auth.admin.get_user_by_id(str(user_id))
        user = getattr(response, "user", response)
        confirmed_at = getattr(user, "email_confirmed_at", None)
        if confirmed_at is None and isinstance(user, dict):
            confirmed_at = user.get("email_confirmed_at")
        return confirmed_at is None
    except (AuthApiError, AuthError, ValueError, TypeError) as exc:
        logger.debug("Could not inspect Auth email confirmation for %s: %s", user_id, exc)
        return False


def supabase_sign_in_with_optional_auto_confirm(
    *,
    supabase_url: str,
    anon_key: str,
    email: str,
    password: str,
    service_role_key: str | None,
    auth_user_id: uuid.UUID | str | None,
    auto_confirm: bool,
    client: Client | None = None,
) -> SupabaseAuthResult:
    """Sign in; when login fails and Auth email is unconfirmed, Admin-confirm then retry.

    Supabase often maps unconfirmed users to ``invalid_credentials`` (not
    ``email_not_confirmed``). We only Admin-confirm after verifying
    ``email_confirmed_at`` is null — wrong passwords do not trigger confirm.

    Args:
        supabase_url: Project URL.
        anon_key: Anon key.
        email: Login email.
        password: Plain-text password.
        service_role_key: Service role for Admin confirm (optional).
        auth_user_id: Known Auth subject (e.g. Papita ``users.id``) to confirm.
        auto_confirm: Whether local auto-confirm is enabled.
        client: Optional pre-built anon client (tests).

    Returns:
        Normalized Auth result including access and refresh tokens.

    Raises:
        AuthApiError / AuthError / ValueError: From :func:`supabase_sign_in` when
            confirm is skipped or retry still fails.
    """
    try:
        return supabase_sign_in(
            supabase_url=supabase_url,
            anon_key=anon_key,
            email=email,
            password=password,
            client=client,
        )
    except (AuthApiError, AuthError) as exc:
        if not auto_confirm or auth_user_id is None or not service_role_key or not str(service_role_key).strip():
            raise
        if not (is_email_not_confirmed_error(exc) or is_invalid_credentials_error(exc)):
            raise
        if not _auth_user_email_unconfirmed(
            supabase_url=supabase_url,
            service_role_key=service_role_key,
            user_id=auth_user_id,
        ):
            raise
        if not maybe_auto_confirm_auth_email(
            supabase_url=supabase_url,
            service_role_key=service_role_key,
            user_id=auth_user_id,
            enabled=True,
        ):
            raise
        return supabase_sign_in(
            supabase_url=supabase_url,
            anon_key=anon_key,
            email=email,
            password=password,
            client=client,
        )


def register_requires_email_confirmation(
    *,
    access_token: str | None,
    auto_confirm_enabled: bool,
) -> bool:
    """Return whether register should signal pending email confirmation (PPT-068).

    Admin auto-confirm / local DX creates confirmed users without a session; those
    must not flip the SPA into check-email UX. Confirm-required anon ``sign_up``
    (no access token, auto-confirm off) must.

    Args:
        access_token: Session access token from Auth, if any.
        auto_confirm_enabled: ``settings.should_auto_confirm_email()``.

    Returns:
        True when the client should show pending confirmation UX.
    """
    return access_token is None and not auto_confirm_enabled


def elevate_unconfirmed_login_detail(
    *,
    supabase_url: str,
    service_role_key: str | None,
    auth_user_id: uuid.UUID | str | None,
    auto_confirm: bool,
    http_status: int,
    detail: str,
) -> tuple[int, str]:
    """Map opaque Auth login failures to ``Email not confirmed`` when apt (PPT-068).

    Supabase often returns ``invalid_credentials`` for unconfirmed users. When
    auto-confirm is off (staging/prod) and Admin Auth shows ``email_confirmed_at``
    null for a known subject, elevate to the allowlisted confirm detail.

    Args:
        supabase_url: Project URL.
        service_role_key: Service role for Admin lookup (optional).
        auth_user_id: Known Auth subject (Papita row id) when available.
        auto_confirm: Whether local Admin auto-confirm is enabled.
        http_status: Status from :func:`classify_supabase_auth_error`.
        detail: Detail from classification.

    Returns:
        Possibly updated ``(http_status, detail)``.
    """
    if detail == "Email not confirmed":
        return http_status, detail
    if auto_confirm or auth_user_id is None:
        return http_status, detail
    if http_status not in {400, 401}:
        return http_status, detail
    if not service_role_key or not str(service_role_key).strip():
        return http_status, detail
    if _auth_user_email_unconfirmed(
        supabase_url=supabase_url,
        service_role_key=service_role_key,
        user_id=auth_user_id,
    ):
        return 401, "Email not confirmed"
    return http_status, detail


__all__ = [
    "SupabaseClientOverrides",
    "elevate_unconfirmed_login_detail",
    "register_requires_email_confirmation",
    "supabase_admin_create_user",
    "supabase_register_user",
    "supabase_sign_in_with_optional_auto_confirm",
]
