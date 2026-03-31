"""
JWT token management and authentication for the API.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable

from jose import JWTError, jwt

from papita_txnsapi.core.settings import APISettings
from papita_txnsmodel.utils.classutils import MetaSingleton

logger = logging.getLogger(__name__)


class AuthSecurityManager(metaclass=MetaSingleton):
    """
    Token manager that authenticates credentials and issues JWT tokens on success.
    """

    def __init__(self, settings: APISettings) -> None:
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.expiration_time = timedelta(seconds=settings.JWT_EXPIRATION_TIME_SECONDS)
        self.token_type = settings.JWT_TOKEN_TYPE

    def generate_token(self, user_id: str) -> str:
        """
        Build a JWT payload and encode it with the configured secret and algorithm.

        Args:
            user_id: Subject identifier to embed in the token.

        Returns:
            Encoded JWT string.
        """
        now = datetime.now(timezone.utc)
        exp = now + self.expiration_time
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
        """
        Verify credentials; if valid, return a JWT for the corresponding user.

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

    def decode_token(self, token: str) -> dict | None:
        """
        Decode and validate a JWT; return the payload or None if invalid.

        Args:
            token: Encoded JWT string.

        Returns:
            Payload dict with at least 'sub' and 'exp', or None if decode/validation fails.
        """
        if not token or not token.strip():
            return None
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            return payload
        except JWTError as exc:
            logger.debug("Token decode failed: %s", exc)
            return None

    def renew_access_token(self, token: str) -> str | None:
        """
        If the token is valid, issue a new access token for the same subject.

        Used for sliding sessions without trusting an expired token.

        Args:
            token: Current bearer token.

        Returns:
            A new JWT string, or None if the token is invalid.
        """
        payload = self.decode_token(token)
        if payload is None:
            return None
        user_id = payload.get("sub")
        if user_id is None or not str(user_id).strip():
            return None
        return self.generate_token(str(user_id))
