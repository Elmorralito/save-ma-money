"""Users service module for the Papita Transactions system.

This module provides the UsersService class which implements operations for
managing user entities in the system. It extends the base service functionality
with user-specific configurations and behavior. UsersService is the canonical
service for resolving owner_id to UsersDTO for use as owner= in other services.

Classes:
    UsersService: Service for managing user entities in the system.
"""

import logging
import uuid
from typing import Annotated

from pydantic import Field

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.access.users.repository import UsersRepository
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.utils.hashutils import PasswordManagerFactory

logger = logging.getLogger(__name__)


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

        return user

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
