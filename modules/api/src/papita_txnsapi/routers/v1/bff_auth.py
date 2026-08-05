"""BFF cookie session routes — login/register/session/refresh/logout (PPT-049).

Thin session boundary inside ``papita_txnsapi``. Wraps the same Supabase / local
credential paths as ``/api/v1/auth/*`` but stores JWTs server-side and sets an
HttpOnly session-id cookie. Direct token clients keep using ``/auth/*``.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
import uuid
from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.auth_errors import auth_error_detail, public_value_error_detail
from papita_txnsapi.core.bff_session import (
    BFF_COOKIE_PATH,
    BFF_SESSION_COOKIE,
    DEFAULT_BFF_SESSION_MAX_AGE_SECONDS,
    BffSessionRecord,
    BffSessionStore,
    new_session_id,
    parse_owner_id_hint,
)
from papita_txnsapi.core.client_contract import ERROR_EMAIL_NOT_CONFIRMED, HEADER_ERROR_CODE
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.core.session_store import SessionStore
from papita_txnsapi.core.supabase_auth import (
    AuthApiError,
    AuthError,
    SupabaseSignUpProfile,
    classify_supabase_auth_error,
    supabase_oauth_authorize_url,
    supabase_refresh_session,
    supabase_sign_out,
)
from papita_txnsapi.core.supabase_auth_local import (
    elevate_unconfirmed_login_detail,
    register_requires_email_confirmation,
    supabase_register_user,
    supabase_sign_in_with_optional_auto_confirm,
)
from papita_txnsapi.dependencies.auth import get_auth_manager, get_current_owner, oauth2_scheme
from papita_txnsapi.dependencies.bff_session import get_bff_session_store
from papita_txnsapi.dependencies.rate_limit import (
    enforce_auth_login_rate_limit,
    enforce_auth_oauth_rate_limit,
    enforce_auth_register_rate_limit,
)
from papita_txnsapi.dependencies.services import get_users_service
from papita_txnsapi.dependencies.session_store import get_session_store
from papita_txnsapi.routers.v1.auth import (
    _UNAUTHORIZED_HEADERS,
    _cleanup_orphan_auth_user,
    _complete_oauth_provision,
    _http_status_for_provision_error,
    _parse_oauth_provider,
    _require_supabase_auth_settings,
    _resolve_oauth_redirect_to,
    _token_response_from_auth,
    soft_resend_signup_confirmation,
)
from papita_txnsapi.schemas.auth import RegisterResponse, UserResponse
from papita_txnsapi.schemas.bff_auth import (
    BffLoginRequest,
    BffRegisterRequest,
    BffResendConfirmationRequest,
    BffSessionResponse,
)
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import ProviderType
from papita_txnsmodel.services.users import UsersService

logger = logging.getLogger(__name__)

# Opaque ids from ``secrets.token_urlsafe`` (and length bound for Set-Cookie safety).
_BFF_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_EMAIL_NOT_CONFIRMED_HEADERS = {
    "WWW-Authenticate": "Bearer",
    HEADER_ERROR_CODE: ERROR_EMAIL_NOT_CONFIRMED,
}

# BFF OAuth PKCE cookies (Path=/api) — distinct from Bearer ``/auth/oauth/*`` cookies.
_BFF_OAUTH_VERIFIER_COOKIE = "papita_bff_oauth_cv"
_BFF_OAUTH_PROVIDER_COOKIE = "papita_bff_oauth_provider"
_BFF_OAUTH_REDIRECT_COOKIE = "papita_bff_oauth_rt"
_BFF_OAUTH_RETURN_COOKIE = "papita_bff_oauth_return"
_BFF_OAUTH_COOKIE_MAX_AGE = 600
_DEFAULT_SPA_RETURN_PATH = "/dashboard"
_OAUTH_ERROR_LOGIN_PATH = "/login?oauth_error=1"
# PKCE verifier charset (RFC 7636 unreserved) + length bound for Set-Cookie safety.
_BFF_OAUTH_VERIFIER_RE = re.compile(r"^[A-Za-z0-9._~-]{16,128}$")
# IdP ``error`` query codes are logged only when they match this shape.
_OAUTH_IDP_ERROR_CODE_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

router = APIRouter(prefix="/bff/auth", tags=["BFF Authentication"])


def _session_max_age(settings: Settings) -> int:
    """Return the BFF session cookie max-age from settings."""
    return int(getattr(settings, "BFF_SESSION_MAX_AGE_SECONDS", DEFAULT_BFF_SESSION_MAX_AGE_SECONDS))


def _set_session_cookie(response: Response, *, session_id: str, settings: Settings) -> None:
    """Attach the HttpOnly ``papita_sid`` cookie to ``response``.

    ``session_id`` must be server-generated opaque entropy (see ``new_session_id``),
    never a client-supplied value. Callers must not pass ``request.cookies`` values.
    """
    if _BFF_SESSION_ID_RE.fullmatch(session_id) is None:
        raise ValueError("invalid BFF session id for Set-Cookie")
    response.set_cookie(
        key=BFF_SESSION_COOKIE,
        value=session_id,
        max_age=_session_max_age(settings),
        httponly=True,
        samesite="lax",
        secure=settings.oauth_cookie_secure(),
        path=BFF_COOKIE_PATH,
    )


def _clear_session_cookie(response: Response) -> None:
    """Clear the BFF session cookie (logout / invalid session)."""
    response.delete_cookie(key=BFF_SESSION_COOKIE, path=BFF_COOKIE_PATH)


def _allowlisted_origins(settings: Settings) -> set[str]:
    """Concrete SPA origins from ``ALLOWED_ORIGINS`` (``*`` and blanks excluded)."""
    return {origin.rstrip("/") for origin in settings.ALLOWED_ORIGINS if origin and origin != "*"}


def _is_allowlisted_url(settings: Settings, url: str) -> bool:
    """True when ``url`` sits under a concrete allowlisted origin (no logging)."""
    trimmed = url.strip()
    if not trimmed:
        return False
    return any(trimmed == base or trimmed.startswith(f"{base}/") for base in _allowlisted_origins(settings))


def _match_allowlisted_origin(settings: Settings, candidate: str) -> str | None:
    """Return the ``ALLOWED_ORIGINS`` entry equal to ``candidate``, or ``None``.

    Iterating the allowlist and returning that entry (not the candidate string)
    breaks CodeQL URL-redirection taint after an allowlist membership check.
    """
    normalized = candidate.strip().rstrip("/")
    if not normalized:
        return None
    for allowed in _allowlisted_origins(settings):
        if normalized == allowed:
            return allowed
    return None


def _browser_origin_candidates(request: Request) -> list[str]:
    """Browser-facing origins advertised by the current request headers.

    Both ``Origin`` and ``Referer`` are attacker-influenced; callers must check
    them against ``ALLOWED_ORIGINS`` before using them to build a redirect.
    """
    candidates: list[str] = []
    origin_header = (request.headers.get("origin") or "").strip().rstrip("/")
    if origin_header:
        candidates.append(origin_header)
    referer = (request.headers.get("referer") or "").strip()
    if referer:
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc:
            candidates.append(f"{parsed.scheme}://{parsed.netloc}")
    return candidates


def _bff_oauth_callback_url(request: Request, settings: Settings) -> str:
    """Absolute BFF OAuth callback URL for Supabase ``redirect_to``.

    Prefers the browser-facing SPA origin (``Origin`` / ``Referer``) when it is
    allowlisted so Vite ``changeOrigin`` proxies do not advertise the upstream
    API host (cookies are scoped to the host the browser navigated). Falls back
    to the server-derived URL — never to an unvalidated header — so an empty or
    wildcard-only allowlist cannot widen the redirect target.
    """
    path = request.url_for("bff_oauth_callback_get").path
    server_callback = str(request.url_for("bff_oauth_callback_get"))
    candidates = [f"{origin}{path}" for origin in _browser_origin_candidates(request)]
    configured = (settings.SUPABASE_OAUTH_REDIRECT_TO or "").strip()
    if configured and "/bff/auth/oauth/callback" in configured:
        candidates.append(configured.rstrip("/"))
    candidates.append(server_callback)

    for candidate in candidates:
        if _is_allowlisted_url(settings, candidate):
            return candidate
    return server_callback


def _is_allowlisted_bff_callback(request: Request, settings: Settings, url: str) -> bool:
    """True when ``url`` is this API's OAuth callback on an allowlisted origin.

    Guards the ``papita_bff_oauth_rt`` cookie: a value tossed in by a sibling
    subdomain must not widen the Supabase ``redirect_to`` allowlist.
    """
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return False
    if parsed.path != request.url_for("bff_oauth_callback_get").path:
        return False
    allowed = _allowlisted_origins(settings)
    if not allowed:
        return url.strip() == str(request.url_for("bff_oauth_callback_get"))
    return f"{parsed.scheme}://{parsed.netloc}" in allowed


def _safe_spa_return_path(return_to: str | None) -> str:
    """Normalize a relative SPA path after OAuth; reject open redirects."""
    candidate = (return_to or _DEFAULT_SPA_RETURN_PATH).strip() or _DEFAULT_SPA_RETURN_PATH
    if not candidate.startswith("/") or candidate.startswith("//") or "\\" in candidate:
        return _DEFAULT_SPA_RETURN_PATH
    if "://" in candidate:
        return _DEFAULT_SPA_RETURN_PATH
    path_only = candidate.split("?", 1)[0].split("#", 1)[0]
    if not path_only.startswith("/") or path_only.startswith("//"):
        return _DEFAULT_SPA_RETURN_PATH
    return path_only or _DEFAULT_SPA_RETURN_PATH


def _spa_origin_from_request(request: Request, settings: Settings) -> str:
    """Pick an allowlisted SPA origin for post-OAuth redirects.

    ``Origin`` / ``Referer`` are only honoured when they appear verbatim in
    ``ALLOWED_ORIGINS``. With no concrete allowlist configured (empty, or ``*``
    only under ``DEBUG``) the headers are ignored entirely in favour of the
    request base URL, which TrustedHost validates whenever ``DEBUG=false``.
    """
    base_origin = str(request.base_url).rstrip("/")
    allowed = _allowlisted_origins(settings)
    if not allowed:
        return base_origin
    for candidate in (*_browser_origin_candidates(request), base_origin):
        if candidate in allowed:
            return candidate
    return sorted(allowed)[0]


def _resolve_spa_return_url(request: Request, settings: Settings, return_to: str | None) -> str:
    """Build an allowlisted SPA URL for the post-login redirect.

    Returns a relative ``Location`` when no allowlisted origin matches; that
    keeps the browser on the origin it already navigated instead of emitting an
    absolute URL that was never validated.
    """
    path = _safe_spa_return_path(return_to)
    origin = _spa_origin_from_request(request, settings)
    matched = _match_allowlisted_origin(settings, origin)
    if matched is not None:
        return f"{matched}{path}"
    # Fall back to dashboard on a known SPA origin (never the raw user string).
    absolute = f"{origin}{path}"
    if _is_allowlisted_url(settings, absolute):
        return absolute
    fallback = f"{origin}{_DEFAULT_SPA_RETURN_PATH}"
    if _is_allowlisted_url(settings, fallback):
        return fallback
    return path


def _post_oauth_spa_location(request: Request, settings: Settings, return_url: str | None) -> str:
    """Rebuild the post-OAuth SPA ``Location`` from allowlisted origins only.

    Never returns the raw ``papita_bff_oauth_return`` cookie string to
    ``RedirectResponse`` — even after an allowlist check — so open-redirect
    taint cannot reach the response.
    """
    if return_url:
        trimmed = return_url.strip()
        parsed = urlparse(trimmed)
        if parsed.scheme and parsed.netloc:
            matched = _match_allowlisted_origin(settings, f"{parsed.scheme}://{parsed.netloc}")
            if matched is not None:
                return f"{matched}{_safe_spa_return_path(parsed.path or _DEFAULT_SPA_RETURN_PATH)}"
        if trimmed.startswith("/") and not trimmed.startswith("//"):
            return _resolve_spa_return_url(request, settings, trimmed)
    return _resolve_spa_return_url(request, settings, _DEFAULT_SPA_RETURN_PATH)


def _set_bff_oauth_pkce_cookies(
    response: Response,
    *,
    settings: Settings,
    code_verifier: str,
    provider: ProviderType,
    redirect_to: str,
    return_url: str,
    secure: bool,
) -> None:
    """Store BFF OAuth PKCE + SPA return URL in Path=/api HttpOnly cookies."""
    cookie_kwargs = {
        "max_age": _BFF_OAUTH_COOKIE_MAX_AGE,
        "httponly": True,
        "samesite": "lax",
        "secure": secure,
        "path": BFF_COOKIE_PATH,
    }
    if _BFF_OAUTH_VERIFIER_RE.fullmatch(code_verifier) is None:
        raise ValueError("invalid BFF OAuth PKCE code_verifier for Set-Cookie")
    # PKCE code_verifier is OAuth entropy for the token exchange, not a user password.
    # It must round-trip in an HttpOnly Path=/api cookie until the BFF callback.
    # codeql[py/clear-text-storage-sensitive-data] PKCE verifier (not a password); HttpOnly Path=/api round-trip
    response.set_cookie(key=_BFF_OAUTH_VERIFIER_COOKIE, value=code_verifier, **cookie_kwargs)
    response.set_cookie(key=_BFF_OAUTH_PROVIDER_COOKIE, value=provider.value, **cookie_kwargs)
    # ``redirect_to`` is the server-computed BFF callback (never a query param).
    response.set_cookie(key=_BFF_OAUTH_REDIRECT_COOKIE, value=redirect_to, **cookie_kwargs)
    # Persist only an allowlist-rebuilt SPA URL / relative path (not raw return_to).
    parsed_return = urlparse(return_url.strip())
    if parsed_return.scheme and parsed_return.netloc:
        matched = _match_allowlisted_origin(settings, f"{parsed_return.scheme}://{parsed_return.netloc}")
        if matched is not None:
            safe_return = f"{matched}{_safe_spa_return_path(parsed_return.path or _DEFAULT_SPA_RETURN_PATH)}"
        else:
            safe_return = _safe_spa_return_path(parsed_return.path or _DEFAULT_SPA_RETURN_PATH)
    else:
        safe_return = _safe_spa_return_path(return_url)
    # codeql[py/cookie-injection] value is allowlist-rebuilt or a sanitized relative SPA path
    response.set_cookie(key=_BFF_OAUTH_RETURN_COOKIE, value=safe_return, **cookie_kwargs)


def _clear_bff_oauth_pkce_cookies(response: Response) -> None:
    """Delete BFF OAuth PKCE cookies after callback success or failure."""
    for key in (
        _BFF_OAUTH_VERIFIER_COOKIE,
        _BFF_OAUTH_PROVIDER_COOKIE,
        _BFF_OAUTH_REDIRECT_COOKIE,
        _BFF_OAUTH_RETURN_COOKIE,
    ):
        response.delete_cookie(key=key, path=BFF_COOKIE_PATH)


def _oauth_error_redirect(request: Request, settings: Settings, return_url: str | None) -> RedirectResponse:
    """302 to SPA ``/login?oauth_error=1``, clearing BFF OAuth cookies.

    The stored return cookie only selects the origin, and only when that origin
    is allowlisted, so a tampered cookie cannot redirect the failure off-site.
    """
    origin = _spa_origin_from_request(request, settings)
    if return_url:
        parsed = urlparse(return_url.strip())
        if parsed.scheme and parsed.netloc:
            matched = _match_allowlisted_origin(settings, f"{parsed.scheme}://{parsed.netloc}")
            if matched is not None:
                origin = matched
    matched_origin = _match_allowlisted_origin(settings, origin)
    if matched_origin is not None:
        target = f"{matched_origin}{_OAUTH_ERROR_LOGIN_PATH}"
    else:
        target = _OAUTH_ERROR_LOGIN_PATH
    response = RedirectResponse(url=target, status_code=status.HTTP_302_FOUND)
    _clear_bff_oauth_pkce_cookies(response)
    return response


def _session_response(
    *,
    user: UsersDTO,
    csrf_token: str | None,
    backend: str,
    access_expires_at: float | None = None,
) -> BffSessionResponse:
    """Build an authenticated BFF session JSON body (never includes JWTs)."""
    return BffSessionResponse(
        authenticated=True,
        user=UserResponse.from_dto(user),
        csrf_token=csrf_token,
        session_backend=backend,
        access_expires_at=access_expires_at,
    )


def _issue_local_tokens(
    *,
    users_service: UsersService,
    auth_manager: AuthSecurityManager,
    settings: Settings,
    email_or_username: str,
    password: str,
) -> tuple[str, str | None, int, UsersDTO]:
    """Verify local credentials and return access token fields plus owner DTO."""
    user = users_service.verify_credentials(email_or_username, password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers=_UNAUTHORIZED_HEADERS,
        )
    token = auth_manager.generate_token(str(user.id))
    return token, None, settings.JWT_EXPIRATION_TIME_SECONDS, user


def _issue_supabase_tokens(
    *,
    settings: Settings,
    users_service: UsersService,
    email: str,
    password: str,
) -> tuple[str, str | None, int, UsersDTO]:
    """Sign in via Supabase Auth and ensure the Papita tenant row exists."""
    _require_supabase_auth_settings(settings)
    auth_result = None
    existing = None
    try:
        existing = users_service.get_by_email(email)
        auth_result = supabase_sign_in_with_optional_auto_confirm(
            supabase_url=settings.SUPABASE_URL or "",
            anon_key=settings.SUPABASE_ANON_KEY or "",
            email=email,
            password=password,
            service_role_key=settings.SUPABASE_SERVICE_ROLE_KEY,
            auth_user_id=existing.id if existing is not None else None,
            auto_confirm=settings.should_auto_confirm_email(),
        )
        user = users_service.ensure_from_auth_subject(
            subject=auth_result.user_id,
            email=auth_result.email,
        )
        token = _token_response_from_auth(
            access_token=str(auth_result.access_token),
            refresh_token=auth_result.refresh_token,
            expires_in=auth_result.expires_in,
            settings=settings,
        )
        return token.access_token, token.refresh_token, token.expires_in, user
    except (AuthApiError, AuthError) as exc:
        http_status, detail = classify_supabase_auth_error(exc, fallback="login failed")
        http_status, detail = elevate_unconfirmed_login_detail(
            supabase_url=settings.SUPABASE_URL or "",
            service_role_key=settings.SUPABASE_SERVICE_ROLE_KEY,
            auth_user_id=existing.id if existing is not None else None,
            auto_confirm=settings.should_auto_confirm_email(),
            http_status=http_status,
            detail=detail,
        )
        if http_status == 401 and detail != "Email not confirmed":
            detail = "Incorrect username or password"
        headers = _EMAIL_NOT_CONFIRMED_HEADERS if detail == "Email not confirmed" else _UNAUTHORIZED_HEADERS
        raise HTTPException(
            status_code=http_status if http_status in {401, 429} else status.HTTP_401_UNAUTHORIZED,
            detail=detail if http_status in {401, 429} else "Incorrect username or password",
            headers=headers,
        ) from exc
    except ValueError as exc:
        if auth_result is not None and str(exc) != "User is inactive or deleted":
            _cleanup_orphan_auth_user(
                settings=settings,
                user_id=auth_result.user_id,
                reason="bff-login",
                require_recent=True,
            )
        raise HTTPException(
            status_code=_http_status_for_provision_error(exc),
            detail=public_value_error_detail(exc, fallback="Login failed"),
            headers=_UNAUTHORIZED_HEADERS if str(exc) == "User is inactive or deleted" else None,
        ) from exc


def _refresh_record(
    *,
    settings: Settings,
    record: BffSessionRecord,
) -> BffSessionRecord:
    """Rotate Supabase tokens in-place; local sessions cannot refresh."""
    if settings.AUTH_PROVIDER != "supabase":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="BFF refresh requires AUTH_PROVIDER=supabase",
        )
    if not record.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has no refresh token",
            headers=_UNAUTHORIZED_HEADERS,
        )
    _require_supabase_auth_settings(settings)
    try:
        auth_result = supabase_refresh_session(
            supabase_url=settings.SUPABASE_URL or "",
            anon_key=settings.SUPABASE_ANON_KEY or "",
            refresh_token=record.refresh_token,
        )
        token = _token_response_from_auth(
            access_token=str(auth_result.access_token),
            refresh_token=auth_result.refresh_token or record.refresh_token,
            expires_in=auth_result.expires_in,
            settings=settings,
        )
    except (AuthApiError, AuthError) as exc:
        detail = auth_error_detail(exc, fallback="Invalid or expired refresh token")
        logger.info("BFF refresh failed: %s", detail)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers=_UNAUTHORIZED_HEADERS,
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=public_value_error_detail(exc, fallback="Invalid or expired refresh token"),
        ) from exc

    return BffSessionRecord(
        access_token=token.access_token,
        refresh_token=token.refresh_token,
        csrf_token=record.csrf_token,
        access_expires_at=time.time() + max(1, token.expires_in),
        owner_id=record.owner_id,
    )


@router.post("/login", response_model=BffSessionResponse)
def bff_login(  # pylint: disable=too-many-positional-arguments
    body: BffLoginRequest,
    response: Response,
    _rate_limit: Annotated[None, Depends(enforce_auth_login_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
    auth_manager: Annotated[AuthSecurityManager, Depends(get_auth_manager)],
    bff_store: Annotated[BffSessionStore, Depends(get_bff_session_store)],
) -> BffSessionResponse:
    """Authenticate and set an HttpOnly session-id cookie (JWTs stay server-side)."""
    if settings.AUTH_PROVIDER == "supabase":
        access, refresh, expires_in, user = _issue_supabase_tokens(
            settings=settings,
            users_service=users_service,
            email=body.email.strip(),
            password=body.password,
        )
    else:
        access, refresh, expires_in, user = _issue_local_tokens(
            users_service=users_service,
            auth_manager=auth_manager,
            settings=settings,
            email_or_username=body.email.strip(),
            password=body.password,
        )

    session_id, record = bff_store.create(
        access_token=access,
        refresh_token=refresh,
        expires_in=expires_in,
        owner_id=parse_owner_id_hint(user.id),
        ttl_seconds=_session_max_age(settings),
    )
    _set_session_cookie(response, session_id=session_id, settings=settings)
    return _session_response(
        user=user,
        csrf_token=record.csrf_token,
        backend=bff_store.backend,
        access_expires_at=record.access_expires_at,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=RegisterResponse)
def bff_register(
    body: BffRegisterRequest,
    response: Response,
    _rate_limit: Annotated[None, Depends(enforce_auth_register_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
) -> RegisterResponse:
    """Register via the same Auth/UsersService path as ``POST /auth/register``.

    Does not create a BFF session — clients should call ``POST /bff/auth/login``
    after email confirmation when required (PPT-068). Never sets ``papita_sid``.
    """
    # Belt-and-suspenders: register must never attach a session cookie.
    _clear_session_cookie(response)
    resolved_username = body.username or UsersService.username_from_email(body.email)

    if settings.AUTH_PROVIDER == "supabase":
        _require_supabase_auth_settings(settings)
        auth_result = None
        try:
            auth_result = supabase_register_user(
                supabase_url=settings.SUPABASE_URL or "",
                anon_key=settings.SUPABASE_ANON_KEY or "",
                email=body.email,
                password=body.password,
                profile=SupabaseSignUpProfile(
                    username=resolved_username,
                    display_name=body.display_name,
                    phone=body.phone,
                    provider=body.provider_type,
                ),
                service_role_key=settings.SUPABASE_SERVICE_ROLE_KEY,
                prefer_admin_create=settings.should_auto_confirm_email(),
            )
            user = users_service.ensure_from_auth_subject(
                subject=auth_result.user_id,
                email=auth_result.email,
                username=resolved_username,
                display_name=body.display_name,
                phone=body.phone,
                provider_type=body.provider_type,
            )
        except (AuthApiError, AuthError) as exc:
            http_status, detail = classify_supabase_auth_error(exc, fallback="Supabase Auth registration failed")
            raise HTTPException(status_code=http_status, detail=detail) from exc
        except ValueError as exc:
            if auth_result is not None:
                _cleanup_orphan_auth_user(
                    settings=settings,
                    user_id=auth_result.user_id,
                    reason="bff-register",
                    require_recent=False,
                )
            raise HTTPException(
                status_code=_http_status_for_provision_error(exc),
                detail=public_value_error_detail(exc, fallback="Registration failed"),
                headers=_UNAUTHORIZED_HEADERS if str(exc) == "User is inactive or deleted" else None,
            ) from exc
        pending = register_requires_email_confirmation(
            access_token=auth_result.access_token,
            auto_confirm_enabled=settings.should_auto_confirm_email(),
        )
        return RegisterResponse.from_dto(user, email_confirmation_required=pending)

    user = users_service.register(
        email=body.email,
        password=body.password,
        username=resolved_username,
        display_name=body.display_name,
        phone=body.phone,
        provider_type=body.provider_type,
    )
    return RegisterResponse.from_dto(user, email_confirmation_required=False)


@router.post("/resend-confirmation", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def bff_resend_confirmation(
    body: BffResendConfirmationRequest,
    _rate_limit: Annotated[None, Depends(enforce_auth_register_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """Resend signup confirmation email for pending SPA users (PPT-068).

    Anonymous-friendly (CSRF-exempt). Does not set ``papita_sid``. Soft-succeeds
    for unknown emails; 429 when Auth/SMTP rate limits fire.
    """
    soft_resend_signup_confirmation(
        settings=settings,
        email=body.email,
        email_redirect_to=body.email_redirect_to,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/session", response_model=BffSessionResponse)
def bff_session(  # pylint: disable=too-many-positional-arguments
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
    bff_store: Annotated[BffSessionStore, Depends(get_bff_session_store)],
    session_store: Annotated[SessionStore, Depends(get_session_store)],
) -> BffSessionResponse:
    """Probe BFF session for SPA bootstrap.

    Returns ``authenticated: false`` (200) when no valid cookie/Bearer — avoids
    treating anonymous bootstrap as an error. When authenticated via cookie,
    includes ``csrf_token`` for mutation headers.
    """
    try:
        owner = get_current_owner(
            request=request,
            token=token,
            settings=settings,
            users_service=users_service,
            session_store=session_store,
            bff_store=bff_store,
        )
    except HTTPException as exc:
        # Anonymous bootstrap → 200 unauthenticated. Propagate 503 (denylist / BFF
        # store fail-closed) so the SPA can retry instead of treating Redis as logout.
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return BffSessionResponse(authenticated=False, session_backend=bff_store.backend)
        raise

    csrf_token: str | None = None
    access_expires_at: float | None = None
    session_id = request.cookies.get(BFF_SESSION_COOKIE)
    if session_id:
        record = bff_store.get(session_id)
        if record is not None:
            csrf_token = record.csrf_token
            access_expires_at = record.access_expires_at
    return _session_response(
        user=owner,
        csrf_token=csrf_token,
        backend=bff_store.backend,
        access_expires_at=access_expires_at,
    )


@router.post("/refresh", response_model=BffSessionResponse)
def bff_refresh(
    request: Request,
    response: Response,
    _rate_limit: Annotated[None, Depends(enforce_auth_oauth_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
    bff_store: Annotated[BffSessionStore, Depends(get_bff_session_store)],
) -> BffSessionResponse:
    """Rotate tokens inside the BFF session store (cookie required)."""
    session_id = request.cookies.get(BFF_SESSION_COOKIE)
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing BFF session cookie",
            headers=_UNAUTHORIZED_HEADERS,
        )
    record = bff_store.get(session_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired BFF session",
            headers=_UNAUTHORIZED_HEADERS,
        )

    updated = _refresh_record(settings=settings, record=record)
    # Rotate the opaque cookie id so Set-Cookie never echoes a client-supplied value.
    rotated_id = new_session_id()
    bff_store.delete(session_id)
    bff_store.update(rotated_id, updated, ttl_seconds=_session_max_age(settings))
    _set_session_cookie(response, session_id=rotated_id, settings=settings)

    auth_manager = AuthSecurityManager(settings)
    expected_type = settings.JWT_TOKEN_TYPE if settings.AUTH_PROVIDER == "local" else None
    payload = auth_manager.decode_token(updated.access_token, expected_type=expected_type)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers=_UNAUTHORIZED_HEADERS,
        )
    owner = users_service.get_owner(payload["sub"]) if settings.AUTH_PROVIDER == "local" else None
    if settings.AUTH_PROVIDER == "supabase":
        owner = users_service.ensure_from_auth_subject(
            subject=uuid.UUID(str(payload["sub"])),
            email=str(payload.get("email") or "").strip(),
        )
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers=_UNAUTHORIZED_HEADERS,
        )
    return _session_response(
        user=owner,
        csrf_token=updated.csrf_token,
        backend=bff_store.backend,
        access_expires_at=updated.access_expires_at,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def bff_logout(
    request: Request,
    response: Response,
    _rate_limit: Annotated[None, Depends(enforce_auth_oauth_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    bff_store: Annotated[BffSessionStore, Depends(get_bff_session_store)],
    session_store: Annotated[SessionStore, Depends(get_session_store)],
) -> Response:
    """Clear BFF session cookie, revoke at IdP when possible, denylist access JWT."""
    session_id = request.cookies.get(BFF_SESSION_COOKIE)
    record = bff_store.get(session_id) if session_id else None

    if record is not None and settings.AUTH_PROVIDER == "supabase" and record.refresh_token:
        try:
            _require_supabase_auth_settings(settings)
            supabase_sign_out(
                supabase_url=settings.SUPABASE_URL or "",
                anon_key=settings.SUPABASE_ANON_KEY or "",
                access_token=record.access_token,
                refresh_token=record.refresh_token,
            )
        except (AuthApiError, AuthError, ValueError, HTTPException) as exc:
            logger.info("BFF Supabase sign_out best-effort failed: %s", exc)

    if record is not None and session_store.available:
        session_store.revoke(record.access_token, ttl_seconds=settings.JWT_EXPIRATION_TIME_SECONDS)

    if session_id:
        bff_store.delete(session_id)
    _clear_session_cookie(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/oauth/callback", name="bff_oauth_callback_get", include_in_schema=True)
def bff_oauth_callback(  # pylint: disable=too-many-locals,too-many-positional-arguments
    request: Request,
    _rate_limit: Annotated[None, Depends(enforce_auth_oauth_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
    bff_store: Annotated[BffSessionStore, Depends(get_bff_session_store)],
    code: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> RedirectResponse:
    """Complete Supabase OAuth for the SPA and set ``papita_sid`` (never JWT JSON).

    Pair with ``GET /bff/auth/oauth/{provider}``. Exchanges the authorization
    ``code`` using Path=/api PKCE cookies, creates a BFF session, then 302s to
    the allowlisted SPA ``return_to`` URL. Failures redirect to ``/login?oauth_error=1``.
    """
    return_url = request.cookies.get(_BFF_OAUTH_RETURN_COOKIE)
    if settings.AUTH_PROVIDER != "supabase":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OAuth SSO requires AUTH_PROVIDER=supabase",
        )
    if error:
        safe_error = error if _OAUTH_IDP_ERROR_CODE_RE.fullmatch(error) else "invalid"
        desc_digest = (
            hashlib.sha256((error_description or "").encode("utf-8")).hexdigest()[:12] if error_description else "-"
        )
        logger.info("BFF OAuth IdP error code=%s desc_digest=%s", safe_error, desc_digest)
        return _oauth_error_redirect(request, settings, return_url)

    code_verifier = request.cookies.get(_BFF_OAUTH_VERIFIER_COOKIE)
    provider_raw = request.cookies.get(_BFF_OAUTH_PROVIDER_COOKIE)
    redirect_from_cookie = request.cookies.get(_BFF_OAUTH_REDIRECT_COOKIE)
    if not code or not code_verifier or not provider_raw:
        return _oauth_error_redirect(request, settings, return_url)

    try:
        oauth_provider = _parse_oauth_provider(provider_raw)
    except HTTPException:
        return _oauth_error_redirect(request, settings, return_url)

    callback = _bff_oauth_callback_url(request, settings)
    # Only honour the stored redirect when it is still this API's callback on an
    # allowlisted origin; otherwise recompute rather than trust the cookie.
    stored_redirect = (redirect_from_cookie or "").strip()
    if not stored_redirect or not _is_allowlisted_bff_callback(request, settings, stored_redirect):
        stored_redirect = callback
    try:
        redirect_to = _resolve_oauth_redirect_to(
            request,
            settings,
            stored_redirect,
            extra_allowed={callback, stored_redirect},
        )
        token, user = _complete_oauth_provision(
            settings=settings,
            users_service=users_service,
            provider=oauth_provider,
            auth_code=code,
            code_verifier=code_verifier,
            redirect_to=redirect_to,
        )
    except (AuthApiError, AuthError, ValueError, HTTPException) as exc:
        logger.info("BFF OAuth callback failed: %s", exc)
        return _oauth_error_redirect(request, settings, return_url)

    session_id, _record = bff_store.create(
        access_token=token.access_token,
        refresh_token=token.refresh_token,
        expires_in=token.expires_in,
        owner_id=parse_owner_id_hint(user.id),
        ttl_seconds=_session_max_age(settings),
    )

    spa_target = _post_oauth_spa_location(request, settings, return_url)

    response = RedirectResponse(url=spa_target, status_code=status.HTTP_302_FOUND)
    _set_session_cookie(response, session_id=session_id, settings=settings)
    _clear_bff_oauth_pkce_cookies(response)
    return response


@router.get("/oauth/{provider}")
def bff_start_oauth(  # pylint: disable=too-many-positional-arguments
    provider: str,
    request: Request,
    _rate_limit: Annotated[None, Depends(enforce_auth_oauth_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    return_to: str | None = None,
) -> RedirectResponse:
    """Start Supabase OAuth for the SPA and 302 to the IdP (PKCE cookies, Path=/api).

    Browser navigates here (full page, not ``fetch``). ``return_to`` is a relative
    SPA path (default ``/dashboard``) stored for the callback redirect after
    ``papita_sid`` is set. Never returns JWTs or the PKCE verifier to JavaScript.
    """
    if settings.AUTH_PROVIDER != "supabase":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OAuth SSO requires AUTH_PROVIDER=supabase",
        )
    oauth_provider = _parse_oauth_provider(provider)
    _require_supabase_auth_settings(settings)

    callback = _bff_oauth_callback_url(request, settings)
    # Authorize must return to the BFF callback (not Bearer JWT ``/auth/oauth/callback``).
    target = _resolve_oauth_redirect_to(
        request,
        settings,
        callback,
        extra_allowed={callback},
    )
    return_url = _resolve_spa_return_url(request, settings, return_to)

    try:
        started = supabase_oauth_authorize_url(
            supabase_url=settings.SUPABASE_URL or "",
            anon_key=settings.SUPABASE_ANON_KEY or "",
            provider=oauth_provider.value,
            redirect_to=target,
        )
    except (AuthApiError, AuthError) as exc:
        detail = auth_error_detail(exc, fallback=f"Failed to start {oauth_provider.value} OAuth")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=public_value_error_detail(exc, fallback=f"Failed to start {oauth_provider.value} OAuth"),
        ) from exc

    response = RedirectResponse(url=started.url, status_code=status.HTTP_302_FOUND)
    _set_bff_oauth_pkce_cookies(
        response,
        settings=settings,
        code_verifier=started.code_verifier,
        provider=oauth_provider,
        redirect_to=target,
        return_url=return_url,
        secure=settings.oauth_cookie_secure(),
    )
    return response
