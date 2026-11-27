"""Authentication routes — register, login, Google OAuth PKCE, refresh, and logout.

Maps HTTP under ``/api/v1/auth`` to self-hosted HS256 JWT helpers and optional
direct Google OAuth. Business logic stays in ``papita_txnsmodel`` /
``core.security``.
"""

# Auth surface is intentionally one router module (PPT-039/043/044).
# pylint: disable=too-many-lines

from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.oauth_txns import consume_oauth_txn, store_oauth_txn
from papita_txnsapi.core.security import AuthSecurityManager
from papita_txnsapi.dependencies.auth import (
    AUTH_ACCESS_COOKIE,
    AUTH_COOKIE_PATH,
    get_auth_manager,
    get_current_owner,
)
from papita_txnsapi.dependencies.rate_limit import (
    enforce_auth_login_rate_limit,
    enforce_auth_oauth_rate_limit,
    enforce_auth_register_rate_limit,
    enforce_tenant_api_rate_limit,
)
from papita_txnsapi.dependencies.services import get_users_service
from papita_txnsapi.schemas.auth import (
    OAuthCodeExchangeRequest,
    OAuthStartResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResendConfirmationRequest,
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

_AUTH_DEFERRED = DeferredResponse(deferred_reason="Stateless HS256 JWTs do not use an external refresh-token store")
_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}
_OAUTH_VERIFIER_COOKIE = "papita_oauth_cv"
_OAUTH_PROVIDER_COOKIE = "papita_oauth_provider"
_OAUTH_REDIRECT_COOKIE = "papita_oauth_rt"
_OAUTH_STATE_COOKIE = "papita_oauth_state"
_OAUTH_NEXT_COOKIE = "papita_oauth_next"
_OAUTH_COOKIE_MAX_AGE = 600
_OAUTH_COOKIE_PATH = "/api/v1/auth"
_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def _api_oauth_callback_url(request: Request) -> str:
    """Absolute URL for the named ``GET /auth/oauth/callback`` route.

    Args:
        request: Incoming request used to reverse-lookup the callback path.

    Returns:
        Absolute callback URI (scheme/host from the request).
    """
    return str(request.url_for("oauth_callback_get"))


def _resolve_oauth_redirect_to(
    request: Request,
    settings: Settings,
    redirect_to: str | None,
    *,
    extra_allowed: set[str] | None = None,
) -> str:
    """Resolve and allowlist the OAuth ``redirect_to`` URI."""
    callback = _api_oauth_callback_url(request)
    configured = (settings.GOOGLE_OAUTH_REDIRECT_URI or "").strip() or None
    allowed = {callback}
    if configured is not None:
        allowed.add(configured)
    if extra_allowed:
        allowed.update(extra_allowed)
    if redirect_to is None or not redirect_to.strip():
        return configured or callback
    candidate = redirect_to.strip()
    if candidate not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="redirect_to is not allowlisted; set GOOGLE_OAUTH_REDIRECT_URI or use the API callback",
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
    flow_handle = str(uuid.uuid4())
    store_oauth_txn(
        flow_handle,
        {
            "code_verifier": code_verifier,
            "provider": provider.value,
            "redirect_to": redirect_to,
        },
        ttl_seconds=_OAUTH_COOKIE_MAX_AGE,
    )
    response.set_cookie(
        key=_OAUTH_VERIFIER_COOKIE,
        value=flow_handle,
        max_age=_OAUTH_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=secure,
        path=_OAUTH_COOKIE_PATH,
    )


def _clear_oauth_pkce_cookies(response: Response) -> None:
    """Delete PKCE cookies after a successful browser OAuth callback.

    Args:
        response: Mutable response that clears the OAuth cookie names.

    Returns:
        None.
    """
    for key in (
        _OAUTH_VERIFIER_COOKIE,
        _OAUTH_PROVIDER_COOKIE,
        _OAUTH_REDIRECT_COOKIE,
        _OAUTH_STATE_COOKIE,
        _OAUTH_NEXT_COOKIE,
    ):
        response.delete_cookie(key=key, path=_OAUTH_COOKIE_PATH)


def _has_direct_google_oauth(settings: Settings) -> bool:
    """Return True when local mode is configured with direct Google OAuth credentials."""
    return (
        settings.AUTH_PROVIDER == "local"
        and bool((settings.GOOGLE_OAUTH_CLIENT_ID or "").strip())
        and bool((settings.GOOGLE_OAUTH_CLIENT_SECRET or "").strip())
    )


_SAFE_RETURN_PATHS = {
    "/": "/",
    "/dashboard": "/dashboard",
    "/accounts": "/accounts",
    "/transactions": "/transactions",
    "/categories": "/categories",
    "/reports": "/reports",
    "/projections": "/projections",
    "/payment-dues": "/payment-dues",
    "/integrations": "/integrations",
    "/settings": "/settings",
    "/login": "/login",
    "/register": "/register",
}


def _sanitize_return_to(raw: str | None) -> str:
    """Allow only strict allowlisted relative SPA paths for post-OAuth redirects."""
    if not raw:
        return "/dashboard"
    candidate = raw.strip()
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in candidate) or "\\" in candidate:
        return "/dashboard"
    if not candidate.startswith("/") or candidate.startswith("//"):
        return "/dashboard"
    parsed = urllib.parse.urlsplit(candidate)
    if parsed.scheme or parsed.netloc:
        return "/dashboard"
    base_path = _SAFE_RETURN_PATHS.get(parsed.path)
    if base_path is None:
        if parsed.path.startswith("/accounts/") and parsed.path.count("/") == 2:
            acc_id = parsed.path.removeprefix("/accounts/")
            if not acc_id or not all(ch.isalnum() or ch in "-_" for ch in acc_id):
                return "/dashboard"
            base_path = f"/accounts/{acc_id}"
        else:
            return "/dashboard"
    if parsed.query:
        safe_q = urllib.parse.urlencode(urllib.parse.parse_qsl(parsed.query, keep_blank_values=False))
        return f"{base_path}?{safe_q}" if safe_q else base_path
    return base_path


def _build_google_authorize_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_verifier: str,
) -> str:
    """Build Google OAuth2 authorization URL with PKCE S256."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    params = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
    )
    return f"{_GOOGLE_AUTH_URL}?{params}"


def _exchange_google_code(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    code_verifier: str,
    redirect_uri: str,
) -> dict[str, Any]:
    """Exchange Google authorization code for tokens and fetch verified OIDC userinfo."""
    token_body = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    token_req = urllib.request.Request(
        _GOOGLE_TOKEN_URL,
        data=token_body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(token_req, timeout=15) as resp:  # nosec B310 - fixed HTTPS Google token URL
        token_payload = json.loads(resp.read().decode("utf-8"))
    access_token = str(token_payload.get("access_token") or "").strip()
    if not access_token:
        raise ValueError("Google token response missing access_token")

    userinfo_req = urllib.request.Request(
        _GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(userinfo_req, timeout=15) as resp:  # nosec B310 - fixed HTTPS Google OIDC URL
        userinfo = json.loads(resp.read().decode("utf-8"))
    if not isinstance(userinfo, dict):
        raise ValueError("Invalid Google userinfo payload")
    return userinfo


def _set_access_token_cookie(
    response: Response,
    *,
    access_token: str,
    max_age: int,
    secure: bool,
) -> None:
    """Persist the stateless JWT in an HttpOnly, SameSite=Lax cookie for browser reloads."""
    response.set_cookie(
        key=AUTH_ACCESS_COOKIE,
        value=access_token,
        max_age=max(int(max_age), 1),
        httponly=True,
        samesite="lax",
        secure=secure,
        path=AUTH_COOKIE_PATH,
    )


def _clear_access_token_cookie(response: Response) -> None:
    """Clear the browser HttpOnly access-token cookie on logout."""
    response.delete_cookie(key=AUTH_ACCESS_COOKIE, path=AUTH_COOKIE_PATH)


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


def soft_resend_signup_confirmation(
    *,
    settings: Settings,
    email: str,
    email_redirect_to: str | None = None,
) -> None:
    """No-op signup confirmation resend for self-hosted local auth (PPT-068).

    Kept as a soft-success endpoint so older SPA clients can call it without
    probing whether an email is registered.

    Args:
        settings: Active API settings (unused for local auth).
        email: Candidate address from the client (unused).
        email_redirect_to: Optional confirm landing URL (unused).
    """
    _ = (settings, email, email_redirect_to)


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=RegisterResponse)
def register_user(
    body: RegisterRequest,
    _rate_limit: Annotated[None, Depends(enforce_auth_register_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
) -> RegisterResponse:
    """Register a new self-hosted user via ``UsersService``."""
    _ = settings
    resolved_username = body.username or UsersService.username_from_email(body.email)
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
def resend_confirmation(
    body: ResendConfirmationRequest,
    _rate_limit: Annotated[None, Depends(enforce_auth_register_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """Soft-success resend confirmation stub for self-hosted local auth.

    Always returns 204 (including unknown emails). Rate-limited with the
    register bucket for anti-enumeration parity with older clients.
    """
    soft_resend_signup_confirmation(
        settings=settings,
        email=body.email,
        email_redirect_to=body.email_redirect_to,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/login", response_model=TokenResponse)
def login(
    response: Response,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    _rate_limit: Annotated[None, Depends(enforce_auth_login_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
    auth_manager: Annotated[AuthSecurityManager, Depends(get_auth_manager)],
) -> TokenResponse:
    """OAuth2 password flow — local credential verify and HS256 JWT issuance."""
    user = users_service.verify_credentials(form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers=_UNAUTHORIZED_HEADERS,
        )

    token = auth_manager.generate_token(str(user.id))
    _set_access_token_cookie(
        response,
        access_token=token,
        max_age=settings.JWT_EXPIRATION_TIME_SECONDS,
        secure=settings.oauth_cookie_secure(),
    )
    return TokenResponse(
        access_token=token,
        token_type=settings.JWT_TOKEN_TYPE,
        expires_in=settings.JWT_EXPIRATION_TIME_SECONDS,
        refresh_token=None,
    )


@router.post("/oauth/callback", response_model=TokenResponse)
def oauth_callback_post(
    body: OAuthCodeExchangeRequest,
    _rate_limit: Annotated[None, Depends(enforce_auth_oauth_rate_limit)],
) -> TokenResponse:
    """Browser PKCE flow completes via ``GET /auth/oauth/callback``."""
    _ = body
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Use GET /api/v1/auth/oauth/google?follow=true for direct Google OAuth PKCE",
    )


@router.get("/oauth/callback", response_model=TokenResponse, name="oauth_callback_get")
def oauth_callback_get(  # pylint: disable=too-many-locals
    request: Request,
    _rate_limit: Annotated[None, Depends(enforce_auth_oauth_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
    auth_manager: Annotated[AuthSecurityManager, Depends(get_auth_manager)],
    *,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> TokenResponse | JSONResponse | RedirectResponse:
    """Browser redirect target for direct Google OAuth PKCE."""
    if _has_direct_google_oauth(settings):
        txn = consume_oauth_txn(request.cookies.get(_OAUTH_VERIFIER_COOKIE))
        next_path = _sanitize_return_to((txn or {}).get("next_path"))
        if next_path not in _SAFE_RETURN_PATHS.values() and not next_path.startswith(
            ("/settings?", "/integrations?", "/accounts/")
        ):
            next_path = "/dashboard"
        expected_state = (txn or {}).get("state")
        code_verifier = (txn or {}).get("code_verifier")
        redirect_uri = (
            (txn or {}).get("redirect_to")
            or (settings.GOOGLE_OAUTH_REDIRECT_URI or "").strip()
            or _api_oauth_callback_url(request)
        )
        state_ok = bool(state and expected_state and secrets.compare_digest(state, expected_state))
        if error or not code or not code_verifier or not state_ok:
            logger.warning("Direct Google OAuth callback rejected (error=%s, state_ok=%s)", bool(error), state_ok)
            failed = RedirectResponse(url="/login?oauth_error=1", status_code=status.HTTP_302_FOUND)
            _clear_oauth_pkce_cookies(failed)
            return failed
        try:
            userinfo = _exchange_google_code(
                client_id=(settings.GOOGLE_OAUTH_CLIENT_ID or "").strip(),
                client_secret=(settings.GOOGLE_OAUTH_CLIENT_SECRET or "").strip(),
                code=code,
                code_verifier=code_verifier,
                redirect_uri=redirect_uri,
            )
            email = str(userinfo.get("email") or "").strip().lower()
            if not email or not userinfo.get("email_verified", False):
                raise ValueError("Google account email is missing or unverified")
            display_name = str(userinfo.get("name") or "").strip() or None
            sub = str(userinfo.get("sub") or email).strip()

            user = users_service.get_by_email(email)
            if user is None:
                user = users_service.ensure_from_auth_subject(
                    subject=uuid.uuid5(uuid.NAMESPACE_URL, f"google:{sub}"),
                    email=email,
                    display_name=display_name,
                    provider_type=ProviderType.GOOGLE,
                )
            elif not user.active or user.deleted_at is not None:
                raise ValueError("User is inactive or deleted")

            token = auth_manager.generate_token(str(user.id))
            redirect_resp = RedirectResponse(url=next_path, status_code=status.HTTP_302_FOUND)
            _set_access_token_cookie(
                redirect_resp,
                access_token=token,
                max_age=settings.JWT_EXPIRATION_TIME_SECONDS,
                secure=settings.oauth_cookie_secure(),
            )
            _clear_oauth_pkce_cookies(redirect_resp)
            return redirect_resp
        except (urllib.error.URLError, ValueError, KeyError, json.JSONDecodeError) as exc:
            logger.warning("Direct Google OAuth exchange failed: %s", exc)
            failed = RedirectResponse(url="/login?oauth_error=1", status_code=status.HTTP_302_FOUND)
            _clear_oauth_pkce_cookies(failed)
            return failed

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Google OAuth is not configured (set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET)",
    )


@router.get("/oauth/{provider}", response_model=OAuthStartResponse)
def start_oauth(
    provider: str,
    request: Request,
    _rate_limit: Annotated[None, Depends(enforce_auth_oauth_rate_limit)],
    settings: Annotated[Settings, Depends(get_settings)],
    redirect_to: str | None = None,
    follow: bool = False,
    return_to: str = "/dashboard",
) -> OAuthStartResponse | RedirectResponse:
    """Start direct local Google OAuth (PKCE)."""
    _ = redirect_to
    oauth_provider = _parse_oauth_provider(provider)
    if oauth_provider == ProviderType.GOOGLE and _has_direct_google_oauth(settings):
        callback_uri = (settings.GOOGLE_OAUTH_REDIRECT_URI or "").strip() or _api_oauth_callback_url(request)
        code_verifier = secrets.token_urlsafe(48)
        state = secrets.token_urlsafe(24)
        auth_url = _build_google_authorize_url(
            client_id=(settings.GOOGLE_OAUTH_CLIENT_ID or "").strip(),
            redirect_uri=callback_uri,
            state=state,
            code_verifier=code_verifier,
        )
        if follow:
            response = RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)
            secure = settings.oauth_cookie_secure()
            safe_next = _sanitize_return_to(return_to)
            flow_handle = str(uuid.uuid4())
            store_oauth_txn(
                flow_handle,
                {
                    "code_verifier": code_verifier,
                    "provider": oauth_provider.value,
                    "redirect_to": callback_uri,
                    "state": state,
                    "next_path": safe_next,
                },
                ttl_seconds=_OAUTH_COOKIE_MAX_AGE,
            )
            response.set_cookie(
                key=_OAUTH_VERIFIER_COOKIE,
                value=flow_handle,
                max_age=_OAUTH_COOKIE_MAX_AGE,
                httponly=True,
                samesite="lax",
                secure=secure,
                path=_OAUTH_COOKIE_PATH,
            )
            return response
        return OAuthStartResponse(provider=oauth_provider, url=auth_url, code_verifier=code_verifier)

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Google OAuth is not configured (set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET)",
    )


@router.post("/sso", response_model=TokenResponse)
def complete_sso(
    body: SsoSessionRequest,
    _rate_limit: Annotated[None, Depends(enforce_auth_oauth_rate_limit)],
) -> TokenResponse:
    """Deprecated external SSO endpoint (use direct Google OAuth PKCE)."""
    _ = body
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Use GET /api/v1/auth/oauth/google?follow=true for direct Google OAuth PKCE",
    )


@router.get("/me", response_model=UserResponse)
def get_current_user(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    _rate_limit: Annotated[None, Depends(enforce_tenant_api_rate_limit)],
) -> UserResponse:
    """Return the authenticated user profile (protected route smoke test).

    Uses ``get_current_owner``, which verifies the bearer JWT (header or
    HttpOnly cookie). Tenant API rate limits apply (same Free/Pro/Enterprise
    quotas as other protected routers).

    Args:
        owner: Authenticated tenant user resolved from the bearer JWT.
        _rate_limit: Tenant API rate-limit dependency (side effect only).

    Returns:
        Public ``UserResponse`` for the current session user (never includes password).

    Raises:
        HTTPException: 401 when credentials are missing/invalid; 429 when the
            tenant API quota is exceeded.
    """
    return UserResponse.from_dto(owner)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    body: RefreshRequest,
    _rate_limit: Annotated[None, Depends(enforce_auth_oauth_rate_limit)],
) -> JSONResponse:
    """Self-hosted HS256 JWTs do not use an external refresh-token store."""
    _ = body
    return JSONResponse(status_code=status.HTTP_501_NOT_IMPLEMENTED, content=_AUTH_DEFERRED.model_dump())


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def logout(
    _rate_limit: Annotated[None, Depends(enforce_auth_oauth_rate_limit)],
) -> JSONResponse:
    """Clear the access-token cookie and return deferred status for stateless JWTs."""
    deferred_response = JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=_AUTH_DEFERRED.model_dump(),
    )
    _clear_access_token_cookie(deferred_response)
    return deferred_response
