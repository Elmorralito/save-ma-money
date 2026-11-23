"""Sibling Identity / Auth provider protocol decoupling routers from Supabase SDK."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, Protocol, runtime_checkable

from papita_txnsapi.config.settings import Settings
from papita_txnsapi.core.auth_health import AuthProbeDetail, AuthProbeResult, probe_supabase_auth
from papita_txnsapi.core.supabase_auth import (
    SupabaseAuthResult,
    SupabaseOAuthStart,
    SupabaseSignUpProfile,
    classify_supabase_auth_error,
    supabase_admin_delete_user,
    supabase_auth_user_created_recently,
    supabase_establish_session,
    supabase_exchange_code_for_session,
    supabase_oauth_authorize_url,
    supabase_refresh_session,
    supabase_resend_signup_confirmation,
    supabase_sign_out,
)
from papita_txnsapi.core.supabase_auth_local import (
    supabase_register_user,
    supabase_sign_in_with_optional_auto_confirm,
)


@runtime_checkable
class AuthProvider(Protocol):
    """Protocol for external/local authentication providers."""

    @property
    def provider_name(self) -> Literal["local", "supabase"]:
        """Active provider slug."""

    @property
    def supports_external_sessions(self) -> bool:
        """Whether this provider handles OAuth/refresh/sign-out externally."""

    def probe_health(self, *, probe_fn: Callable[..., AuthProbeResult] | None = None) -> AuthProbeResult:
        """Run a readiness probe against the auth backend."""

    def register(
        self,
        *,
        email: str,
        password: str,
        profile: SupabaseSignUpProfile | None = None,
    ) -> SupabaseAuthResult:
        """Register a user via the external auth backend."""

    def sign_in(self, *, email: str, password: str, auth_user_id: str | None = None) -> SupabaseAuthResult:
        """Authenticate a user via email/password."""

    def refresh_session(self, *, refresh_token: str) -> SupabaseAuthResult:
        """Rotate/refresh an external session."""

    def sign_out(self, *, access_token: str, refresh_token: str, scope: str = "global") -> None:
        """Revoke an external session."""

    def resend_signup_confirmation(self, *, email: str) -> None:
        """Trigger confirmation email resend."""

    def oauth_authorize_url(self, *, provider: str, redirect_to: str) -> SupabaseOAuthStart:
        """Start an OAuth PKCE flow."""

    def exchange_code_for_session(self, *, auth_code: str, code_verifier: str) -> SupabaseAuthResult:
        """Complete an OAuth PKCE exchange."""

    def establish_session(self, *, access_token: str, refresh_token: str) -> SupabaseAuthResult:
        """Validate and normalize a client-held external session."""

    def classify_error(self, exc: Exception, *, fallback: str) -> tuple[int, str]:
        """Map provider exceptions to ``(http_status, detail)``."""

    def admin_delete_user(self, *, user_id: str) -> None:
        """Delete an orphaned external user via admin credentials."""

    def user_created_recently(self, *, user_id: str) -> bool:
        """Return whether an external user was created within the orphan cleanup window."""


class LocalAuthProvider:
    """Test/dev HS256 auth provider (no external network calls)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def provider_name(self) -> Literal["local", "supabase"]:
        return "local"

    @property
    def supports_external_sessions(self) -> bool:
        return False

    def probe_health(self, *, probe_fn: Callable[..., AuthProbeResult] | None = None) -> AuthProbeResult:
        if probe_fn is not None:
            return probe_fn(
                auth_provider="local",
                supabase_url=self._settings.SUPABASE_URL,
                anon_key=self._settings.SUPABASE_ANON_KEY,
            )
        return AuthProbeResult(
            reachable=True,
            latency_ms=None,
            detail=AuthProbeDetail.SKIPPED_LOCAL,
            provider="local",
        )

    def _unsupported(self, action: str) -> NotImplementedError:
        return NotImplementedError(f"{action} requires an external AuthProvider (AUTH_PROVIDER=supabase)")

    def register(
        self,
        *,
        email: str,
        password: str,
        profile: SupabaseSignUpProfile | None = None,
    ) -> SupabaseAuthResult:
        raise self._unsupported("register")

    def sign_in(self, *, email: str, password: str, auth_user_id: str | None = None) -> SupabaseAuthResult:
        raise self._unsupported("sign_in")

    def refresh_session(self, *, refresh_token: str) -> SupabaseAuthResult:
        raise self._unsupported("refresh_session")

    def sign_out(self, *, access_token: str, refresh_token: str, scope: str = "global") -> None:
        raise self._unsupported("sign_out")

    def resend_signup_confirmation(self, *, email: str) -> None:
        raise self._unsupported("resend_signup_confirmation")

    def oauth_authorize_url(self, *, provider: str, redirect_to: str) -> SupabaseOAuthStart:
        raise self._unsupported("oauth_authorize_url")

    def exchange_code_for_session(self, *, auth_code: str, code_verifier: str) -> SupabaseAuthResult:
        raise self._unsupported("exchange_code_for_session")

    def establish_session(self, *, access_token: str, refresh_token: str) -> SupabaseAuthResult:
        raise self._unsupported("establish_session")

    def classify_error(self, exc: Exception, *, fallback: str) -> tuple[int, str]:
        return (500, str(exc) or fallback)

    def admin_delete_user(self, *, user_id: str) -> None:
        return None

    def user_created_recently(self, *, user_id: str) -> bool:
        return False


class SupabaseAuthProvider:
    """Supabase GoTrue Auth provider adapter."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def provider_name(self) -> Literal["local", "supabase"]:
        return "supabase"

    @property
    def supports_external_sessions(self) -> bool:
        return True

    def _require_credentials(self) -> tuple[str, str]:
        url = (self._settings.SUPABASE_URL or "").strip()
        anon_key = (self._settings.SUPABASE_ANON_KEY or "").strip()
        if not url or not anon_key:
            raise ValueError("AUTH_PROVIDER=supabase requires SUPABASE_URL and SUPABASE_ANON_KEY")
        return url, anon_key

    def probe_health(self, *, probe_fn: Callable[..., AuthProbeResult] | None = None) -> AuthProbeResult:
        fn = probe_fn or probe_supabase_auth
        return fn(
            auth_provider="supabase",
            supabase_url=self._settings.SUPABASE_URL,
            anon_key=self._settings.SUPABASE_ANON_KEY,
        )

    def register(
        self,
        *,
        email: str,
        password: str,
        profile: SupabaseSignUpProfile | None = None,
    ) -> SupabaseAuthResult:
        url, anon_key = self._require_credentials()
        return supabase_register_user(
            supabase_url=url,
            anon_key=anon_key,
            service_role_key=self._settings.SUPABASE_SERVICE_ROLE_KEY,
            prefer_admin_create=bool(self._settings.AUTH_AUTO_CONFIRM_EMAIL),
            email=email,
            password=password,
            profile=profile,
        )

    def sign_in(self, *, email: str, password: str, auth_user_id: str | None = None) -> SupabaseAuthResult:
        url, anon_key = self._require_credentials()
        return supabase_sign_in_with_optional_auto_confirm(
            supabase_url=url,
            anon_key=anon_key,
            service_role_key=self._settings.SUPABASE_SERVICE_ROLE_KEY,
            auth_user_id=auth_user_id,
            auto_confirm=bool(self._settings.AUTH_AUTO_CONFIRM_EMAIL),
            email=email,
            password=password,
        )

    def refresh_session(self, *, refresh_token: str) -> SupabaseAuthResult:
        url, anon_key = self._require_credentials()
        return supabase_refresh_session(
            supabase_url=url,
            anon_key=anon_key,
            refresh_token=refresh_token,
        )

    def sign_out(self, *, access_token: str, refresh_token: str, scope: str = "global") -> None:
        url, anon_key = self._require_credentials()
        supabase_sign_out(
            supabase_url=url,
            anon_key=anon_key,
            access_token=access_token,
            refresh_token=refresh_token,
            scope=scope,
        )

    def resend_signup_confirmation(self, *, email: str) -> None:
        url, anon_key = self._require_credentials()
        supabase_resend_signup_confirmation(supabase_url=url, anon_key=anon_key, email=email)

    def oauth_authorize_url(self, *, provider: str, redirect_to: str) -> SupabaseOAuthStart:
        url, anon_key = self._require_credentials()
        return supabase_oauth_authorize_url(
            supabase_url=url,
            anon_key=anon_key,
            provider=provider,
            redirect_to=redirect_to,
        )

    def exchange_code_for_session(self, *, auth_code: str, code_verifier: str) -> SupabaseAuthResult:
        url, anon_key = self._require_credentials()
        return supabase_exchange_code_for_session(
            supabase_url=url,
            anon_key=anon_key,
            auth_code=auth_code,
            code_verifier=code_verifier,
        )

    def establish_session(self, *, access_token: str, refresh_token: str) -> SupabaseAuthResult:
        url, anon_key = self._require_credentials()
        return supabase_establish_session(
            supabase_url=url,
            anon_key=anon_key,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    def classify_error(self, exc: Exception, *, fallback: str) -> tuple[int, str]:
        return classify_supabase_auth_error(exc, fallback=fallback)

    def admin_delete_user(self, *, user_id: str) -> None:
        if not self._settings.SUPABASE_URL or not self._settings.SUPABASE_SERVICE_ROLE_KEY:
            return
        supabase_admin_delete_user(
            supabase_url=self._settings.SUPABASE_URL,
            service_role_key=self._settings.SUPABASE_SERVICE_ROLE_KEY,
            user_id=user_id,
        )

    def user_created_recently(self, *, user_id: str) -> bool:
        if not self._settings.SUPABASE_URL or not self._settings.SUPABASE_SERVICE_ROLE_KEY:
            return False
        return supabase_auth_user_created_recently(
            supabase_url=self._settings.SUPABASE_URL,
            service_role_key=self._settings.SUPABASE_SERVICE_ROLE_KEY,
            user_id=user_id,
        )


AuthProviderFactory = Callable[[Settings], AuthProvider]

_AUTH_PROVIDER_FACTORIES: dict[str, AuthProviderFactory] = {
    "local": LocalAuthProvider,
    "supabase": SupabaseAuthProvider,
}


def register_auth_provider(name: str, factory: AuthProviderFactory, *, replace: bool = False) -> None:
    """Register an ``AuthProvider`` factory under ``name``."""
    key = name.strip().lower()
    if not key:
        raise ValueError("Auth provider name must be non-empty")
    if key in _AUTH_PROVIDER_FACTORIES and not replace:
        raise ValueError(f"Duplicate auth provider: {key!r}")
    _AUTH_PROVIDER_FACTORIES[key] = factory


def build_auth_provider(settings: Settings) -> AuthProvider:
    """Instantiate the configured ``AuthProvider`` from application settings."""
    factory = _AUTH_PROVIDER_FACTORIES.get(settings.AUTH_PROVIDER)
    if factory is None:
        raise ValueError(
            f"Unknown AUTH_PROVIDER={settings.AUTH_PROVIDER!r}; registered: {sorted(_AUTH_PROVIDER_FACTORIES)}"
        )
    return factory(settings)


__all__ = [
    "AuthProvider",
    "AuthProviderFactory",
    "LocalAuthProvider",
    "SupabaseAuthProvider",
    "build_auth_provider",
    "register_auth_provider",
]
