"""Users service module for the Papita Transactions system.

This module provides the UsersService class which implements operations for
managing user entities in the system. It extends the base service functionality
with user-specific configurations and behavior. UsersService is the canonical
service for resolving owner_id to UsersDTO for use as owner= in other services.

Classes:
    UsersService: Service for managing user entities in the system.
"""

import hashlib
import logging
import re
import uuid
from typing import Annotated

from pydantic import Field

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.access.users.repository import UsersRepository
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.model.contstants import USERNAME_REGEX
from papita_txnsmodel.model.enums import ProviderType
from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.utils.configutils import DEFAULT_ENCODING
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

        # Uniqueness / collision checks need soft-deleted rows; auth paths do not.
        user = self._repository.get_record_from_attributes(
            probe,
            dto_type=UsersDTO,
            include_deleted=not require_active,
        )
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
            auth_provider=user.auth_provider,
            display_name=user.display_name,
            phone=user.phone,
            provider_type=user.provider_type,
            active=user.active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            deleted_at=user.deleted_at,
        )
        self._repository.upsert_record(updated, owner=None)
        return updated

    def _rehash_password_if_needed(self, user: UsersDTO, plain_password: str) -> UsersDTO:
        """Upgrade Argon2 parameters on login when the stored hash is outdated."""
        if not user.password:
            return user
        password_manager = PasswordManagerFactory().password_manager
        if not isinstance(password_manager, Argon2PasswordManager):
            return user
        if not password_manager.needs_rehash(user.password):
            return user

        new_hash = password_manager.hash_password(plain_password)
        logger.info("Upgrading Argon2 hash parameters for user_id=%s", user.id)
        return self._persist_password_hash(user, new_hash)

    def verify_credentials(self, username_or_email: str, password: str) -> UsersDTO | None:
        """Verify local-login credentials and return the user on success.

        Accepts either ``users.username`` or ``users.email`` as the login identifier.
        Returns None for unknown users, Supabase-managed rows, and wrong passwords
        (same failure path — no enumeration).

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
        if user.auth_provider != "local" or not user.password:
            logger.debug("Authentication failed: non-local auth for user_id=%s", user.id)
            return None

        password_manager = PasswordManagerFactory().password_manager
        if not password_manager.verify_password(password, user.password):
            logger.debug("Authentication failed: password mismatch for user_id=%s", user.id)
            return None

        return self._rehash_password_if_needed(user, password)

    def register(
        self,
        *,
        email: str,
        password: str,
        username: str | None = None,
        display_name: str | None = None,
        phone: str | None = None,
        provider_type: ProviderType | str = ProviderType.EMAIL,
    ) -> UsersDTO:
        """Register a new local-auth user after uniqueness checks.

        ``username`` defaults to a handle derived from ``email`` (email is the
        canonical client login identity).

        Args:
            email: Unique email (``EMAIL_REGEX``); used as the login identifier.
            password: Plain-text password (``PASSWORD_REGEX``); hashed on persist.
            username: Optional handle; when omitted, derived from the email local-part.
            display_name: Optional human-readable name.
            phone: Optional E.164-style phone.
            provider_type: Signup channel (``ProviderType``; password register uses ``EMAIL``).

        Returns:
            UsersDTO: The persisted user (password field holds Argon2 hash).

        Raises:
            ValueError: If username or email is already registered.
        """
        self.ensure_password_manager()
        normalized_email = email.strip().lower()
        resolved_username = (username or "").strip() or self.username_from_email(normalized_email)
        resolved_username = self._ensure_unique_username(resolved_username, email=normalized_email)

        if self._lookup_by_identifier(normalized_email, require_active=False):
            raise ValueError("Email already registered")

        resolved_provider = (
            provider_type if isinstance(provider_type, ProviderType) else ProviderType(str(provider_type).lower())
        )
        user = UsersDTO(
            username=resolved_username,
            email=normalized_email,
            password=password,
            auth_provider="local",
            display_name=display_name,
            phone=phone,
            provider_type=resolved_provider,
        )
        return self.create(obj=user, owner=None)

    def get_by_email(self, email: str, *, require_active: bool = True) -> UsersDTO | None:
        """Resolve a tenant user by email (local or Supabase-linked rows).

        Args:
            email: Login email (normalized to lowercase).
            require_active: When True, soft-deleted / inactive rows are ignored.

        Returns:
            Matching ``UsersDTO`` or ``None``.
        """
        normalized = (email or "").strip().lower()
        if not normalized:
            return None
        return self._lookup_by_identifier(normalized, require_active=require_active)

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
    def username_from_email(email: str) -> str:
        """Derive a ``USERNAME_REGEX``-safe handle from an email address.

        Args:
            email: Email used as the canonical client login identity.

        Returns:
            Sanitized username of length 6–255.
        """
        normalized = (email or "").strip().lower()
        local = normalized.split("@", 1)[0] if normalized else ""
        sanitized = re.sub(r"[^A-Za-z0-9_]", "_", local)
        if len(sanitized) < 6:
            digest = hashlib.sha256(normalized.encode(DEFAULT_ENCODING)).hexdigest()
            sanitized = (sanitized + digest)[:12]
        if not _USERNAME_RE.fullmatch(sanitized[:255]):
            digest = hashlib.sha256(normalized.encode(DEFAULT_ENCODING)).hexdigest()
            return f"u_{digest[:20]}"
        return sanitized[:255]

    def _ensure_unique_username(self, username: str, *, email: str) -> str:
        """Ensure the username is free; fall back to an email-hash handle on collision."""
        owner = self._lookup_by_identifier(username, require_active=False)
        if owner is None:
            return username
        digest = hashlib.sha256(email.encode(DEFAULT_ENCODING)).hexdigest()
        fallback = f"u_{digest[:20]}"
        if self._lookup_by_identifier(fallback, require_active=False) is None:
            return fallback
        raise ValueError("Username already registered")

    @staticmethod
    def username_from_auth_claims(*, subject: uuid.UUID, email: str, preferred_username: str | None = None) -> str:
        """Derive a local ``users.username`` that satisfies ``USERNAME_REGEX``.

        Prefers a valid ``preferred_username``; otherwise derives from email
        (canonical login identity); finally ``sb_<hex>`` from the Auth subject.

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
        candidates.append(UsersService.username_from_email(email))
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
        display_name: str | None = None,
        phone: str | None = None,
        provider_type: ProviderType | str | None = None,
    ) -> UsersDTO:
        """Load or create a tenant profile row for a Supabase Auth ``sub``.

        ``users.id`` equals the Auth user id. Credentials stay in Supabase Auth;
        ``password`` is ``None`` and ``auth_provider`` is ``supabase``.

        When the row already exists, optional profile fields from Auth
        (``display_name``, ``phone``, ``provider_type``, and claim ``email``) are
        refreshed when provided — ``provider_type=None`` leaves the stored channel
        unchanged so password login does not overwrite OAuth.

        Args:
            subject: Auth subject UUID to use as ``users.id`` (``auth.users.id``).
            email: User email from Auth claims (required for new rows; refreshes
                existing rows when it differs and does not collide).
            username: Optional preferred username for new rows.
            display_name: Optional human-readable name (create + refresh).
            phone: Optional phone (create + refresh).
            provider_type: Signup channel; ``None`` defaults to ``EMAIL`` on create
                and skips provider updates on existing rows.

        Returns:
            Active ``UsersDTO`` for ``subject``.

        Raises:
            ValueError: When email is blank, or email/username collide with another user.
        """
        existing = self.get_owner(subject)
        if existing is not None:
            if not existing.active or existing.deleted_at is not None:
                raise ValueError("User is inactive or deleted")
            return self._refresh_auth_profile(
                existing,
                email=email,
                display_name=display_name,
                phone=phone,
                provider_type=provider_type,
            )

        # ``get_owner`` / ``get`` hide soft-deleted rows; creating again would upsert
        # ``active=True`` onto the same primary key and silently reactivate them.
        inactive_or_deleted = self._repository.get_record_by_id(subject, dto_type=self.dto_type, include_deleted=True)
        if inactive_or_deleted is not None:
            raise ValueError("User is inactive or deleted")

        normalized_email = (email or "").strip().lower()
        if not normalized_email:
            raise ValueError("Auth subject is missing email")

        preferred = self.username_from_auth_claims(
            subject=subject,
            email=normalized_email,
            preferred_username=username or self.username_from_email(normalized_email),
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

        if provider_type is None:
            resolved_provider = ProviderType.EMAIL
        elif isinstance(provider_type, ProviderType):
            resolved_provider = provider_type
        else:
            resolved_provider = ProviderType(str(provider_type).lower())
        user = UsersDTO.model_validate(
            {
                "id": subject,
                "username": preferred,
                "email": normalized_email,
                "password": None,
                "auth_provider": "supabase",
                "display_name": display_name,
                "phone": phone,
                "provider_type": resolved_provider,
            }
        )
        logger.info("Provisioning tenant user linked to Auth subject user_id=%s", subject)
        return self.create(obj=user, owner=None)

    def _refresh_auth_profile(
        self,
        existing: UsersDTO,
        *,
        email: str,
        display_name: str | None,
        phone: str | None,
        provider_type: ProviderType | str | None,
    ) -> UsersDTO:
        """Update stored profile fields from Auth when values are provided."""
        changed = False
        normalized_email = (email or "").strip().lower()
        if normalized_email and normalized_email != existing.email:
            email_owner = self._lookup_by_identifier(normalized_email, require_active=False)
            if email_owner is not None and email_owner.id != existing.id:
                raise ValueError("Email already registered")
            existing.email = normalized_email
            changed = True

        if display_name is not None:
            resolved_name = display_name.strip() or None
            if resolved_name != existing.display_name:
                existing.display_name = resolved_name
                changed = True

        if phone is not None:
            resolved_phone = phone.strip() or None
            if resolved_phone != existing.phone:
                existing.phone = resolved_phone
                changed = True

        if provider_type is not None:
            resolved_provider = (
                provider_type if isinstance(provider_type, ProviderType) else ProviderType(str(provider_type).lower())
            )
            if existing.provider_type != resolved_provider:
                existing.provider_type = resolved_provider
                changed = True

        if not changed:
            return existing

        existing.password = None
        existing.auth_provider = "supabase"
        logger.debug("Refreshing Auth-linked profile user_id=%s", existing.id)
        return self.create(obj=existing, owner=None)
