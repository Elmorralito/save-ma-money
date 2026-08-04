"""Supabase Auth client helpers for register, login, OAuth, and sessions.

When ``AUTH_PROVIDER=supabase``, API ``/auth/*`` routes delegate credential and
session work to GoTrue through the official Supabase Python client. This module
normalizes SDK responses into Papita DTOs, maps Auth errors to stable HTTP
status/detail pairs, and provides Admin helpers for orphan Auth-user cleanup.

Covered Auth operations:
    * Password — ``sign_up``, ``sign_in_with_password``, ``refresh_session``, ``sign_out``
    * OAuth PKCE — ``sign_in_with_oauth``, ``exchange_code_for_session``
    * SSO handoff — ``set_session`` plus user lookup for email backfill
    * Admin orphan cleanup — ``admin.delete_user`` / ``admin.get_user_by_id``

JWT verification on protected routes is **not** performed here; that stays in
:mod:`papita_txnsapi.core.security` (JWKS). Anon and service-role clients are
process-cached by ``(url, key)`` under a lock. Call
:func:`clear_supabase_client_cache` in tests or after credential rotation.

Key exports:
    SupabaseAuthResult: Normalized Auth outcome for register/login/refresh/OAuth.
    SupabaseOAuthStart: Authorize URL plus PKCE verifier for OAuth start.
    SupabaseSignUpProfile: Optional Auth ``user_metadata`` / phone for ``sign_up``.
    create_supabase_auth_client / create_supabase_admin_client: Cached SDK clients.
    classify_supabase_auth_error: Map Auth exceptions to HTTP status + detail.
    supabase_sign_up / supabase_sign_in / supabase_refresh_session / supabase_sign_out.
    supabase_oauth_authorize_url / supabase_exchange_code_for_session.
    supabase_establish_session: Attach an existing client-held session.
    supabase_admin_delete_user / supabase_auth_user_created_recently: Orphan cleanup.
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from supabase import Client, create_client
from supabase_auth.errors import AuthApiError, AuthError

logger = logging.getLogger(__name__)

_CONFLICT_HINTS = ("already registered", "already been registered", "user already exists", "email_exists")
_ORPHAN_AUTH_MAX_AGE = timedelta(minutes=15)
_CLIENT_CACHE_LOCK = threading.Lock()
_AUTH_CLIENT_CACHE: dict[tuple[str, str], Client] = {}
_ADMIN_CLIENT_CACHE: dict[tuple[str, str], Client] = {}


@dataclass(frozen=True, slots=True)
class SupabaseAuthResult:
    """Normalized Auth outcome for Papita register, login, refresh, and OAuth.

    Routers map this into API token envelopes. Session fields may be absent when
    Supabase requires email confirmation before issuing tokens.

    Attributes:
        user_id: Auth subject UUID (``auth.users.id`` / JWT ``sub``).
        email: Lowercased email from Auth (may be empty until backfilled).
        access_token: Bearer JWT when a session was issued; ``None`` on confirm-only signup.
        refresh_token: Opaque refresh token when a session was issued.
        expires_in: Access-token lifetime in seconds when provided by Auth.
        raw: Underlying SDK response object for debugging and tests.
    """

    user_id: uuid.UUID
    email: str
    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = None
    raw: Any = None


@dataclass(frozen=True, slots=True)
class SupabaseOAuthStart:
    """Authorize URL plus PKCE verifier for a server-mediated OAuth start.

    The caller must persist ``code_verifier`` (response body or HttpOnly cookie)
    and present it to :func:`supabase_exchange_code_for_session` after redirect.

    Attributes:
        provider: Supabase provider id (e.g. ``google``, ``github``).
        url: Browser authorize URL including the PKCE challenge.
        code_verifier: PKCE verifier the client must send on code exchange.
    """

    provider: str
    url: str
    code_verifier: str


@dataclass(frozen=True, slots=True)
class SupabaseSignUpProfile:
    """Optional Auth ``user_metadata`` and phone fields for ``sign_up``.

    Does not create a Papita ``users`` row; callers still provision via
    ``UsersService.ensure_from_auth_subject`` after Auth succeeds.

    Attributes:
        username: Preferred handle stored in ``user_metadata.username``.
        display_name: Human name; also mirrored to ``full_name`` metadata.
        phone: Optional phone on the Auth user when provided.
        provider: Signup channel mirrored into ``user_metadata.provider``.
    """

    username: str | None = None
    display_name: str | None = None
    phone: str | None = None
    provider: str = "email"


def clear_supabase_client_cache() -> None:
    """Drop cached anon and admin clients (tests or credential rotation).

    Thread-safe. Subsequent ``create_supabase_*_client`` calls build fresh SDK
    clients for the next ``(url, key)`` lookup.

    Returns:
        None.
    """
    with _CLIENT_CACHE_LOCK:
        _AUTH_CLIENT_CACHE.clear()
        _ADMIN_CLIENT_CACHE.clear()


def create_supabase_auth_client(*, supabase_url: str, anon_key: str) -> Client:
    """Return a process-cached Supabase client for Auth API calls.

    Clients are keyed by ``(url, anon_key)`` with the URL trailing slash stripped
    so register/login/refresh/OAuth reuse one HTTP stack per credential pair.
    Thread-safe via a module lock.

    Args:
        supabase_url: Project URL (e.g. ``https://xyz.supabase.co``).
        anon_key: Supabase anon (publishable) key.

    Returns:
        Shared ``supabase.Client`` for the given URL and anon key.
    """
    key = (supabase_url.rstrip("/"), anon_key)
    with _CLIENT_CACHE_LOCK:
        cached = _AUTH_CLIENT_CACHE.get(key)
        if cached is not None:
            return cached
        client = create_client(key[0], anon_key)
        _AUTH_CLIENT_CACHE[key] = client
        return client


def create_supabase_admin_client(*, supabase_url: str, service_role_key: str) -> Client:
    """Return a process-cached Supabase client with the service-role key.

    Used only for Admin Auth operations (orphan delete and ``created_at``
    inspection). Never pass the service role key to browsers or anon Auth paths.

    Args:
        supabase_url: Project URL.
        service_role_key: Service role JWT (server-only).

    Returns:
        Shared ``supabase.Client`` with Admin Auth privileges for that key.
    """
    key = (supabase_url.rstrip("/"), service_role_key)
    with _CLIENT_CACHE_LOCK:
        cached = _ADMIN_CLIENT_CACHE.get(key)
        if cached is not None:
            return cached
        client = create_client(key[0], service_role_key)
        _ADMIN_CLIENT_CACHE[key] = client
        return client


def classify_supabase_auth_error(exc: Exception, *, fallback: str) -> tuple[int, str]:
    """Map a Supabase Auth exception to an HTTP status code and public detail.

    Recognizes conflict (email exists), rate limits, and invalid credentials so
    routers can return stable client messages. Other 4xx Auth statuses are passed
    through (422 coerced to 400). Unmapped or empty Auth messages become
    ``502`` with ``fallback``.

    Args:
        exc: Raised ``AuthApiError``, ``AuthError``, or a wrapping exception.
        fallback: Detail used when the Auth message is empty or unmapped (502).

    Returns:
        ``(http_status, detail)`` suitable for ``fastapi.HTTPException``.
    """
    message = str(getattr(exc, "message", None) or exc or fallback).strip() or fallback
    lower = message.lower()
    auth_status = getattr(exc, "status", None)
    code = str(getattr(exc, "code", "") or "").lower()

    if any(hint in lower for hint in _CONFLICT_HINTS) or code in {"email_exists", "user_already_exists"}:
        return 409, "Email already registered"
    if auth_status == 429 or code == "over_email_send_rate_limit":
        return 429, "Email rate limit exceeded. Wait a few minutes, or use local Admin register."
    if code == "email_not_confirmed" or "email not confirmed" in lower:
        return 401, "Email not confirmed"
    if auth_status in {401, 403} or code in {"invalid_credentials", "invalid_grant"}:
        return 401, "Incorrect username or password"
    # Do not pass through raw Auth/provider text (may leak internals).
    if auth_status is not None and 400 <= int(auth_status) < 500:
        mapped_status = int(auth_status) if int(auth_status) != 422 else 400
        return mapped_status, "Authentication request failed"
    return 502, fallback


def is_email_not_confirmed_error(exc: Exception) -> bool:
    """Return whether ``exc`` indicates the Auth user email is unconfirmed."""
    code = str(getattr(exc, "code", "") or "").lower()
    message = str(getattr(exc, "message", None) or exc or "").lower()
    return code == "email_not_confirmed" or "email not confirmed" in message


def is_invalid_credentials_error(exc: Exception) -> bool:
    """Return whether ``exc`` is a Supabase invalid-credentials Auth failure."""
    if is_email_not_confirmed_error(exc):
        return True
    code = str(getattr(exc, "code", "") or "").lower()
    status = getattr(exc, "status", None)
    message = str(getattr(exc, "message", None) or exc or "").lower()
    if code in {"invalid_credentials", "invalid_grant"}:
        return True
    return status in {401, 403} and "invalid" in message


def supabase_admin_confirm_email(
    *,
    supabase_url: str,
    service_role_key: str,
    user_id: uuid.UUID | str,
    client: Client | None = None,
) -> None:
    """Mark an Auth user's email confirmed via the Admin API.

    Used for local DX when Supabase "Confirm email" is enabled and signup does
    not issue a session. Requires the service-role key (never expose to browsers).

    Args:
        supabase_url: Project URL.
        service_role_key: Service role key.
        user_id: Auth subject to confirm.
        client: Optional pre-built admin client (tests).

    Raises:
        ValueError: Missing service role key or empty ``user_id``.
        AuthApiError: Admin update rejected by GoTrue.
        AuthError: Non-API Auth failure from the SDK.
    """
    if not service_role_key or not str(service_role_key).strip():
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required to confirm Auth emails")
    subject = str(user_id).strip()
    if not subject:
        raise ValueError("user_id is required")
    admin_client = client or create_supabase_admin_client(
        supabase_url=supabase_url, service_role_key=service_role_key.strip()
    )
    admin_client.auth.admin.update_user_by_id(subject, {"email_confirm": True})
    logger.info("Confirmed Supabase Auth email user_id=%s (auto-confirm)", subject)


def maybe_auto_confirm_auth_email(
    *,
    supabase_url: str,
    service_role_key: str | None,
    user_id: uuid.UUID | str,
    enabled: bool,
) -> bool:
    """Best-effort Admin email confirm when ``enabled`` and a service role exist.

    Args:
        supabase_url: Project URL.
        service_role_key: Service role key (or ``None`` / empty to skip).
        user_id: Auth subject.
        enabled: Gate from settings (``should_auto_confirm_email``).

    Returns:
        ``True`` when confirm succeeded; ``False`` when skipped or failed.
    """
    if not enabled:
        return False
    if not service_role_key or not str(service_role_key).strip():
        logger.warning(
            "Auth user %s has no session (email confirmation likely required) but "
            "SUPABASE_SERVICE_ROLE_KEY is unset — cannot auto-confirm",
            user_id,
        )
        return False
    try:
        supabase_admin_confirm_email(
            supabase_url=supabase_url,
            service_role_key=service_role_key,
            user_id=user_id,
        )
        return True
    except (AuthApiError, AuthError, ValueError) as exc:
        logger.warning("Auto-confirm Auth email failed for user_id=%s: %s", user_id, exc)
        return False


def supabase_admin_delete_user(
    *,
    supabase_url: str,
    service_role_key: str,
    user_id: uuid.UUID | str,
    client: Client | None = None,
) -> None:
    """Hard-delete an Auth user via the Admin API (orphan cleanup).

    Invoked after Papita provision fails so Auth does not keep a user without a
    matching local ``users`` row. Soft-delete is disabled.

    Args:
        supabase_url: Project URL.
        service_role_key: Service role key.
        user_id: Auth subject to delete.
        client: Optional pre-built admin client (tests).

    Returns:
        None.

    Raises:
        ValueError: Missing service role key or empty ``user_id``.
        AuthApiError: Admin delete rejected by GoTrue.
        AuthError: Non-API Auth failure from the SDK.
    """
    if not service_role_key or not str(service_role_key).strip():
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required to delete Auth users")
    subject = str(user_id).strip()
    if not subject:
        raise ValueError("user_id is required")
    admin_client = client or create_supabase_admin_client(
        supabase_url=supabase_url, service_role_key=service_role_key.strip()
    )
    admin_client.auth.admin.delete_user(subject, should_soft_delete=False)
    logger.info("Deleted Supabase Auth user user_id=%s (orphan cleanup)", subject)


def supabase_auth_user_created_recently(
    *,
    supabase_url: str,
    service_role_key: str,
    user_id: uuid.UUID | str,
    max_age: timedelta = _ORPHAN_AUTH_MAX_AGE,
    client: Client | None = None,
) -> bool:
    """Return whether an Auth user was created within ``max_age``.

    Scopes orphan cleanup on login so older Auth accounts are not deleted after
    a transient Papita provision failure. Failures consulting Admin Auth are
    treated as “not recent” (returns ``False``).

    Args:
        supabase_url: Project URL.
        service_role_key: Service role key.
        user_id: Auth subject.
        max_age: Recency window (default 15 minutes).
        client: Optional pre-built admin client (tests).

    Returns:
        ``True`` when ``created_at`` is within ``max_age``; ``False`` when the
        service role is missing, metadata is absent, or the Admin probe errors.
    """
    if not service_role_key or not str(service_role_key).strip():
        return False
    try:
        admin_client = client or create_supabase_admin_client(
            supabase_url=supabase_url, service_role_key=service_role_key.strip()
        )
        response = admin_client.auth.admin.get_user_by_id(str(user_id))
        user = getattr(response, "user", None) or response
        raw_created = getattr(user, "created_at", None)
        if raw_created is None and isinstance(user, dict):
            raw_created = user.get("created_at")
        if raw_created is None:
            return False
        if isinstance(raw_created, datetime):
            created_at = raw_created if raw_created.tzinfo else raw_created.replace(tzinfo=timezone.utc)
        else:
            created_at = datetime.fromisoformat(str(raw_created).replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - created_at <= max_age
    except Exception as exc:  # pragma: no cover - defensive Admin probe
        logger.warning("Could not inspect Auth user age for cleanup user_id=%s: %s", user_id, exc)
        return False


def _user_id_from_auth_user(user: Any) -> uuid.UUID:
    raw_id = getattr(user, "id", None)
    if raw_id is None and isinstance(user, dict):
        raw_id = user.get("id")
    if raw_id is None:
        raise ValueError("Supabase Auth response missing user id")
    return uuid.UUID(str(raw_id))


def _email_from_auth_user(user: Any, fallback: str = "") -> str:
    email = getattr(user, "email", None)
    if email is None and isinstance(user, dict):
        email = user.get("email")
    return str(email or fallback).strip().lower()


def _session_token_fields(session: Any) -> tuple[str | None, str | None, int | None]:
    if session is None:
        return None, None, None
    access_token = getattr(session, "access_token", None)
    if access_token is None and isinstance(session, dict):
        access_token = session.get("access_token")
    refresh_token = getattr(session, "refresh_token", None)
    if refresh_token is None and isinstance(session, dict):
        refresh_token = session.get("refresh_token")
    expires_in = getattr(session, "expires_in", None)
    if expires_in is None and isinstance(session, dict):
        expires_in = session.get("expires_in")
    if expires_in is not None:
        expires_in = int(expires_in)
    return (
        (str(access_token) if access_token else None),
        (str(refresh_token) if refresh_token else None),
        expires_in,
    )


def _result_from_auth_response(response: Any, *, email_fallback: str = "") -> SupabaseAuthResult:
    user = getattr(response, "user", None)
    session = getattr(response, "session", None)
    if user is None and session is not None:
        user = getattr(session, "user", None)
    if user is None:
        raise ValueError("Supabase Auth response missing user")
    access_token, refresh_token, expires_in = _session_token_fields(session)
    return SupabaseAuthResult(
        user_id=_user_id_from_auth_user(user),
        email=_email_from_auth_user(user, email_fallback),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        raw=response,
    )


def _signup_user_metadata(profile: SupabaseSignUpProfile) -> dict[str, Any]:
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


def supabase_sign_up(
    *,
    supabase_url: str,
    anon_key: str,
    email: str,
    password: str,
    profile: SupabaseSignUpProfile | None = None,
    client: Client | None = None,
) -> SupabaseAuthResult:
    """Create a user via Supabase Auth ``sign_up``.

    Stores optional profile fields on Auth ``user_metadata`` (and phone on the
    Auth user when set). Does not create the Papita ``users`` row — callers must
    call ``UsersService.ensure_from_auth_subject``.

    Args:
        supabase_url: Project URL.
        anon_key: Anon key.
        email: User email.
        password: Plain-text password.
        profile: Optional username, display_name, phone, and provider metadata.
        client: Optional pre-built client (tests).

    Returns:
        Normalized Auth result. Session tokens may be ``None`` when email
        confirmation is required before Auth issues a session.

    Raises:
        AuthApiError: Supabase Auth rejected the signup (API error).
        AuthError: Non-API Auth failure from the SDK.
        ValueError: Response missing user id.
    """
    sign_up_profile = profile or SupabaseSignUpProfile()
    auth_client = client or create_supabase_auth_client(supabase_url=supabase_url, anon_key=anon_key)
    metadata = _signup_user_metadata(sign_up_profile)
    payload: dict[str, Any] = {"email": email, "password": password, "options": {"data": metadata}}
    if sign_up_profile.phone:
        payload["phone"] = sign_up_profile.phone
    response = auth_client.auth.sign_up(cast(Any, payload))
    result = _result_from_auth_response(response, email_fallback=email)
    logger.debug(
        "Supabase sign_up ok user_id=%s has_session=%s",
        result.user_id,
        result.access_token is not None,
    )
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
        Normalized Auth result including access and refresh tokens.

    Raises:
        AuthApiError: Invalid credentials or Auth API failure.
        AuthError: Non-API Auth failure from the SDK.
        ValueError: Response missing user id or access token.
    """
    auth_client = client or create_supabase_auth_client(supabase_url=supabase_url, anon_key=anon_key)
    response = auth_client.auth.sign_in_with_password({"email": email, "password": password})
    result = _result_from_auth_response(response, email_fallback=email)
    if not result.access_token:
        raise ValueError("Supabase Auth login response missing access_token")
    logger.debug("Supabase sign_in ok user_id=%s", result.user_id)
    return result


def supabase_refresh_session(
    *,
    supabase_url: str,
    anon_key: str,
    refresh_token: str,
    client: Client | None = None,
) -> SupabaseAuthResult:
    """Rotate session tokens via Supabase Auth ``refresh_session``.

    Args:
        supabase_url: Project URL.
        anon_key: Anon key.
        refresh_token: Current Supabase refresh token.
        client: Optional pre-built client (tests).

    Returns:
        New access/refresh pair and user id.

    Raises:
        AuthApiError: Refresh token rejected or expired.
        AuthError: Non-API Auth failure from the SDK.
        ValueError: Empty ``refresh_token`` or response missing access token.
    """
    if not refresh_token or not refresh_token.strip():
        raise ValueError("refresh_token is required")
    auth_client = client or create_supabase_auth_client(supabase_url=supabase_url, anon_key=anon_key)
    response = auth_client.auth.refresh_session(refresh_token.strip())
    result = _result_from_auth_response(response)
    if not result.access_token:
        raise ValueError("Supabase Auth refresh response missing access_token")
    logger.debug("Supabase refresh ok user_id=%s", result.user_id)
    return result


def supabase_sign_out(
    *,
    supabase_url: str,
    anon_key: str,
    access_token: str,
    refresh_token: str,
    scope: str = "global",
    client: Client | None = None,
) -> None:
    """Revoke the Supabase session via ``set_session`` then ``sign_out``.

    Args:
        supabase_url: Project URL.
        anon_key: Anon key.
        access_token: Current access JWT.
        refresh_token: Current refresh token (revoked server-side when possible).
        scope: Sign-out scope passed to GoTrue (``global`` or ``local``).
        client: Optional pre-built client (tests).

    Returns:
        None.

    Raises:
        AuthApiError: Auth rejected the sign-out (API error).
        AuthError: Non-API Auth failure from the SDK.
        ValueError: Missing tokens, or ``set_session`` failed on a malformed JWT.
    """
    if not access_token or not access_token.strip():
        raise ValueError("access_token is required for logout")
    if not refresh_token or not refresh_token.strip():
        raise ValueError("refresh_token is required for logout")
    auth_client = client or create_supabase_auth_client(supabase_url=supabase_url, anon_key=anon_key)
    try:
        auth_client.auth.set_session(access_token.strip(), refresh_token.strip())
        auth_client.auth.sign_out(cast(Any, {"scope": scope}))
    except (AuthApiError, AuthError):
        raise
    except Exception as exc:  # pragma: no cover - defensive against malformed JWTs
        raise ValueError(f"Invalid access_token for logout: {exc}") from exc
    logger.debug("Supabase sign_out ok scope=%s", scope)


def supabase_oauth_authorize_url(
    *,
    supabase_url: str,
    anon_key: str,
    provider: str = "google",
    redirect_to: str | None = None,
    scopes: str | None = None,
    client: Client | None = None,
) -> SupabaseOAuthStart:
    """Start Supabase OAuth (PKCE) and return the authorize URL plus verifier.

    Uses ``sign_in_with_oauth`` / GoTrue authorize with ``code_challenge``. The
    SDK stores the PKCE verifier in client storage; this helper reads it back so
    the API can return it or set an HttpOnly cookie. The caller must present
    ``code_verifier`` later to :func:`supabase_exchange_code_for_session`.

    Args:
        supabase_url: Project URL.
        anon_key: Anon key.
        provider: Auth provider id (e.g. ``google``, ``github``).
        redirect_to: Browser redirect after OAuth (must be allowlisted in Supabase).
        scopes: Optional space-delimited OAuth scopes.
        client: Optional pre-built client (tests).

    Returns:
        ``SupabaseOAuthStart`` with authorize URL and PKCE ``code_verifier``.

    Raises:
        AuthApiError: Auth rejected the OAuth start (API error).
        AuthError: Non-API Auth failure from the SDK.
        ValueError: Response missing URL or PKCE verifier in client storage.
    """
    auth_client = client or create_supabase_auth_client(supabase_url=supabase_url, anon_key=anon_key)
    options: dict[str, Any] = {}
    if redirect_to:
        options["redirect_to"] = redirect_to
    if scopes:
        options["scopes"] = scopes
    credentials: dict[str, Any] = {"provider": provider}
    if options:
        credentials["options"] = options
    response = auth_client.auth.sign_in_with_oauth(cast(Any, credentials))
    url = getattr(response, "url", None)
    if not url:
        raise ValueError("Supabase OAuth response missing authorize url")
    storage = getattr(auth_client.auth, "_storage", None)
    storage_key = getattr(auth_client.auth, "_storage_key", "supabase.auth.token")
    code_verifier = None
    if storage is not None:
        code_verifier = storage.get_item(f"{storage_key}-code-verifier")
    if not code_verifier:
        raise ValueError("Supabase OAuth PKCE code_verifier missing from client storage")
    return SupabaseOAuthStart(provider=provider, url=str(url), code_verifier=str(code_verifier))


def supabase_exchange_code_for_session(
    *,
    supabase_url: str,
    anon_key: str,
    auth_code: str,
    code_verifier: str,
    redirect_to: str | None = None,
    client: Client | None = None,
) -> SupabaseAuthResult:
    """Complete Supabase OAuth via ``exchange_code_for_session`` (PKCE).

    When the session response omits email, falls back to ``get_user`` with the
    new access token so Papita provision always receives a login identity.

    Args:
        supabase_url: Project URL.
        anon_key: Anon key.
        auth_code: Authorization ``code`` query param from the OAuth redirect.
        code_verifier: PKCE verifier from :func:`supabase_oauth_authorize_url`.
        redirect_to: Optional redirect URI that was used to start OAuth.
        client: Optional pre-built client (tests).

    Returns:
        Normalized Auth result with access/refresh tokens and email.

    Raises:
        AuthApiError: Code or verifier rejected by Auth.
        AuthError: Non-API Auth failure from the SDK.
        ValueError: Missing inputs or response missing session/email.
    """
    if not auth_code or not auth_code.strip():
        raise ValueError("auth_code is required")
    if not code_verifier or not code_verifier.strip():
        raise ValueError("code_verifier is required")
    auth_client = client or create_supabase_auth_client(supabase_url=supabase_url, anon_key=anon_key)
    params: dict[str, Any] = {
        "auth_code": auth_code.strip(),
        "code_verifier": code_verifier.strip(),
    }
    if redirect_to:
        params["redirect_to"] = redirect_to
    response = auth_client.auth.exchange_code_for_session(cast(Any, params))
    result = _result_from_auth_response(response)
    if not result.access_token:
        raise ValueError("Supabase OAuth code exchange missing access_token")
    if not result.email:
        user_resp = auth_client.auth.get_user(result.access_token)
        user = getattr(user_resp, "user", None) or user_resp
        email = _email_from_auth_user(user)
        if not email:
            raise ValueError("Supabase OAuth session missing email")
        result = SupabaseAuthResult(
            user_id=_user_id_from_auth_user(user) if getattr(user, "id", None) else result.user_id,
            email=email,
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            expires_in=result.expires_in,
            raw=response,
        )
    logger.debug("Supabase OAuth code exchange ok user_id=%s", result.user_id)
    return result


def supabase_establish_session(
    *,
    supabase_url: str,
    anon_key: str,
    access_token: str,
    refresh_token: str,
    client: Client | None = None,
) -> SupabaseAuthResult:
    """Attach an existing Supabase session and return the authenticated user.

    Used when the client already holds Auth tokens (e.g. after a client-side
    OAuth hash/fragment flow). Prefer :func:`supabase_exchange_code_for_session`
    when the app receives an authorization ``code``.

    Args:
        supabase_url: Project URL.
        anon_key: Anon key.
        access_token: Supabase access JWT from OAuth.
        refresh_token: Supabase refresh token from OAuth.
        client: Optional pre-built client (tests).

    Returns:
        Normalized Auth result including tokens and email.

    Raises:
        AuthApiError: Session rejected by Auth.
        AuthError: Non-API Auth failure from the SDK.
        ValueError: Missing tokens or user email.
    """
    if not access_token or not access_token.strip():
        raise ValueError("access_token is required")
    if not refresh_token or not refresh_token.strip():
        raise ValueError("refresh_token is required")
    auth_client = client or create_supabase_auth_client(supabase_url=supabase_url, anon_key=anon_key)
    response = auth_client.auth.set_session(access_token.strip(), refresh_token.strip())
    result = _result_from_auth_response(response)
    if not result.access_token:
        result = SupabaseAuthResult(
            user_id=result.user_id,
            email=result.email,
            access_token=access_token.strip(),
            refresh_token=refresh_token.strip(),
            expires_in=result.expires_in,
            raw=response,
        )
    if not result.email:
        user_resp = auth_client.auth.get_user(access_token.strip())
        user = getattr(user_resp, "user", None) or user_resp
        email = _email_from_auth_user(user)
        if not email:
            raise ValueError("Supabase SSO session missing email")
        result = SupabaseAuthResult(
            user_id=_user_id_from_auth_user(user) if getattr(user, "id", None) else result.user_id,
            email=email,
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            expires_in=result.expires_in,
            raw=response,
        )
    logger.debug("Supabase SSO session ok user_id=%s", result.user_id)
    return result


def supabase_resend_signup_confirmation(
    *,
    supabase_url: str,
    anon_key: str,
    email: str,
    email_redirect_to: str | None = None,
    client: Client | None = None,
) -> None:
    """Resend the signup confirmation email via Supabase Auth ``resend``.

    Thin wrap of GoTrue ``auth.resend`` with ``type=signup``. Does not create
    Papita users or open sessions. Callers should treat Auth "user not found" /
    already-confirmed style errors as soft success to avoid email enumeration.

    Args:
        supabase_url: Project URL.
        anon_key: Anon (publishable) key.
        email: Address that previously signed up and still needs confirmation.
        email_redirect_to: Optional same-origin URL for the confirm link.
        client: Optional pre-built anon client (tests).

    Raises:
        AuthApiError: Supabase Auth rejected the resend (including SMTP 429).
        AuthError: Non-API Auth failure from the SDK.
        ValueError: Empty ``email``.
    """
    normalized = (email or "").strip().lower()
    if not normalized:
        raise ValueError("email is required")
    auth_client = client or create_supabase_auth_client(supabase_url=supabase_url, anon_key=anon_key)
    payload: dict[str, Any] = {"type": "signup", "email": normalized}
    if email_redirect_to and str(email_redirect_to).strip():
        payload["options"] = {"email_redirect_to": str(email_redirect_to).strip()}
    auth_client.auth.resend(cast(Any, payload))
    logger.info("Supabase signup confirmation resend requested email=%s", normalized)


__all__ = [
    "AuthApiError",
    "AuthError",
    "SupabaseAuthResult",
    "SupabaseOAuthStart",
    "SupabaseSignUpProfile",
    "classify_supabase_auth_error",
    "clear_supabase_client_cache",
    "create_supabase_admin_client",
    "create_supabase_auth_client",
    "is_email_not_confirmed_error",
    "is_invalid_credentials_error",
    "maybe_auto_confirm_auth_email",
    "supabase_admin_confirm_email",
    "supabase_admin_delete_user",
    "supabase_auth_user_created_recently",
    "supabase_establish_session",
    "supabase_exchange_code_for_session",
    "supabase_oauth_authorize_url",
    "supabase_refresh_session",
    "supabase_resend_signup_confirmation",
    "supabase_sign_in",
    "supabase_sign_out",
    "supabase_sign_up",
]
