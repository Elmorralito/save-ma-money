"""JWT token management and authentication for the API.

Uses self-hosted HS256 JWT issuance and validation with ``Settings.JWT_SECRET_KEY``.

``AuthSecurityManager`` is a process singleton configured once from ``Settings``.
Call :meth:`AuthSecurityManager.reset_instances` after clearing ``get_settings``
cache when tests swap secrets.

Key exports:
    AuthSecurityManager: Issue and validate JWTs for protected routes.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable

import jwt
from jwt.exceptions import PyJWTError

from papita_txnsapi.config.settings import Settings
from papita_txnsmodel.utils.classutils import MetaSingleton

logger = logging.getLogger(__name__)


class AuthSecurityManager(metaclass=MetaSingleton):  # pylint: disable=too-many-instance-attributes
    """Singleton manager for JWT issuance and token decoding."""

    def __init__(self, settings: Settings) -> None:
        self.auth_provider = settings.AUTH_PROVIDER
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.expiration_time = settings.JWT_EXPIRATION_TIME_SECONDS
        self.token_type = settings.JWT_TOKEN_TYPE

    @classmethod
    def reset_instances(cls) -> None:
        """Drop the MetaSingleton instance so the next call re-reads Settings."""
        MetaSingleton._instances.pop(cls, None)  # pylint: disable=protected-access

    def generate_token(self, user_id: str) -> str:
        """Build and encode an HS256 JWT for ``user_id``."""
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

    def authenticate_and_generate_token(
        self,
        username: str,
        password: str,
        verify_credentials: Callable[[str, str], str | None],
    ) -> str | None:
        """Verify credentials via callback and return an access token when valid."""
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
        """Decode and validate an HS256 JWT; return the payload or None if invalid."""
        if not token or not token.strip():
            return None
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
