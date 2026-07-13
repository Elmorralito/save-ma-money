"""Users service module for the Papita Transactions system.

This module provides the UsersService class which implements operations for
managing user entities in the system. It extends the base service functionality
with user-specific configurations and behavior. UsersService is the canonical
service for resolving owner_id to UsersDTO for use as owner= in other services.

Classes:
    UsersService: Service for managing user entities in the system.
"""

import logging
import re
import secrets
import uuid
from typing import Annotated

from pydantic import Field

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.access.users.repository import UsersRepository
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.model.contstants import USERNAME_REGEX
from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.utils.hashutils import Argon2PasswordManager, PasswordManagerFactory

logger = logging.getLogger(__name__)

_USERNAME_RE = re.compile(USERNAME_REGEX)


class UsersService(BaseService):
    """Service for managing user entities in the Papita Transactions system.

    This service extends the base service to provide user-specific functionality.
    It configures the appropriate DTO and repository types for user operations
    and sets upsert parameters for user registration and updates. Use get_owner()
    to resolve an owner_id to a UsersDTO for passing as owner= to other services
    and handlers that use the owner column.

    Attributes:
        dto_type (type[UsersDTO]): Data Transfer Object type for users.
            Set to UsersDTO.
        repository_type (type[UsersRepository]): Repository class for user
            database operations. Set to UsersRepository.
        missing_upsertions_tol (float): Tolerance threshold for missing upsertions.
            Set to 0.01 (1%).
        on_conflict_do (OnUpsertConflictDo | str): Action to take on upsert conflicts.
            Set to OnUpsertConflictDo.UPDATE to update existing user records.
    """

    dto_type: type[UsersDTO] = UsersDTO
    repository_type: type[UsersRepository] = UsersRepository

    missing_upsertions_tol: Annotated[float, Field(ge=0, le=0.5)] = 0.01
    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE

    @staticmethod
    def ensure_password_manager() -> None:
        """Initialize the Argon2 password manager if not already configured.

        Must run before ``UsersDTO`` serialization (register) or ``verify_credentials`` (login).
        Typically called from FastAPI lifespan or at the start of auth service methods.
        """
        PasswordManagerFactory().get_password_manager(keyword="argon2")

    @staticmethod
    def _build_login_probe(identifier: str) -> UsersDTO | None:
        """Build a partial UsersDTO probe from a username or email identifier.

        Args:
            identifier: Raw login string (username or email).

        Returns:
            UsersDTO probe for repository lookup, or None when identifier is blank.
        """
        normalized = identifier.strip()
        if not normalized:
            return None

        if "@" in normalized:
            return UsersDTO.model_construct(email=normalized.lower())
        return UsersDTO.model_construct(username=normalized)

    def _lookup_by_identifier(self, identifier: str, *, require_active: bool = False) -> UsersDTO | None:
        """Look up a user by username or email.

        Args:
            identifier: Raw login string from the OAuth2 ``username`` form field or register payload.
            require_active: When True, exclude inactive or soft-deleted users.

        Returns:
            UsersDTO if a matching user exists under the filter, otherwise None.
        """
        probe = self._build_login_probe(identifier)
        if probe is None:
            return None

        user = self._repository.get_record_from_attributes(probe, dto_type=UsersDTO)
        if user is None:
            return None
        if require_active and (not user.active or user.deleted_at is not None):
            return None
        return user

    def _find_by_login_identifier(self, identifier: str) -> UsersDTO | None:
        """Look up an active user by username or email.

        Args:
            identifier: Raw login string from the OAuth2 ``username`` form field.

        Returns:
            UsersDTO if a matching active user exists, otherwise None.
        """
        return self._lookup_by_identifier(identifier, require_active=True)

    def _persist_password_hash(self, user: UsersDTO, password_hash: str) -> UsersDTO:
        """Persist an already-hashed password without re-running plain-text serialization."""
        updated = UsersDTO.model_construct(
            id=user.id,
            username=user.username,
            email=user.email,
            password=password_hash,
            active=user.active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            deleted_at=user.deleted_at,
        )
        self._repository.upsert_record(updated, owner=None)
        return updated

    def _rehash_password_if_needed(self, user: UsersDTO, plain_password: str) -> UsersDTO:
        """Upgrade Argon2 parameters on login when the stored hash is outdated."""
        password_manager = PasswordManagerFactory().password_manager
        if not isinstance(password_manager, Argon2PasswordManager):
            return user
        if not password_manager.needs_rehash(user.password):
            return user

        new_hash = password_manager.hash_password(plain_password)
        logger.info("Upgrading Argon2 hash parameters for user_id=%s", user.id)
        return self._persist_password_hash(user, new_hash)

    def verify_credentials(self, username_or_email: str, password: str) -> UsersDTO | None:
        """Verify login credentials and return the user on success.

        Accepts either ``users.username`` or ``users.email`` as the login identifier.
        Returns None for unknown users and wrong passwords (same failure path).

        Args:
            username_or_email: Login identifier (OAuth2 form field ``username``).
            password: Plain-text password.

        Returns:
            UsersDTO if credentials are valid, None otherwise.
        """
        if not password:
            return None

        self.ensure_password_manager()
        user = self._find_by_login_identifier(username_or_email)
        if user is None:
            logger.debug("Authentication failed: user not found for identifier")
            return None

        password_manager = PasswordManagerFactory().password_manager
        if not password_manager.verify_password(password, user.password):
            logger.debug("Authentication failed: password mismatch for user_id=%s", user.id)
            return None

        return self._rehash_password_if_needed(user, password)

    def register(self, *, username: str, email: str, password: str) -> UsersDTO:
        """Register a new user after uniqueness checks.

        Args:
            username: Unique username (``USERNAME_REGEX``).
            email: Unique email (``EMAIL_REGEX``).
            password: Plain-text password (``PASSWORD_REGEX``); hashed on persist.

        Returns:
            UsersDTO: The persisted user (password field holds Argon2 hash).

        Raises:
            ValueError: If username or email is already registered.
        """
        self.ensure_password_manager()

        if self._lookup_by_identifier(username, require_active=False):
            raise ValueError("Username already registered")

        if self._lookup_by_identifier(email, require_active=False):
            raise ValueError("Email already registered")

        user = UsersDTO(username=username, email=email, password=password)
        return self.create(obj=user, owner=None)

    def get_owner(self, owner_id: uuid.UUID | str) -> UsersDTO | None:
        """Resolve an owner id to a UsersDTO for use as owner= in other services.

        Use this when you have an owner_id (e.g. from JWT or request context)
        and need a UsersDTO to pass as the owner= argument to create, get_records,
        load, dump, and similar methods on other services and handlers.

        Args:
            owner_id: User id (UUID or string) to resolve.

        Returns:
            UsersDTO if the user exists, None otherwise.
        """
        return self.get(obj=owner_id, owner=None)

    @staticmethod
    def username_from_auth_claims(*, subject: uuid.UUID, email: str, preferred_username: str | None = None) -> str:
        """Derive a local ``users.username`` that satisfies ``USERNAME_REGEX``.

        Prefers ``preferred_username`` when valid; otherwise the email local-part
        sanitized to ``[A-Za-z0-9_]``; finally ``sb_<hex>`` from the Auth subject.

        Args:
            subject: Auth subject UUID (Supabase ``sub``).
            email: Claim or signup email.
            preferred_username: Optional username hint from the client / claims.

        Returns:
            Username string of length 6–255 matching ``USERNAME_REGEX``.
        """
        candidates: list[str] = []
        if preferred_username:
            candidates.append(preferred_username.strip())
        local = (email or "").split("@", 1)[0]
        if local:
            sanitized = re.sub(r"[^A-Za-z0-9_]", "_", local)
            candidates.append(sanitized)
        candidates.append(f"sb_{subject.hex[:20]}")

        for raw in candidates:
            candidate = raw[:255]
            if len(candidate) < 6:
                candidate = (candidate + subject.hex)[:12]
            if _USERNAME_RE.fullmatch(candidate):
                return candidate
        return f"sb_{subject.hex[:20]}"

    def ensure_from_auth_subject(
        self,
        *,
        subject: uuid.UUID,
        email: str,
        username: str | None = None,
    ) -> UsersDTO:
        """Load or create a local user row aligned to an external Auth ``sub``.

        Used for Supabase JWT Bearer flows: the API does not store the Auth
        password; an unusable Argon2 hash is persisted for schema compatibility.

        Args:
            subject: Auth subject UUID to use as ``users.id``.
            email: User email from Auth claims (required for new rows).
            username: Optional preferred username for new rows.

        Returns:
            Active ``UsersDTO`` for ``subject``.

        Raises:
            ValueError: When email is blank, or email/username collide with another user.
        """
        existing = self.get_owner(subject)
        if existing is not None:
            if not existing.active or existing.deleted_at is not None:
                raise ValueError("User is inactive or deleted")
            return existing

        normalized_email = (email or "").strip().lower()
        if not normalized_email:
            raise ValueError("Auth subject is missing email")

        self.ensure_password_manager()
        preferred = self.username_from_auth_claims(
            subject=subject,
            email=normalized_email,
            preferred_username=username,
        )

        email_owner = self._lookup_by_identifier(normalized_email, require_active=False)
        if email_owner is not None and email_owner.id != subject:
            raise ValueError("Email already registered")

        username_owner = self._lookup_by_identifier(preferred, require_active=False)
        if username_owner is not None and username_owner.id != subject:
            # Collision on derived username — fall back to subject-based name.
            preferred = f"sb_{subject.hex[:20]}"
            username_owner = self._lookup_by_identifier(preferred, require_active=False)
            if username_owner is not None and username_owner.id != subject:
                raise ValueError("Username already registered")

        # Plain random password is hashed once on DTO serialize; Auth password stays in Supabase.
        # Must satisfy PASSWORD_REGEX charset (``@$!%*?&`` specials only — no ``-_``).
        user = UsersDTO.model_validate(
            {
                "id": subject,
                "username": preferred,
                "email": normalized_email,
                "password": f"Aa1!{secrets.token_hex(16)}",
            }
        )
        logger.info("Provisioning local user from Auth subject user_id=%s", subject)
        return self.create(obj=user, owner=None)
