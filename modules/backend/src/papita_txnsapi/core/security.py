"""JWT token management and authentication for the API.

Supports two modes via ``Settings.AUTH_PROVIDER``:

* ``local`` — HS256 issue/verify with ``JWT_SECRET_KEY`` (tests / transitional B0).
* ``supabase`` — verify Supabase access JWTs via JWKS (``SUPABASE_URL``); does not
  mint API-owned access tokens.

``AuthSecurityManager`` is a process singleton configured once from ``Settings``.
Call :meth:`AuthSecurityManager.reset_instances` after clearing ``get_settings``
cache when tests swap provider or secrets.

Key exports:
    AuthSecurityManager: Issue (local) and validate JWTs for protected routes.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable
from urllib.parse import urlparse

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

from papita_txnsapi.config.settings import Settings
from papita_txnsmodel.utils.classutils import MetaSingleton

logger = logging.getLogger(__name__)


def supabase_issuer(supabase_url: str) -> str:
    """Return the expected JWT ``iss`` claim for a Supabase project URL.

    Args:
        supabase_url: Project URL such as ``https://xyz.supabase.co``.

    Returns:
        Issuer string ``{origin}/auth/v1``.
    """
    parsed = urlparse(supabase_url.rstrip("/"))
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return f"{origin}/auth/v1"


def supabase_jwks_url(supabase_url: str) -> str:
    """Return the JWKS URL for Supabase Auth asymmetric JWT verification.

    Args:
        supabase_url: Project URL such as ``https://xyz.supabase.co``.

    Returns:
        ``{origin}/auth/v1/.well-known/jwks.json``.
    """
    return f"{supabase_issuer(supabase_url)}/.well-known/jwks.json"


class AuthSecurityManager(metaclass=MetaSingleton):  # pylint: disable=too-many-instance-attributes
    """Singleton manager for JWT issuance (local) and token decoding.

    Reads signing / verification parameters from ``Settings`` on construction.
    Subsequent calls with the same class reuse the shared instance via
    ``MetaSingleton`` — call :meth:`reset_instances` when settings change in tests.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize auth parameters from application settings.

        Args:
            settings: API settings supplying provider, secret, and Supabase URL.
        """
        self.auth_provider = settings.AUTH_PROVIDER
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.expiration_time = settings.JWT_EXPIRATION_TIME_SECONDS
        self.token_type = settings.JWT_TOKEN_TYPE
        self.supabase_url = (settings.SUPABASE_URL or "").rstrip("/")
        self.supabase_jwt_audience = settings.SUPABASE_JWT_AUDIENCE
        self._jwks_client: PyJWKClient | None = None
        if self.auth_provider == "supabase" and self.supabase_url:
            self._jwks_client = PyJWKClient(supabase_jwks_url(self.supabase_url), cache_keys=True)

    @classmethod
    def reset_instances(cls) -> None:
        """Drop the MetaSingleton instance so the next call re-reads Settings."""
        MetaSingleton._instances.pop(cls, None)  # pylint: disable=protected-access

    def generate_token(self, user_id: str) -> str:
        """Build and encode a local HS256 JWT (``AUTH_PROVIDER=local`` only).

        Args:
            user_id: Subject identifier to embed in the token.

        Returns:
            Encoded JWT string.

        Raises:
            RuntimeError: When ``AUTH_PROVIDER`` is ``supabase`` (API must not mint
                access tokens; clients obtain them from Supabase Auth).
        """
        if self.auth_provider != "local":
            message = (
                "Local JWT issuance is disabled when AUTH_PROVIDER=supabase; "
                + "obtain access tokens from Supabase Auth"
            )
            raise RuntimeError(message)
        now = datetime.now(timezone.utc)
        exp = now + timedelta(seconds=self.expiration_time)
        payload = {
            "sub": user_id,
            "exp": exp,
            "iat": now,
            "type": self.token_type,
        }
        return jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm,
        )

    def authenticate_and_get_token(
        self,
        username: str,
        password: str,
        verify_credentials: Callable[[str, str], str | None],
    ) -> str | None:
        """Verify credentials; if valid, return a local JWT for the user.

        Args:
            username: Username or identifier (e.g. email).
            password: Plain-text password.
            verify_credentials: Callable that takes (username, password) and returns
                user_id if valid, None otherwise.

        Returns:
            JWT string if authentication succeeds, None otherwise.
        """
        if not username or not password:
            logger.debug("Authentication skipped: missing username or password")
            return None
        user_id = verify_credentials(username, password)
        if user_id is None:
            logger.debug("Authentication failed for username=%s", username)
            return None
        token = self.generate_token(user_id)
        logger.debug("Token generated for user_id=%s", user_id)
        return token

    def decode_token(self, token: str, *, expected_type: str | None = None) -> dict | None:
        """Decode and validate a JWT; return the payload or None if invalid.

        Local mode checks HS256 signature and optional ``type`` claim. Supabase mode
        verifies via JWKS (``aud`` / ``iss`` / ``sub``) and ignores local ``type``.

        Args:
            token: Encoded JWT string.
            expected_type: When set in local mode, reject tokens whose ``type`` claim
                does not match. Ignored for Supabase tokens.

        Returns:
            Payload dict with at least ``sub``, or None if decode/validation fails.
        """
        if not token or not token.strip():
            return None
        if self.auth_provider == "supabase":
            return self._decode_supabase_token(token)
        return self._decode_local_token(token, expected_type=expected_type)

    def _decode_local_token(self, token: str, *, expected_type: str | None) -> dict | None:
        """Validate an HS256 token minted by this API."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            if expected_type is not None and payload.get("type") != expected_type:
                logger.debug("Token type mismatch: expected=%s got=%s", expected_type, payload.get("type"))
                return None
            return payload
        except PyJWTError as exc:
            logger.debug("Token decode failed: %s", exc)
            return None

    def _decode_supabase_token(self, token: str) -> dict | None:
        """Validate a Supabase Auth access JWT via JWKS."""
        if self._jwks_client is None or not self.supabase_url:
            logger.error("Supabase JWT verification requires SUPABASE_URL and JWKS client")
            return None
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=self.supabase_jwt_audience,
                issuer=supabase_issuer(self.supabase_url),
            )
            if "sub" not in payload:
                return None
            return payload
        except PyJWTError as exc:
            logger.debug("Supabase token decode failed: %s", exc)
            return None
