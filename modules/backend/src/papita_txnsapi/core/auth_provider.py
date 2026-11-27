"""Self-hosted Identity / Auth provider protocol."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, Protocol, runtime_checkable

from papita_txnsapi.config.settings import Settings
from papita_txnsapi.core.auth_health import AuthProbeDetail, AuthProbeResult, probe_local_auth


@runtime_checkable
class AuthProvider(Protocol):
    """Protocol for authentication providers."""

    @property
    def provider_name(self) -> Literal["local"]:
        """Active provider slug."""

    @property
    def supports_external_sessions(self) -> bool:
        """Whether this provider delegates session refresh/sign-out externally."""

    def probe_health(self, *, probe_fn: Callable[..., AuthProbeResult] | None = None) -> AuthProbeResult:
        """Run a readiness probe against the auth backend."""


class LocalAuthProvider:
    """Self-hosted HS256 JWT + direct Google OAuth PKCE auth provider."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def provider_name(self) -> Literal["local"]:
        return "local"

    @property
    def supports_external_sessions(self) -> bool:
        return False

    def probe_health(self, *, probe_fn: Callable[..., AuthProbeResult] | None = None) -> AuthProbeResult:
        if probe_fn is not None:
            return probe_fn(auth_provider="local")
        return probe_local_auth(auth_provider="local")


AuthProviderFactory = Callable[[Settings], AuthProvider]

_AUTH_PROVIDER_FACTORIES: dict[str, AuthProviderFactory] = {
    "local": LocalAuthProvider,
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
    factory = _AUTH_PROVIDER_FACTORIES.get(settings.AUTH_PROVIDER) or LocalAuthProvider
    return factory(settings)


__all__ = [
    "AuthProbeDetail",
    "AuthProvider",
    "AuthProviderFactory",
    "LocalAuthProvider",
    "build_auth_provider",
    "register_auth_provider",
]
