"""FastAPI dependencies for JWT user sessions, credential checks, and sliding refresh.

Session **creation** uses :class:`~papita_txnsapi.core.security.auth.AuthSecurityManager`
with password verification via :class:`~papita_txnsapi.core.security.hashing.AbstractPasswordManager`
(Argon2 through :class:`~papita_txnsapi.core.security.hashing.PasswordManagerFactory`).

**Review** validates the ``Authorization: Bearer`` token and exposes :class:`UserSession`.

**Keeping sessions alive** is optional: when ``JWT_SLIDING_REFRESH_ENABLED`` is true and
time-to-expiry is at or below ``JWT_REFRESH_THRESHOLD_SECONDS``, the dependency sets
``X-New-Access-Token`` on the response with a new JWT (same subject).

Note:
    Stored ``users.password`` values must be Argon2 hashes compatible with the API
    password manager (not legacy SHA-256 digests from other code paths).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from papita_txnsapi.core.security.auth import AuthSecurityManager
from papita_txnsapi.core.settings import APISettings, get_settings
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.access.users.repository import UsersRepository
from papita_txnsmodel.helpers.hashing.abstract import AbstractPasswordManager
from papita_txnsmodel.helpers.hashing.factory import PasswordManagerFactory
from papita_txnsmodel.model.users import Users

logger = logging.getLogger(__name__)

REFRESH_TOKEN_HEADER = "X-New-Access-Token"

_http_bearer_optional = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class UserSession:
    """Authenticated context derived from a validated JWT."""

    user_id: str
    payload: dict[str, Any]


def get_auth_security_manager(
    settings: Annotated[APISettings, Depends(get_settings)],
) -> AuthSecurityManager:
    """Return the singleton :class:`AuthSecurityManager` for the app settings."""
    return AuthSecurityManager(settings)


def get_password_manager() -> AbstractPasswordManager:
    """Return the API-layer Argon2 (or configured) password manager singleton."""
    return PasswordManagerFactory().password_manager


def get_verify_credentials(
    password_manager: Annotated[AbstractPasswordManager, Depends(get_password_manager)],
) -> Callable[[str, str], str | None]:
    """
    Build ``verify_credentials`` for :meth:`AuthSecurityManager.authenticate_and_get_token`.

    Looks up the user by username, checks active / not soft-deleted, and verifies the
    password with the API password manager against the stored hash.
    """

    def verify(username: str, password: str) -> str | None:
        if not username or not password:
            return None
        repo = UsersRepository()
        df = repo.get_records(Users.username == username.strip(), dto_type=UsersDTO)
        if getattr(df, "empty", True):
            logger.debug("No user found for username=%s", username)
            return None
        row = df.iloc[0]
        stored_hash = row.get("password")
        if stored_hash is None or (isinstance(stored_hash, float) and str(stored_hash) == "nan"):
            return None
        stored_hash_str = str(stored_hash)
        is_active = bool(row.get("active", True))
        deleted_at = row.get("deleted_at")
        if not is_active or deleted_at is not None:
            logger.debug("User inactive or deleted username=%s", username)
            return None
        if not password_manager.verify_password(password, stored_hash_str):
            return None
        user_id = row.get("id")
        return str(user_id) if user_id is not None else None

    return verify


VerifyCredentialsDep = Annotated[Callable[[str, str], str | None], Depends(get_verify_credentials)]


def get_issue_session_token(
    auth: Annotated[AuthSecurityManager, Depends(get_auth_security_manager)],
    verify_credentials: VerifyCredentialsDep,
) -> Callable[[str, str], str | None]:
    """Return a callable ``(username, password) -> jwt | None`` for login flows."""

    def issue(username: str, password: str) -> str | None:
        return auth.authenticate_and_get_token(username, password, verify_credentials)

    return issue


SessionTokenIssuerDep = Annotated[Callable[[str, str], str | None], Depends(get_issue_session_token)]


def get_optional_bearer_credentials(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_http_bearer_optional),
    ],
) -> HTTPAuthorizationCredentials | None:
    """Return bearer credentials when present; does not raise."""
    return credentials


def get_bearer_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_http_bearer_optional),
    ],
) -> str:
    """Require a non-empty Bearer token or respond with 401."""
    if credentials is None or not credentials.credentials or not credentials.credentials.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials.strip()


def _seconds_until_expiry(exp_claim: Any) -> float | None:
    if exp_claim is None:
        return None
    now = datetime.now(timezone.utc)
    if isinstance(exp_claim, (int, float)):
        exp_dt = datetime.fromtimestamp(float(exp_claim), tz=timezone.utc)
    elif isinstance(exp_claim, datetime):
        exp_dt = exp_claim if exp_claim.tzinfo else exp_claim.replace(tzinfo=timezone.utc)
    else:
        return None
    return (exp_dt - now).total_seconds()


def _session_from_token(token: str, auth: AuthSecurityManager, settings: APISettings) -> UserSession:
    payload = auth.decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("type") != settings.JWT_TOKEN_TYPE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    sub = payload.get("sub")
    if sub is None or not str(sub).strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UserSession(user_id=str(sub), payload=payload)


def get_current_user_session(
    token: Annotated[str, Depends(get_bearer_token)],
    auth: Annotated[AuthSecurityManager, Depends(get_auth_security_manager)],
    settings: Annotated[APISettings, Depends(get_settings)],
) -> UserSession:
    """Validate JWT and return :class:`UserSession` (401 if missing/invalid)."""
    return _session_from_token(token, auth, settings)


def get_current_user_session_kept_alive(
    response: Response,
    token: Annotated[str, Depends(get_bearer_token)],
    auth: Annotated[AuthSecurityManager, Depends(get_auth_security_manager)],
    settings: Annotated[APISettings, Depends(get_settings)],
) -> UserSession:
    """
    Same as :func:`get_current_user_session`, plus sliding refresh when enabled.

    When ``JWT_SLIDING_REFRESH_ENABLED`` is true and remaining lifetime is at or below
    ``JWT_REFRESH_THRESHOLD_SECONDS``, sets ``X-New-Access-Token`` on the response.
    """
    session = _session_from_token(token, auth, settings)
    if not settings.JWT_SLIDING_REFRESH_ENABLED:
        return session
    remaining = _seconds_until_expiry(session.payload.get("exp"))
    if remaining is None:
        return session
    if remaining <= settings.JWT_REFRESH_THRESHOLD_SECONDS:
        renewed = auth.generate_token(session.user_id)
        response.headers[REFRESH_TOKEN_HEADER] = renewed
    return session


def get_optional_user_session(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_http_bearer_optional),
    ],
    auth: Annotated[AuthSecurityManager, Depends(get_auth_security_manager)],
    settings: Annotated[APISettings, Depends(get_settings)],
) -> UserSession | None:
    """Return :class:`UserSession` when a valid Bearer token is sent; otherwise ``None``."""
    if credentials is None or not credentials.credentials or not credentials.credentials.strip():
        return None
    token = credentials.credentials.strip()
    payload = auth.decode_token(token)
    if payload is None:
        return None
    if payload.get("type") != settings.JWT_TOKEN_TYPE:
        return None
    sub = payload.get("sub")
    if sub is None or not str(sub).strip():
        return None
    return UserSession(user_id=str(sub), payload=payload)


AuthSecurityManagerDep = Annotated[AuthSecurityManager, Depends(get_auth_security_manager)]
PasswordManagerDep = Annotated[AbstractPasswordManager, Depends(get_password_manager)]

CurrentUserSessionDep = Annotated[UserSession, Depends(get_current_user_session)]
CurrentUserSessionKeptAliveDep = Annotated[UserSession, Depends(get_current_user_session_kept_alive)]
OptionalUserSessionDep = Annotated[UserSession | None, Depends(get_optional_user_session)]

__all__ = [
    "REFRESH_TOKEN_HEADER",
    "AuthSecurityManagerDep",
    "CurrentUserSessionDep",
    "CurrentUserSessionKeptAliveDep",
    "OptionalUserSessionDep",
    "PasswordManagerDep",
    "SessionTokenIssuerDep",
    "UserSession",
    "VerifyCredentialsDep",
    "get_auth_security_manager",
    "get_bearer_token",
    "get_current_user_session",
    "get_current_user_session_kept_alive",
    "get_issue_session_token",
    "get_optional_bearer_credentials",
    "get_optional_user_session",
    "get_password_manager",
    "get_verify_credentials",
]
