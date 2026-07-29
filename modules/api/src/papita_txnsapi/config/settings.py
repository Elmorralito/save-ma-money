# type: ignore
"""Environment-backed application settings for the Papita Transactions API.

Loads configuration from ``environments/$PAPITA_ENV/.env`` (see
:mod:`papita_txnsapi.config.environment`) via Pydantic Settings. Establishes the
shared SQLAlchemy connector, configures model and API loggers, and exposes JWT,
CORS, database pool, and auth rate-limit parameters consumed by
:mod:`papita_txnsapi.main` and FastAPI dependencies.
"""

from __future__ import annotations

import logging
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Self, Type
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from papita_txnsapi import LIB_NAME as API_LIB_NAME
from papita_txnsapi import __version__ as API_VERSION
from papita_txnsapi.config.environment import ENV_VAR_NAME, active_environment, env_file_for_settings
from papita_txnsmodel import LIB_NAME as MODEL_LIB_NAME
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.configutils import configure_logger
from papita_txnsmodel.utils.enums import FallbackAction

JWT_SECRET_MIN_LENGTH = 32
JWT_ALGORITHM_ALLOWLIST = frozenset({"HS256"})
# Secure PPT-044 defaults (overridable via Settings for ops tuning / migration).
MAX_REPORT_WINDOW_DAYS = 366
MAX_BULK_TRANSACTIONS = 100
MAX_DESCRIPTION_LENGTH = 2_000
MAX_TAG_LENGTH = 64
MAX_TAGS_PER_TRANSACTION = 20
MAX_SEARCH_LENGTH = 256
MAX_EXTENSION_STRING_LENGTH = 255
# Temporary bulk ceiling when operators raise API_BULK_MAX_TRANSACTIONS during migration.
MAX_BULK_TRANSACTIONS_HARD_CAP = 500

# API package root (modules/api/src) — logger YAML only; secrets live under environments/.
PROJECT_ROOT = Path(__file__).parent.parent.parent
LOGGER_CONFIG_PATH = Path(__file__).parent / "logger.yaml"

logger = logging.getLogger(API_LIB_NAME)


def is_supabase_transaction_pooler_url(url: str) -> bool:
    """Return True when ``url`` targets a Supabase transaction pooler (B1).

    Args:
        url: SQLAlchemy / PostgreSQL connection URL.

    Returns:
        True for ``:6543``, ``*.pooler.supabase.com``, or ``pgbouncer=true`` query.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host == "pooler.supabase.com" or host.endswith(".pooler.supabase.com"):
        return True
    if parsed.port == 6543:
        return True
    return "pgbouncer=true" in url.lower()


def postgres_engine_kwargs(*, url: str, pool_size: int) -> dict:
    """Build SQLAlchemy ``create_engine`` kwargs for PostgreSQL (PPT-039).

    Always enables ``pool_pre_ping``. Uses a bounded ``pool_size`` from Settings.
    On transaction-pooler URLs, sets ``max_overflow=0`` so workers do not burst
    extra connections against PgBouncer transaction mode.

    Args:
        url: PostgreSQL SQLAlchemy URL.
        pool_size: Configured ``DATABASE_POOL_SIZE``.

    Returns:
        Keyword arguments passed to :meth:`SQLDatabaseConnector.establish`.
    """
    kwargs: dict = {"pool_pre_ping": True, "pool_size": pool_size}
    if is_supabase_transaction_pooler_url(url):
        kwargs["max_overflow"] = 0
    return kwargs


class Settings(BaseSettings):
    """Runtime configuration loaded from process env and ``environments/$PAPITA_ENV/.env``.

    Set ``PAPITA_ENV`` to ``local`` (default), ``staging``, or ``production``. Prefer
    ``get_settings()`` so the correct env file is bound for the active environment.

    Attributes:
        APP_NAME: Human-readable application title used in startup logs.
        APP_VERSION: Semantic version re-exported from package metadata.
        DEBUG: When ``True``, enables verbose diagnostics (reserved for future use).
        HOST: Unused for process bind (PPT-045). Compose image ``CMD`` binds
            ``0.0.0.0:8000``; kept for env-file compatibility only.
        PORT: Unused for process bind (PPT-045). See ``HOST``; host publish uses
            Compose ``API_PORT``, not this field.
        DATABASE_URL: PostgreSQL SQLAlchemy URL or an established connector class.
            When unset, falls back to the model default storage with a warning.
        LOG_LEVEL: Root log level applied to model and API loggers on init.
        LOG_FILE: Optional path to a logging YAML file; defaults to ``logger.yaml``.
        DATABASE_POOL_SIZE: SQLAlchemy connection pool size for PostgreSQL
            (wired into ``create_engine`` via PPT-039; default 5).
        JWT_SECRET_KEY: Symmetric signing key for local HS256 tokens (required when
            ``AUTH_PROVIDER=local``; unused for verification when ``supabase``).
        JWT_TOKEN_TYPE: Expected ``type`` claim for local bearer tokens.
        JWT_ALGORITHM: Local JWT signing algorithm (default HS256).
        JWT_EXPIRATION_TIME_SECONDS: Local access token lifetime in seconds.
        AUTH_PROVIDER: ``local`` (API-issued HS256) or ``supabase`` (JWKS verify).
        SUPABASE_URL: Project URL for JWKS / Auth API when ``AUTH_PROVIDER=supabase``.
        SUPABASE_ANON_KEY: Optional anon key for register/login pass-through.
        SUPABASE_JWT_AUDIENCE: Expected ``aud`` claim (default ``authenticated``).
        ALLOWED_ORIGINS: CORS allowed origins list (``*`` only when ``DEBUG=true``).
        ALLOWED_HOSTS: TrustedHost allowlist; required (non-empty) when ``DEBUG=false``.
        DOCS_ENABLED: Expose ``/api/docs``, ``/api/redoc``, and ``/api/openapi.json``.
        FALLBACK_ACTION: Behavior when optional model fallbacks trigger.
        AUTH_RATE_LIMIT_ENABLED: Toggle per-IP auth endpoint rate limiting (B0).
        AUTH_RATE_LIMIT_FAIL_CLOSED: When Redis auth limits error, deny (``True``) or allow.
        AUTH_RATE_LIMIT_WINDOW_SECONDS: Sliding window length for auth limits.
        AUTH_LOGIN_RATE_LIMIT_PER_MINUTE: Max login attempts per window per IP.
        AUTH_REGISTER_RATE_LIMIT_PER_MINUTE: Max register attempts per window per IP.
        HEALTH_RATE_LIMIT_ENABLED: Toggle per-IP limits on DB-touching health probes.
        HEALTH_RATE_LIMIT_PER_MINUTE: Max health/ready/database/auth/redis probes per IP.
        HEALTH_PROBE_TIMEOUT_MS: Session-local statement timeout for database probes.
        REDIS_URL: Redis connection URL when shared infra is enabled (PPT-043).
        REDIS_ENABLED: When ``True``, initialize a Redis pool and include Redis in readiness.
        REDIS_DEFAULT_TTL_SECONDS: Legacy unused fallback; prefer per-namespace TTLs.
        REDIS_CACHE_TTL_ACCOUNTS_SECONDS: Cache TTL for accounts list (default 60s).
        REDIS_CACHE_TTL_CATEGORIES_SECONDS: Cache TTL for categories list (default 300s).
        REDIS_CACHE_TTL_REPORTS_SECONDS: Cache TTL for reports (default 180s; range 120–300).
        REDIS_CACHE_TTL_TRANSACTIONS_SECONDS: Short cache TTL for transactions (default 15s).
        REDIS_IDEMPOTENCY_TTL_SECONDS: TTL for ``Idempotency-Key`` replay records.
        REDIS_RATE_LIMIT_ENABLED: When ``True`` (and Redis enabled), use distributed rate limits.
        REDIS_MAX_CONNECTIONS: Max connections in the Redis pool.
        API_RATE_LIMIT_ENABLED: Tenant-scoped Free/Pro/Enterprise API quotas on protected routes.
        API_RATE_LIMIT_DEFAULT_TIER: Default plan when no Redis ``papita:{env}:{owner_id}:api_tier`` override.
        API_RATE_LIMIT_FREE_PER_MINUTE: Free tier requests per rolling minute.
        API_RATE_LIMIT_FREE_PER_DAY: Free tier requests per rolling day.
        API_RATE_LIMIT_PRO_PER_MINUTE: Pro tier requests per rolling minute.
        API_RATE_LIMIT_PRO_PER_DAY: Pro tier requests per rolling day.
        API_BULK_MAX_TRANSACTIONS: Max items in ``POST /transactions/bulk`` (1–500).
        API_REPORT_WINDOW_MAX_DAYS: Max inclusive span for report date windows.
        API_COMPAT_LEGACY_REPORT_ACCOUNT_400: Temporary: foreign report account → 400.
        API_COMPAT_LEGACY_REFRESH_BALANCES_DEFAULT_TRUE: Temporary: omit → refresh true.
    """

    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    # Application
    APP_NAME: str = "Save Ma Money API"
    APP_VERSION: str = API_VERSION
    DEBUG: bool = False
    DOCS_ENABLED: bool = False

    # Server bind metadata only — uvicorn listen address comes from Dockerfile CMD (PPT-045).
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str | Type[SQLDatabaseConnector] | None = None
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FILE: str | None = None
    DATABASE_POOL_SIZE: int = 5
    JWT_SECRET_KEY: str = "local-dev-only-replace-me-min-32-chars"
    JWT_TOKEN_TYPE: Literal["bearer", "refresh"] = "bearer"
    JWT_ALGORITHM: Literal["HS256"] = "HS256"
    JWT_EXPIRATION_TIME_SECONDS: int = 3600
    AUTH_PROVIDER: Literal["local", "supabase"] = "local"
    SUPABASE_URL: str | None = None
    SUPABASE_ANON_KEY: str | None = None
    # Server-only; used to delete orphan Auth users after failed provision.
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    SUPABASE_JWT_AUDIENCE: str = "authenticated"
    SUPABASE_OAUTH_REDIRECT_TO: str | None = None
    ALLOWED_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"])
    ALLOWED_HOSTS: list[str] = Field(default_factory=list)
    FALLBACK_ACTION: FallbackAction = FallbackAction.LOG

    # Auth hardening — per-IP sliding window (Redis when REDIS_RATE_LIMIT_ENABLED)
    AUTH_RATE_LIMIT_ENABLED: bool = True
    AUTH_RATE_LIMIT_FAIL_CLOSED: bool = False
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60
    AUTH_LOGIN_RATE_LIMIT_PER_MINUTE: int = 10
    AUTH_REGISTER_RATE_LIMIT_PER_MINUTE: int = 5
    AUTH_OAUTH_RATE_LIMIT_PER_MINUTE: int = 20
    # When None, OAuth PKCE cookies use Secure when DEBUG is false.
    AUTH_COOKIE_SECURE: bool | None = None
    # BFF HttpOnly session cookie lifetime (PPT-049). Memory store when Redis off.
    BFF_SESSION_MAX_AGE_SECONDS: int = Field(default=604_800, ge=60, le=31_536_000)

    # Health / ops probes (PPT-044)
    HEALTH_RATE_LIMIT_ENABLED: bool = True
    HEALTH_RATE_LIMIT_PER_MINUTE: int = 120
    HEALTH_PROBE_TIMEOUT_MS: int = 3_000

    # Redis (PPT-043) — optional; in-memory fallbacks when disabled
    REDIS_URL: str | None = None
    REDIS_ENABLED: bool = False
    REDIS_DEFAULT_TTL_SECONDS: int = 60
    REDIS_CACHE_TTL_ACCOUNTS_SECONDS: int = 60
    REDIS_CACHE_TTL_CATEGORIES_SECONDS: int = 300
    REDIS_CACHE_TTL_REPORTS_SECONDS: int = 180
    REDIS_CACHE_TTL_TRANSACTIONS_SECONDS: int = 15
    REDIS_IDEMPOTENCY_TTL_SECONDS: int = 86_400
    REDIS_RATE_LIMIT_ENABLED: bool = False
    REDIS_MAX_CONNECTIONS: int = 10

    # Tenant API rate limits (README Free / Pro / Enterprise)
    API_RATE_LIMIT_ENABLED: bool = True
    API_RATE_LIMIT_DEFAULT_TIER: Literal["free", "pro", "enterprise"] = "free"
    API_RATE_LIMIT_FREE_PER_MINUTE: int = 60
    API_RATE_LIMIT_FREE_PER_DAY: int = 1_000
    API_RATE_LIMIT_PRO_PER_MINUTE: int = 300
    API_RATE_LIMIT_PRO_PER_DAY: int = 10_000

    # PPT-044 client-contract knobs (secure defaults; compat flags are temporary)
    API_BULK_MAX_TRANSACTIONS: int = Field(default=MAX_BULK_TRANSACTIONS, ge=1, le=MAX_BULK_TRANSACTIONS_HARD_CAP)
    API_REPORT_WINDOW_MAX_DAYS: int = Field(default=MAX_REPORT_WINDOW_DAYS, ge=1, le=3_660)
    API_COMPAT_LEGACY_REPORT_ACCOUNT_400: bool = False
    API_COMPAT_LEGACY_REFRESH_BALANCES_DEFAULT_TRUE: bool = False

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def coerce_database_url(
        cls, value: str | Type[SQLDatabaseConnector] | None
    ) -> str | Type[SQLDatabaseConnector] | None:
        """Accept a connector class, a non-empty URL string, or ``None``.

        Engine establishment is deferred to :meth:`build_model` so ``DATABASE_POOL_SIZE``
        and pooler-safe options can be applied together (PPT-039).

        Args:
            value: Raw env string, an already-established connector class, or ``None``.

        Returns:
            Normalized URL string, connector class, or ``None``.
        """
        if isinstance(value, type) and issubclass(value, SQLDatabaseConnector):
            return value
        if isinstance(value, str) and value.strip() != "":
            return value.strip()
        return None

    @field_validator("SUPABASE_URL", mode="before")
    @classmethod
    def coerce_supabase_url(cls, value: str | None) -> str | None:
        """Normalize blank Supabase URLs to ``None``.

        Args:
            value: Raw env string or ``None``.

        Returns:
            Stripped URL or ``None``.
        """
        if value is None:
            return None
        if isinstance(value, str) and value.strip() != "":
            return value.strip().rstrip("/")
        return None

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def coerce_redis_url(cls, value: str | None) -> str | None:
        """Normalize blank Redis URLs to ``None``.

        Args:
            value: Raw env string or ``None``.

        Returns:
            Stripped URL or ``None``.
        """
        if value is None:
            return None
        if isinstance(value, str) and value.strip() != "":
            return value.strip()
        return None

    @model_validator(mode="before")
    @classmethod
    def prefer_supabase_when_url_configured(cls, data: Any) -> Any:
        """Default ``AUTH_PROVIDER=supabase`` when ``SUPABASE_URL`` is set and provider unset.

        Keeps explicit ``AUTH_PROVIDER=local`` for unit tests. Staging/local env files
        that only set ``SUPABASE_URL`` (+ anon key) activate Auth without a second flag.

        Args:
            data: Raw settings input mapping.

        Returns:
            Input with ``AUTH_PROVIDER`` filled when applicable.
        """
        if not isinstance(data, dict):
            return data
        provider = data.get("AUTH_PROVIDER")
        if provider is not None and str(provider).strip() != "":
            return data
        url = data.get("SUPABASE_URL")
        if isinstance(url, str) and url.strip() != "":
            return {**data, "AUTH_PROVIDER": "supabase"}
        return data

    @field_validator("JWT_ALGORITHM", mode="before")
    @classmethod
    def allowlist_jwt_algorithm(cls, value: str | None) -> str:
        """Reject JWT algorithms outside the local HS256 allowlist.

        Args:
            value: Raw algorithm string from env or constructor.

        Returns:
            Normalized algorithm name.

        Raises:
            ValueError: When the algorithm is missing or not allowlisted.
        """
        algorithm = (value or "").strip().upper()
        if algorithm not in JWT_ALGORITHM_ALLOWLIST:
            allowed = ", ".join(sorted(JWT_ALGORITHM_ALLOWLIST))
            raise ValueError(f"JWT_ALGORITHM must be one of: {allowed}")
        return algorithm

    @model_validator(mode="after")
    def build_model(self) -> Self:
        """Validate Auth provider config, establish DB connector, configure loggers.

        Returns:
            The validated settings instance with ``DATABASE_URL`` as a connector class.

        Raises:
            ValueError: When ``AUTH_PROVIDER=supabase`` without ``SUPABASE_URL``,
                when ``REDIS_ENABLED`` without ``REDIS_URL``, when production CORS
                uses ``*``, or when local JWT secret is shorter than the minimum.
        """
        if self.AUTH_PROVIDER == "supabase" and not self.SUPABASE_URL:
            raise ValueError("SUPABASE_URL is required when AUTH_PROVIDER=supabase")
        if self.REDIS_ENABLED and not self.REDIS_URL:
            raise ValueError("REDIS_URL is required when REDIS_ENABLED=true")
        if not self.DEBUG and "*" in self.ALLOWED_ORIGINS:
            raise ValueError("ALLOWED_ORIGINS cannot include '*' when DEBUG=false (CORS credentials)")
        if not self.DEBUG and not [host for host in self.ALLOWED_HOSTS if str(host).strip()]:
            raise ValueError("ALLOWED_HOSTS must be non-empty when DEBUG=false (TrustedHost)")
        if self.AUTH_PROVIDER == "local" and len(self.JWT_SECRET_KEY.strip()) < JWT_SECRET_MIN_LENGTH:
            raise ValueError(
                f"JWT_SECRET_KEY must be at least {JWT_SECRET_MIN_LENGTH} characters when AUTH_PROVIDER=local"
            )
        if not self.DEBUG and self.LOG_LEVEL == "DEBUG":
            object.__setattr__(self, "LOG_LEVEL", "INFO")

        url_or_connector = self.DATABASE_URL
        if isinstance(url_or_connector, type) and issubclass(url_or_connector, SQLDatabaseConnector):
            connector: Type[SQLDatabaseConnector] = url_or_connector
        elif isinstance(url_or_connector, str):
            connector = SQLDatabaseConnector.establish(
                connection=url_or_connector,
                **postgres_engine_kwargs(url=url_or_connector, pool_size=self.DATABASE_POOL_SIZE),
            )
        else:
            warnings.warn(
                "The connection has been set with the default storage option, since the provided DATABASE_URL is None",
                stacklevel=2,
            )
            connector = SQLDatabaseConnector.establish(connection=None)

        object.__setattr__(self, "DATABASE_URL", connector)

        log_config = Path(self.LOG_FILE) if self.LOG_FILE else LOGGER_CONFIG_PATH
        configure_logger(logger_name=MODEL_LIB_NAME, config=log_config, level=self.LOG_LEVEL)
        configure_logger(logger_name=API_LIB_NAME, config=log_config, level=self.LOG_LEVEL)
        logger.info(
            "Application %s %s initialized (AUTH_PROVIDER=%s)",
            self.APP_NAME,
            self.APP_VERSION,
            self.AUTH_PROVIDER,
        )
        return self

    def oauth_cookie_secure(self) -> bool:
        """Whether OAuth PKCE cookies should set the Secure flag.

        Returns:
            Explicit ``AUTH_COOKIE_SECURE`` when set; otherwise ``not DEBUG``.
        """
        if self.AUTH_COOKIE_SECURE is not None:
            return self.AUTH_COOKIE_SECURE
        return not self.DEBUG


@lru_cache()
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance for dependency injection.

    Loads ``environments/$PAPITA_ENV/.env`` when present; otherwise process env only.
    Clear the cache after changing ``PAPITA_ENV`` in tests.

    Returns:
        Singleton settings for the active :data:`PAPITA_ENV`.
    """
    env_path = env_file_for_settings()
    if env_path is not None:
        logger.debug("Loading settings from %s (%s=%s)", env_path, ENV_VAR_NAME, active_environment())
        return Settings(_env_file=env_path)
    return Settings()
