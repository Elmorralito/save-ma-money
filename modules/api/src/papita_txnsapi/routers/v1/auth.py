"""Authentication routes — register, login, OAuth/SSO, refresh, and logout.

Exposes identity endpoints under ``/api/v1/auth``. Behavior depends on
``Settings.AUTH_PROVIDER``:

* ``supabase`` — register/login/refresh/logout/OAuth via Supabase Auth; JWTs are
  verified with JWKS on protected routes. Email is the canonical login identity.
  Failed Papita provision after Auth signup may trigger Admin orphan cleanup when
  ``SUPABASE_SERVICE_ROLE_KEY`` is set.
* ``local`` — register/login against ``UsersService`` and issue HS256 JWTs
  (tests / B0 only). Refresh and OAuth/SSO return HTTP 501. Logout returns 501
  unless Redis is enabled (JWT denylist via PPT-043).

Routes:
    ``POST /auth/register`` — create user (email + password; username derived).
    ``POST /auth/login`` — OAuth2 password flow (email in the username field).
    ``GET /auth/oauth/{provider}`` — PKCE authorize URL + ``code_verifier``.
    ``POST /auth/oauth/callback`` — exchange auth ``code`` + verifier.
    ``GET /auth/oauth/callback`` — browser redirect (code + HttpOnly PKCE cookies).
    ``POST /auth/sso`` — hand off when the client already holds session tokens.
    ``GET /auth/me`` — authenticated profile smoke test.
    ``POST /auth/refresh`` — Supabase session rotation (501 when local).
    ``POST /auth/logout`` — Supabase session revoke and/or Redis JWT denylist.

Rate limits apply to register, login, and OAuth/SSO/refresh via FastAPI
dependencies. OAuth ``redirect_to`` is allowlisted to the API callback URL and
optional ``SUPABASE_OAUTH_REDIRECT_TO``. Business logic stays in
``papita_txnsmodel`` / ``core.supabase_auth``; this module maps HTTP ↔ helpers.

Key exports:
    router: FastAPI ``APIRouter`` mounted at ``/auth`` by the v1 package.
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.core.session_store import SessionStore
from papita_txnsapi.core.supabase_auth import (
    AuthApiError,
    AuthError,
    SupabaseSignUpProfile,
    classify_supabase_auth_error,
    supabase_admin_delete_user,
    supabase_auth_user_created_recently,
    supabase_establish_session,
    supabase_exchange_code_for_session,
    supabase_oauth_authorize_url,
    supabase_refresh_session,
    supabase_sign_in,
    supabase_sign_out,
    supabase_sign_up,
)
from papita_txnsapi.dependencies.auth import get_auth_manager, get_current_owner
from papita_txnsapi.dependencies.rate_limit import (
    enforce_auth_login_rate_limit,
    enforce_auth_oauth_rate_limit,
    enforce_auth_register_rate_limit,
)
from papita_txnsapi.dependencies.services import get_users_service
from papita_txnsapi.dependencies.session_store import get_session_store
from papita_txnsapi.schemas.auth import (
    LogoutRequest,
    OAuthCodeExchangeRequest,
    OAuthStartResponse,
    RefreshRequest,
    RegisterRequest,
    SsoSessionRequest,
    TokenResponse,
    UserResponse,
)
from papita_txnsapi.schemas.common import DeferredResponse
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import ProviderType
from papita_txnsmodel.services.users import UsersService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

_AUTH_DEFERRED = DeferredResponse(
    deferred_reason="FR-11 refresh/logout require AUTH_PROVIDER=supabase (Supabase Auth sessions)"
)
_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}
_SUPABASE_AUTH_REQUIRED = "AUTH_PROVIDER=supabase requires SUPABASE_URL and SUPABASE_ANON_KEY for auth session APIs"
_optional_bearer = HTTPBearer(auto_error=False)
_OAUTH_VERIFIER_COOKIE = "papita_oauth_cv"
_OAUTH_PROVIDER_COOKIE = "papita_oauth_provider"
_OAUTH_REDIRECT_COOKIE = "papita_oauth_rt"
_OAUTH_COOKIE_MAX_AGE = 600
_OAUTH_COOKIE_PATH = "/api/v1/auth"


def _require_supabase_auth_settings(settings: Settings) -> None:
    """Ensure Supabase URL and anon key are configured for session Auth APIs.

    Args:
        settings: Application settings with ``SUPABASE_URL`` / ``SUPABASE_ANON_KEY``.

    Raises:
        HTTPException: 503 when either required Supabase Auth setting is missing.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_SUPABASE_AUTH_REQUIRED)


def _auth_error_detail(exc: Exception, *, fallback: str) -> str:
    """Extract a public-facing Auth error message from an SDK exception.

    Args:
        exc: Raised Auth or wrapper exception.
        fallback: Detail when the exception carries no usable message.

    Returns:
        Non-empty detail string suitable for ``HTTPException.detail``.
    """
    message = getattr(exc, "message", None) or str(exc) or fallback
    return str(message)


def _token_response_from_auth(
    *,
    access_token: str,
    refresh_token: str | None,
    expires_in: int | None,
    settings: Settings,
) -> TokenResponse:
    """Build an OAuth2-compatible ``TokenResponse`` from Auth session fields.

    Args:
        access_token: Bearer access JWT from Supabase (or local issuer).
        refresh_token: Opaque refresh token when issued; ``None`` for local login.
        expires_in: Access TTL seconds from Auth, or ``None`` to use Settings default.
        settings: Supplies ``JWT_TOKEN_TYPE`` and default expiration.

    Returns:
        ``TokenResponse`` with ``expires_in`` clamped to at least 1 second.
    """
    resolved_expires = int(expires_in or settings.JWT_EXPIRATION_TIME_SECONDS)
    return TokenResponse(
        access_token=access_token,
        token_type=settings.JWT_TOKEN_TYPE,
        expires_in=max(resolved_expires, 1),
        refresh_token=refresh_token,
    )


def _api_oauth_callback_url(request: Request) -> str:
    """Absolute URL for the named ``GET /auth/oauth/callback`` route.

    Args:
        request: Incoming request used to reverse-lookup the callback path.

    Returns:
        Absolute callback URI (scheme/host from the request).
    """
    return str(request.url_for("oauth_callback_get"))


def _resolve_oauth_redirect_to(request: Request, settings: Settings, redirect_to: str | None) -> str:
    """Resolve and allowlist the OAuth ``redirect_to`` URI.

    Allowed values are the API callback URL and ``SUPABASE_OAUTH_REDIRECT_TO``
    when configured. Rejects open redirects via arbitrary query params.

    Args:
        request: Current request (used to build the named callback URL).
        settings: Application settings that may define ``SUPABASE_OAUTH_REDIRECT_TO``.
        redirect_to: Client-requested redirect, or ``None`` for the default.

    Returns:
        An allowlisted absolute redirect URI for Supabase OAuth.

    Raises:
        HTTPException: 400 when ``redirect_to`` is set but not allowlisted.
    """
    callback = _api_oauth_callback_url(request)
    configured = (settings.SUPABASE_OAUTH_REDIRECT_TO or "").strip() or None
    allowed = {callback}
    if configured is not None:
        allowed.add(configured)
    if redirect_to is None or not redirect_to.strip():
        return configured or callback
    candidate = redirect_to.strip()
    if candidate not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="redirect_to is not allowlisted; set SUPABASE_OAUTH_REDIRECT_TO or use the API callback",
        )
    return candidate


def _set_oauth_pkce_cookies(
    response: Response,
    *,
    code_verifier: str,
    provider: ProviderType,
    redirect_to: str,
    secure: bool,
) -> None:
    """Store PKCE state in short-lived HttpOnly cookies for the browser callback.

    ``redirect_to`` must already be allowlisted via ``_resolve_oauth_redirect_to``.
    Cookies are HttpOnly, SameSite=Lax, path-scoped, and optionally Secure — not
    clear-text password storage; the verifier is bound to the OAuth handshake.

    Args:
        response: Mutable response that receives ``Set-Cookie`` headers.
        code_verifier: PKCE verifier from ``sign_in_with_oauth``.
        provider: OAuth channel stored for the GET callback.
        redirect_to: Allowlisted redirect URI used at authorize time.
        secure: When ``True``, set the Secure cookie flag (HTTPS).

    Returns:
        None.
    """
    cookie_kwargs = {
        "max_age": _OAUTH_COOKIE_MAX_AGE,
        "httponly": True,
        "samesite": "lax",
        "secure": secure,
        "path": _OAUTH_COOKIE_PATH,
    }
    # PKCE verifier + allowlisted redirect for GET /oauth/callback (browser flow).
    response.set_cookie(key=_OAUTH_VERIFIER_COOKIE, value=code_verifier, **cookie_kwargs)
    response.set_cookie(key=_OAUTH_PROVIDER_COOKIE, value=provider.value, **cookie_kwargs)
    response.set_cookie(key=_OAUTH_REDIRECT_COOKIE, value=redirect_to, **cookie_kwargs)


def _clear_oauth_pkce_cookies(response: Response) -> None:
    """Delete PKCE cookies after a successful browser OAuth callback.

    Args:
        response: Mutable response that clears the OAuth cookie names.

    Returns:
        None.
    """
    for key in (_OAUTH_VERIFIER_COOKIE, _OAUTH_PROVIDER_COOKIE, _OAUTH_REDIRECT_COOKIE):
        response.delete_cookie(key=key, path=_OAUTH_COOKIE_PATH)


def _parse_oauth_provider(raw: str) -> ProviderType:
    """Parse a path/cookie provider string into an OAuth ``ProviderType``.

    Args:
        raw: Provider id such as ``google`` or ``github`` (case-insensitive).

    Returns:
        ``ProviderType`` that reports ``is_oauth()`` as true.

    Raises:
        HTTPException: 404 when the value is unknown or not an OAuth channel.
    """
    try:
        oauth_provider = ProviderType(raw.strip().lower())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unsupported OAuth provider") from exc
    if not oauth_provider.is_oauth():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unsupported OAuth provider")
    return oauth_provider


def _http_status_for_provision_error(exc: ValueError) -> int:
    """Map Papita provision ``ValueError`` messages to HTTP status codes.

    Args:
        exc: Raised during ``ensure_from_auth_subject`` or related provision.

    Returns:
        409 for username/email conflicts, 401 for inactive/deleted users, else 502.
    """
    message = str(exc)
    if message in {"Username already registered", "Email already registered"}:
        return status.HTTP_409_CONFLICT
    if message == "User is inactive or deleted":
        return status.HTTP_401_UNAUTHORIZED
    return status.HTTP_502_BAD_GATEWAY


def _cleanup_orphan_auth_user(
    *,
    settings: Settings,
    user_id: uuid.UUID,
    reason: str,
    require_recent: bool,
) -> None:
    """Best-effort Admin delete of a half-created Auth identity.

    No-ops when the service role key is unset. Login cleanup can require the
    Auth user to be younger than the orphan window so established accounts are
    not wiped after a transient DB blip.

    Args:
        settings: Must include ``SUPABASE_SERVICE_ROLE_KEY`` for cleanup to run.
        user_id: Auth subject created before Papita provision failed.
        reason: Short label for logs (``register`` / ``login``).
        require_recent: When ``True`` (login), only delete Auth users younger than
            the orphan window so a transient DB blip does not wipe established accounts.

    Returns:
        None. Failures are logged; they do not raise to the client.
    """
    service_key = (settings.SUPABASE_SERVICE_ROLE_KEY or "").strip()
    if not service_key or not settings.SUPABASE_URL:
        logger.warning(
            "Skipping Auth orphan cleanup user_id=%s reason=%s (SUPABASE_SERVICE_ROLE_KEY unset)",
            user_id,
            reason,
        )
        return
    try:
        if require_recent and not supabase_auth_user_created_recently(
            supabase_url=settings.SUPABASE_URL,
            service_role_key=service_key,
            user_id=user_id,
        ):
            logger.info(
                "Skipping Auth orphan cleanup user_id=%s reason=%s (Auth user not recently created)",
                user_id,
                reason,
            )
            return
        supabase_admin_delete_user(
            supabase_url=settings.SUPABASE_URL,
            service_role_key=service_key,
            user_id=user_id,
        )
        logger.info("Cleaned up half-created Auth user user_id=%s reason=%s", user_id, reason)
    except Exception as cleanup_exc:  # pragma: no cover - Admin cleanup best-effort
        logger.exception(
            "Failed Auth orphan cleanup user_id=%s reason=%s: %s",
            user_id,
            reason,
            cleanup_exc,
        )


def _complete_oauth_provision(
    *,
    settings: Settings,
    users_service: UsersService,
    provider: ProviderType,
    auth_code: str,
    code_verifier: str,
    redirect_to: str | None,
    display_name: str | None = None,
) -> TokenResponse:
    """Exchange an OAuth code for a session and provision the Papita tenant row.

    Args:
        settings: App settings with Supabase URL and anon key.
        users_service: Service used for ``ensure_from_auth_subject``.
        provider: OAuth channel (``google`` or ``github``).
        auth_code: Authorization code from the IdP redirect.
        code_verifier: PKCE verifier from the authorize step.
        redirect_to: Allowlisted redirect URI that matched authorize, if any.
        display_name: Optional profile override when Auth metadata is incomplete.

    Returns:
        OAuth2-compatible ``TokenResponse`` with Supabase access/refresh tokens.

    Raises:
        AuthApiError: Supabase rejected the code exchange (API error).
        AuthError: Non-API Auth failure from the SDK.
        ValueError: Response missing user/session fields or provision failed.
    """
    auth_result = supabase_exchange_code_for_session(
        supabase_url=settings.SUPABASE_URL or "",
        anon_key=settings.SUPABASE_ANON_KEY or "",
        auth_code=auth_code,
        code_verifier=code_verifier,
        redirect_to=redirect_to,
    )
    users_service.ensure_from_auth_subject(
        subject=auth_result.user_id,
        email=auth_result.email,
        display_name=display_name,
        provider_type=provider,
    )
    return _token_response_from_auth(
        access_token=str(auth_result.access_token),
        refresh_token=auth_result.refresh_token,
        expires_in=auth_result.expires_in,
        settings=settings,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register_user(
    body: RegisterRequest,
    _rate_limit: Annotated[None, Depends(enforce_auth_register_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
) -> UserResponse:
    """Register a new user via Supabase Auth (or local ``UsersService``).

    Email is the canonical login identity. A schema ``username`` handle is
    derived from the email local-part when not supplied. Under Supabase, Auth
    signup runs first; Papita provision is idempotent. Provision failure after a
    successful Auth create triggers best-effort Admin orphan cleanup.

    Args:
        body: Registration payload (email, password, optional profile fields).
        _rate_limit: Per-IP register rate-limit dependency (side effect only).
        settings: Selects ``supabase`` vs ``local`` Auth mode.
        users_service: Creates or links the tenant ``users`` row.

    Returns:
        Public ``UserResponse`` for the new or already-linked tenant user.

    Raises:
        HTTPException: Mapped Auth/provision errors (409 conflict, 401 inactive,
            429 rate limit, 503 misconfigured Supabase, etc.).
    """
    resolved_username = body.username or UsersService.username_from_email(body.email)

    if settings.AUTH_PROVIDER == "supabase":
        _require_supabase_auth_settings(settings)
        auth_result = None
        try:
            auth_result = supabase_sign_up(
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
            )
            # Idempotent: returns existing active Papita row or creates one.
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
            logger.info("Supabase sign_up failed: %s", detail)
            raise HTTPException(status_code=http_status, detail=detail) from exc
        except ValueError as exc:
            logger.exception("Supabase signup provision error")
            if auth_result is not None:
                _cleanup_orphan_auth_user(
                    settings=settings,
                    user_id=auth_result.user_id,
                    reason="register",
                    require_recent=False,
                )
            raise HTTPException(
                status_code=_http_status_for_provision_error(exc),
                detail=str(exc),
                headers=_UNAUTHORIZED_HEADERS if str(exc) == "User is inactive or deleted" else None,
            ) from exc
        return UserResponse.from_dto(user)

    user = users_service.register(
        email=body.email,
        password=body.password,
        username=resolved_username,
        display_name=body.display_name,
        phone=body.phone,
        provider_type=body.provider_type,
    )
    return UserResponse.from_dto(user)


@router.post("/login", response_model=TokenResponse)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    _rate_limit: Annotated[None, Depends(enforce_auth_login_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
    auth_manager: Annotated[AuthSecurityManager, Depends(get_auth_manager)],
) -> TokenResponse:
    """OAuth2 password flow — Supabase Auth sign-in or local credential verify.

    Clients must put the **email** in the OAuth2 ``username`` form field when
    ``AUTH_PROVIDER=supabase``. Local mode still accepts email or derived username.
    Supabase login provisionally ensures a Papita row by Auth ``sub``; recent
    orphan Auth users may be deleted if provision fails (not for inactive tenants).

    Args:
        form: OAuth2 password form (``username`` + ``password``).
        _rate_limit: Per-IP login rate-limit dependency (side effect only).
        settings: Selects Auth mode and JWT/session defaults.
        users_service: Verifies credentials (local) or ensures Auth-linked user.
        auth_manager: Issues HS256 access tokens in local mode only.

    Returns:
        ``TokenResponse`` with access token; Supabase also returns ``refresh_token``.

    Raises:
        HTTPException: 401 for bad credentials; 429 when Auth rate-limits; other
            provision/Auth failures mapped from helpers.
    """
    if settings.AUTH_PROVIDER == "supabase":
        _require_supabase_auth_settings(settings)
        email = form.username.strip()
        if "@" not in email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Login requires email (OAuth2 username field)",
                headers=_UNAUTHORIZED_HEADERS,
            )
        auth_result = None
        try:
            auth_result = supabase_sign_in(
                supabase_url=settings.SUPABASE_URL or "",
                anon_key=settings.SUPABASE_ANON_KEY or "",
                email=email,
                password=form.password,
            )
            # Idempotent provision of papita_transactions.users by Auth sub.
            users_service.ensure_from_auth_subject(
                subject=auth_result.user_id,
                email=auth_result.email,
            )
            return _token_response_from_auth(
                access_token=str(auth_result.access_token),
                refresh_token=auth_result.refresh_token,
                expires_in=auth_result.expires_in,
                settings=settings,
            )
        except (AuthApiError, AuthError) as exc:
            http_status, detail = classify_supabase_auth_error(exc, fallback="login failed")
            if http_status == 401:
                detail = "Incorrect username or password"
            logger.info("Supabase sign_in failed: %s", detail)
            raise HTTPException(
                status_code=http_status if http_status in {401, 429} else status.HTTP_401_UNAUTHORIZED,
                detail=detail if http_status in {401, 429} else "Incorrect username or password",
                headers=_UNAUTHORIZED_HEADERS,
            ) from exc
        except ValueError as exc:
            logger.exception("Supabase login provision error")
            if auth_result is not None and str(exc) != "User is inactive or deleted":
                # Half-created Auth identity (e.g. prior register left Auth without Papita
                # and provision still fails): remove recent Auth users so re-register works.
                _cleanup_orphan_auth_user(
                    settings=settings,
                    user_id=auth_result.user_id,
                    reason="login",
                    require_recent=True,
                )
            raise HTTPException(
                status_code=_http_status_for_provision_error(exc),
                detail=str(exc),
                headers=_UNAUTHORIZED_HEADERS if str(exc) == "User is inactive or deleted" else None,
            ) from exc

    user = users_service.verify_credentials(form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers=_UNAUTHORIZED_HEADERS,
        )

    token = auth_manager.generate_token(str(user.id))
    return TokenResponse(
        access_token=token,
        token_type=settings.JWT_TOKEN_TYPE,
        expires_in=settings.JWT_EXPIRATION_TIME_SECONDS,
        refresh_token=None,
    )


@router.post("/oauth/callback", response_model=TokenResponse)
def oauth_callback_post(
    body: OAuthCodeExchangeRequest,
    request: Request,
    _rate_limit: Annotated[None, Depends(enforce_auth_oauth_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
) -> TokenResponse:
    """Complete Supabase OAuth with authorization ``code`` + PKCE verifier.

    Calls GoTrue ``exchange_code_for_session``, then provisions
    ``papita_transactions.users`` by Auth ``sub``. Preferred completion path for
    API clients that can store the ``code_verifier`` from authorize start.

    Args:
        body: Provider, auth code, PKCE verifier, optional redirect and name.
        request: Used to allowlist ``redirect_to`` against the API callback URL.
        _rate_limit: Per-IP OAuth rate-limit dependency (side effect only).
        settings: Must be ``AUTH_PROVIDER=supabase`` with URL and anon key.
        users_service: Provisions or refreshes the tenant profile.

    Returns:
        Supabase session tokens as ``TokenResponse``.

    Raises:
        HTTPException: 501 when not Supabase; 400/401 on provider or exchange errors.
    """
    if settings.AUTH_PROVIDER != "supabase":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OAuth SSO requires AUTH_PROVIDER=supabase",
        )
    if not body.provider.is_oauth():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported OAuth provider")
    _require_supabase_auth_settings(settings)
    try:
        redirect_to = _resolve_oauth_redirect_to(request, settings, body.redirect_to)
        return _complete_oauth_provision(
            settings=settings,
            users_service=users_service,
            provider=body.provider,
            auth_code=body.auth_code,
            code_verifier=body.code_verifier,
            redirect_to=redirect_to,
            display_name=body.display_name,
        )
    except (AuthApiError, AuthError) as exc:
        detail = _auth_error_detail(exc, fallback="OAuth code exchange rejected")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers=_UNAUTHORIZED_HEADERS,
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/oauth/callback", response_model=TokenResponse, name="oauth_callback_get")
def oauth_callback_get(
    request: Request,
    _rate_limit: Annotated[None, Depends(enforce_auth_oauth_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
    *,
    code: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> TokenResponse | JSONResponse:
    """Browser redirect target for Supabase OAuth (PKCE cookie + ``code``).

    Use with ``GET /auth/oauth/{provider}?follow=true`` so the PKCE verifier,
    provider, and ``redirect_to`` are available from HTTP-only cookies. Clears
    those cookies after a successful exchange.

    Args:
        request: Incoming redirect; cookies supply verifier/provider/redirect.
        _rate_limit: Per-IP OAuth rate-limit dependency (side effect only).
        settings: Must be ``AUTH_PROVIDER=supabase`` with URL and anon key.
        users_service: Provisions or refreshes the tenant profile.
        code: Authorization code query param from the IdP.
        error: Optional IdP error code when authorize failed.
        error_description: Optional human-readable IdP error text.

    Returns:
        JSON body matching ``TokenResponse`` with PKCE cookies cleared.

    Raises:
        HTTPException: 501 when not Supabase; 400 missing code/cookies; 401 on Auth errors.
    """
    if settings.AUTH_PROVIDER != "supabase":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OAuth SSO requires AUTH_PROVIDER=supabase",
        )
    if error:
        detail = error_description or error
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers=_UNAUTHORIZED_HEADERS)
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing OAuth authorization code")
    code_verifier = request.cookies.get(_OAUTH_VERIFIER_COOKIE)
    provider_raw = request.cookies.get(_OAUTH_PROVIDER_COOKIE)
    redirect_from_cookie = request.cookies.get(_OAUTH_REDIRECT_COOKIE)
    if not code_verifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth PKCE cookie; restart with GET /auth/oauth/{provider}?follow=true",
        )
    if not provider_raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth provider cookie; restart with GET /auth/oauth/{provider}?follow=true",
        )
    oauth_provider = _parse_oauth_provider(provider_raw)
    _require_supabase_auth_settings(settings)
    try:
        redirect_to = _resolve_oauth_redirect_to(request, settings, redirect_from_cookie)
        token = _complete_oauth_provision(
            settings=settings,
            users_service=users_service,
            provider=oauth_provider,
            auth_code=code,
            code_verifier=code_verifier,
            redirect_to=redirect_to,
        )
    except (AuthApiError, AuthError) as exc:
        detail = _auth_error_detail(exc, fallback="OAuth code exchange rejected")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers=_UNAUTHORIZED_HEADERS,
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    response = JSONResponse(content=token.model_dump(mode="json"))
    _clear_oauth_pkce_cookies(response)
    return response


@router.get("/oauth/{provider}", response_model=OAuthStartResponse)
def start_oauth(
    provider: str,
    request: Request,
    _rate_limit: Annotated[None, Depends(enforce_auth_oauth_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    redirect_to: str | None = None,
    follow: bool = False,
) -> OAuthStartResponse | RedirectResponse:
    """Start Supabase OAuth (PKCE) via ``sign_in_with_oauth``.

    Returns the authorize ``url`` and ``code_verifier``. Clients must keep the
    verifier and send it with the authorization ``code`` to
    ``POST /auth/oauth/callback``.

    When ``follow=true``, responds with ``302`` to the IdP and stores the PKCE
    verifier, provider, and ``redirect_to`` in HTTP-only cookies for
    ``GET /auth/oauth/callback``. Cookie ``Secure`` follows settings
    (``AUTH_COOKIE_SECURE`` / non-debug default).

    Args:
        provider: Path segment (``google`` or ``github``).
        request: Used to resolve the allowlisted redirect URI.
        _rate_limit: Per-IP OAuth rate-limit dependency (side effect only).
        settings: Must be ``AUTH_PROVIDER=supabase`` with URL and anon key.
        redirect_to: Optional allowlisted redirect override.
        follow: When ``True``, 302-redirect and set PKCE cookies.

    Returns:
        ``OAuthStartResponse`` JSON, or ``RedirectResponse`` when ``follow=true``.

    Raises:
        HTTPException: 501 when not Supabase; 404 unknown provider; 400 bad redirect;
            502 when Supabase fails to start OAuth.
    """
    if settings.AUTH_PROVIDER != "supabase":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OAuth SSO requires AUTH_PROVIDER=supabase",
        )
    oauth_provider = _parse_oauth_provider(provider)
    _require_supabase_auth_settings(settings)
    target = _resolve_oauth_redirect_to(request, settings, redirect_to)
    try:
        started = supabase_oauth_authorize_url(
            supabase_url=settings.SUPABASE_URL or "",
            anon_key=settings.SUPABASE_ANON_KEY or "",
            provider=oauth_provider.value,
            redirect_to=target,
        )
    except (AuthApiError, AuthError) as exc:
        detail = _auth_error_detail(exc, fallback=f"Failed to start {oauth_provider.value} OAuth")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    payload = OAuthStartResponse(
        provider=oauth_provider,
        url=started.url,
        code_verifier=started.code_verifier,
    )
    if follow:
        response = RedirectResponse(url=started.url, status_code=status.HTTP_302_FOUND)
        _set_oauth_pkce_cookies(
            response,
            code_verifier=started.code_verifier,
            provider=oauth_provider,
            redirect_to=target,
            secure=settings.oauth_cookie_secure(),
        )
        return response
    return payload


@router.post("/sso", response_model=TokenResponse)
def complete_sso(
    body: SsoSessionRequest,
    _rate_limit: Annotated[None, Depends(enforce_auth_oauth_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
) -> TokenResponse:
    """Complete OAuth when the client already holds Supabase session tokens.

    Prefer ``POST /auth/oauth/callback`` (authorization code + PKCE) when the
    redirect yields a ``code``. This endpoint remains for hash/fragment clients
    that already called Supabase JS and hold access/refresh tokens.

    Args:
        body: Provider, access token, refresh token, optional display name.
        _rate_limit: Per-IP OAuth rate-limit dependency (side effect only).
        settings: Must be ``AUTH_PROVIDER=supabase`` with URL and anon key.
        users_service: Provisions or refreshes the tenant profile.

    Returns:
        Validated session as ``TokenResponse`` (refresh falls back to the body).

    Raises:
        HTTPException: 501 when not Supabase; 401 if session is rejected; 400 on
            provision failures.
    """
    if settings.AUTH_PROVIDER != "supabase":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OAuth SSO requires AUTH_PROVIDER=supabase",
        )
    _require_supabase_auth_settings(settings)
    try:
        auth_result = supabase_establish_session(
            supabase_url=settings.SUPABASE_URL or "",
            anon_key=settings.SUPABASE_ANON_KEY or "",
            access_token=body.access_token,
            refresh_token=body.refresh_token,
        )
        users_service.ensure_from_auth_subject(
            subject=auth_result.user_id,
            email=auth_result.email,
            display_name=body.display_name,
            provider_type=body.provider,
        )
        return _token_response_from_auth(
            access_token=str(auth_result.access_token),
            refresh_token=auth_result.refresh_token or body.refresh_token,
            expires_in=auth_result.expires_in,
            settings=settings,
        )
    except (AuthApiError, AuthError) as exc:
        detail = _auth_error_detail(exc, fallback="SSO session rejected")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers=_UNAUTHORIZED_HEADERS,
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/me", response_model=UserResponse)
def get_current_user(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
) -> UserResponse:
    """Return the authenticated user profile (protected route smoke test).

    Uses ``get_current_owner``, which verifies the bearer JWT and may refresh
    Auth-linked profile fields under Supabase mode. When Redis is required,
    revoked tokens are rejected (denylist fail-closed).

    Args:
        owner: Authenticated tenant user resolved from the bearer JWT.

    Returns:
        Public ``UserResponse`` for the current session user (never includes password).

    Raises:
        HTTPException: 401 when credentials are missing/invalid/revoked; 503 when
            the Redis denylist is required but unavailable.
    """
    return UserResponse.from_dto(owner)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    body: RefreshRequest,
    _rate_limit: Annotated[None, Depends(enforce_auth_oauth_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse | JSONResponse:
    """Rotate Supabase Auth access/refresh tokens.

    When ``AUTH_PROVIDER=local``, returns HTTP 501 (no refresh-token store).

    Args:
        body: Current Supabase refresh token.
        _rate_limit: Per-IP OAuth/refresh rate-limit dependency (side effect only).
        settings: Application settings selecting Auth provider.

    Returns:
        New access and refresh tokens from Supabase Auth, or a deferred JSON body
        with status 501 in local mode.

    Raises:
        HTTPException: 401 on invalid refresh token; 400 on malformed Auth response;
            503 when Supabase URL/anon key are missing.
    """
    if settings.AUTH_PROVIDER != "supabase":
        return JSONResponse(status_code=status.HTTP_501_NOT_IMPLEMENTED, content=_AUTH_DEFERRED.model_dump())

    _require_supabase_auth_settings(settings)
    try:
        auth_result = supabase_refresh_session(
            supabase_url=settings.SUPABASE_URL or "",
            anon_key=settings.SUPABASE_ANON_KEY or "",
            refresh_token=body.refresh_token,
        )
        return _token_response_from_auth(
            access_token=str(auth_result.access_token),
            refresh_token=auth_result.refresh_token,
            expires_in=auth_result.expires_in,
            settings=settings,
        )
    except (AuthApiError, AuthError) as exc:
        detail = _auth_error_detail(exc, fallback="Invalid or expired refresh token")
        logger.info("Supabase refresh failed: %s", detail)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers=_UNAUTHORIZED_HEADERS,
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def logout(
    body: LogoutRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_optional_bearer)],
    session_store: Annotated[SessionStore, Depends(get_session_store)],
) -> Response | JSONResponse:
    """Revoke the session: Supabase Auth sign-out and/or Redis JWT denylist.

    * ``AUTH_PROVIDER=supabase`` — calls Supabase ``sign_out``, then denylists the
      access token when Redis is enabled so remaining JWT TTL cannot be reused.
    * ``AUTH_PROVIDER=local`` — when Redis is enabled, denylists the access token
      and returns 204; otherwise returns HTTP 501 (no refresh/session store).

    Access token may be supplied in the JSON body or as ``Authorization: Bearer``.

    Args:
        body: Refresh token (required for Supabase) and optional access token.
        settings: Application settings selecting Auth provider.
        credentials: Optional bearer credentials for the access JWT.
        session_store: Redis-backed JWT denylist (no-op when Redis disabled).

    Returns:
        Empty 204 response on success, or deferred JSON with status 501 in local
        mode without Redis.

    Raises:
        HTTPException: 400 when access token missing; 401 on Auth errors;
            503 when Auth misconfigured.
    """
    access_token = (body.access_token or "").strip() or (
        credentials.credentials.strip() if credentials and credentials.credentials else ""
    )

    if settings.AUTH_PROVIDER != "supabase":
        if not session_store.available:
            return JSONResponse(status_code=status.HTTP_501_NOT_IMPLEMENTED, content=_AUTH_DEFERRED.model_dump())
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="access_token is required (body.access_token or Authorization: Bearer)",
            )
        session_store.revoke(access_token, ttl_seconds=settings.JWT_EXPIRATION_TIME_SECONDS)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    _require_supabase_auth_settings(settings)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="access_token is required (body.access_token or Authorization: Bearer)",
        )

    try:
        supabase_sign_out(
            supabase_url=settings.SUPABASE_URL or "",
            anon_key=settings.SUPABASE_ANON_KEY or "",
            access_token=access_token,
            refresh_token=body.refresh_token,
        )
    except (AuthApiError, AuthError) as exc:
        detail = _auth_error_detail(exc, fallback="Supabase Auth logout failed")
        logger.info("Supabase sign_out failed: %s", detail)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if session_store.available:
        session_store.revoke(access_token, ttl_seconds=settings.JWT_EXPIRATION_TIME_SECONDS)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
