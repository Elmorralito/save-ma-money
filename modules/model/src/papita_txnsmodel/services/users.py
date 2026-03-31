"""User-facing service layer for the Papita Transactions data model.

Defines ``UsersService``, which wires ``UsersDTO`` and ``UsersRepository`` to
``BaseService`` CRUD flows and adds password lifecycle behavior: hashing on
create, verification, and password changes. Callers use ``get_owner()`` to turn
an ``owner_id`` into a ``UsersDTO`` for ``owner=`` arguments on other services.

Key exports:
    UsersService: Pydantic-configured service for user records and credentials.
"""

import base64
import binascii
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Self

from pydantic import ConfigDict, Field

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.access.users.repository import UsersRepository
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.helpers.hashing.abstract import AbstractPasswordManager
from papita_txnsmodel.helpers.hashing.factory import PasswordManagerFactory
from papita_txnsmodel.services.base import BaseService


def _stored_salt_str_to_bytes(stored: str | None) -> bytes | None:
    """Decode ``UsersDTO.hashing_algorithm_salt`` for Argon2 ``salt=`` (expects ``bytes``).

    Accepts lowercase hex (preferred for new rows) or URL-safe base64 (legacy).

    Args:
        stored: Serialized salt from the database, or None.

    Returns:
        Raw salt bytes, or None if ``stored`` is empty/None.

    Raises:
        ValueError: If the string is not valid hex or base64.
    """
    if stored is None or stored == "":
        return None
    try:
        return bytes.fromhex(stored)
    except ValueError:
        pass
    pad = "=" * ((4 - len(stored) % 4) % 4)
    try:
        return base64.urlsafe_b64decode(stored + pad)
    except (ValueError, binascii.Error) as exc:
        raise ValueError(f"Invalid hashing_algorithm_salt encoding: {exc}") from exc


class UsersService(BaseService):
    """Coordinate user persistence, hashing metadata, and password operations.

    Extends ``BaseService`` with ``UsersDTO`` / ``UsersRepository`` and upsert
    defaults suited to user registration. Plaintext passwords are hashed before
    persistence; algorithm choice and salt come from the DTO and the configured
    ``PasswordManagerFactory``. Use ``get_owner()`` to resolve an ``owner_id`` to
    a ``UsersDTO`` for ``owner=`` on other services and handlers.

    Attributes:
        dto_type: Expected DTO class; always ``UsersDTO``.
        repository_type: Repository used for user rows; ``UsersRepository``.
        password_manager_factory: Singleton factory that resolves and constructs
            ``AbstractPasswordManager`` implementations from algorithm keywords.
        missing_upsertions_tol: Maximum acceptable fraction of failed upserts
            during bulk operations (inherited semantics from ``BaseService``).
        on_conflict_do: Upsert conflict policy; defaults to ``UPDATE`` for users.
        pepper: Optional application-level secret mixed into hashing when
            supported by the active password manager. ``None`` disables pepper.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    dto_type: type[UsersDTO] = UsersDTO
    repository_type: type[UsersRepository] = UsersRepository

    password_manager_factory: PasswordManagerFactory = Field(default_factory=PasswordManagerFactory)
    missing_upsertions_tol: Annotated[float, Field(ge=0, le=0.5)] = 0.01
    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE
    pepper: bytes | None = None

    @staticmethod
    def _hashing_algorithm_salt_for_storage(password_manager: AbstractPasswordManager) -> str:
        """Serialize salt for ``UsersDTO.hashing_algorithm_salt`` (str column)."""
        raw_hex = getattr(password_manager, "raw_salt_hex_for_storage", None)
        if callable(raw_hex):
            return raw_hex()
        salt_val = password_manager.salt
        if isinstance(salt_val, (bytes, bytearray)):
            return bytes(salt_val).hex()
        return str(salt_val)

    def setup_password_manager(self, *, user: UsersDTO, **kwargs) -> AbstractPasswordManager:
        """Build a password manager configured for an existing or in-flight user row.

        Merges ``user`` hashing fields (algorithm keyword, parameters, salt, and
        optional ``hashing_algorithm_module`` hints) with ``pepper`` from this
        service and any extra ``kwargs``, then asks the factory for a concrete
        manager instance.

        Args:
            user: User DTO supplying ``hashing_algorithm``, parameters, and salt.
            **kwargs: Extra constructor or ``setup_algorithm`` arguments forwarded
                to the factory after merging with the user's hashing parameters.

        Returns:
            An ``AbstractPasswordManager`` ready to hash or verify for this user.

        Raises:
            ValueError: If the factory cannot resolve a manager for the user's
                algorithm keyword or module hints.
            RuntimeError: If the underlying manager fails to initialize
                (implementation-dependent).
        """
        hashing_algorithm_modules = tuple(set(filter(None, [user.hashing_algorithm_module])))
        hashing_algorithm_parameters = user.hashing_algorithm_parameters | {
            "salt": _stored_salt_str_to_bytes(user.hashing_algorithm_salt),
            "pepper": self.pepper,
        }
        kwargs = kwargs | hashing_algorithm_parameters
        return self.password_manager_factory.get_password_manager(
            *hashing_algorithm_modules, keyword=user.hashing_algorithm, **kwargs
        )

    def get_owner(self, owner_id: uuid.UUID | str) -> UsersDTO | None:
        """Load the user DTO for an owner id, or return None if missing.

        Use when you have an ``owner_id`` (for example from auth context) and need
        a ``UsersDTO`` to pass as ``owner=`` to ``create``, ``get_records``,
        ``load``, ``dump``, or related APIs on other services.

        Args:
            owner_id: Primary key of the user; UUID or string accepted by ``get``.

        Returns:
            The matching ``UsersDTO``, or ``None`` if no row exists.
        """
        return self.get(obj=owner_id, owner=None)

    def create(self, *, obj: UsersDTO | dict[str, Any], owner: UsersDTO | None = None, **kwargs) -> UsersDTO:
        """Create a user after hashing the plaintext password and recording salt metadata.

        Parses and validates the payload as ``UsersDTO``, temporarily clears
        ``hashing_algorithm_salt`` so the manager can assign a fresh salt, hashes
        ``password``, then restores salt and algorithm module metadata before
        delegating to ``BaseService.create``.

        Args:
            obj: New user as ``UsersDTO`` or dict of fields (must include plaintext
                ``password`` and hashing configuration expected by the factory).
            owner: Optional owning user for scoped persistence; usually ``None``
                for top-level user creation.
            **kwargs: Forwarded to ``setup_password_manager`` and the repository
                upsert (for example ``_db_session`` when supplied by callers).

        Returns:
            The persisted ``UsersDTO`` including stored hash and salt fields.

        Raises:
            TypeError: If the DTO type does not match ``UsersDTO``.
            ValidationError: If Pydantic validation fails when parsing ``obj``.
            ValueError: If the password manager cannot be resolved for the
                configured algorithm (from the factory layer).
        """
        parsed_obj = self.parse_dto(obj)
        self.check_expected_dto_type(parsed_obj)
        parsed_obj.hashing_algorithm_salt = None
        password_manager = self.setup_password_manager(user=parsed_obj, **kwargs)
        parsed_obj.password = password_manager.hash_password(parsed_obj.password)
        parsed_obj.hashing_algorithm_salt = self._hashing_algorithm_salt_for_storage(password_manager)
        parsed_obj.hashing_algorithm_module = password_manager.__class__.__module__
        keywords = password_manager.keywords()
        if not keywords:
            raise ValueError("No hashing algorithm keywords exposed by the password manager")

        parsed_obj.hashing_algorithm = next(iter(keywords))
        return super().create(obj=parsed_obj, owner=owner, **kwargs)

    def validate_password(self, *, user_id: uuid.UUID | str, password: str, **kwargs) -> bool:
        """Return True if ``password`` matches the stored hash for ``user_id``.

        Loads the user, rebuilds the password manager from persisted metadata, and
        verifies the candidate password. On success returns ``True``; on mismatch or
        missing user raises ``ValueError`` (see Raises).

        Args:
            user_id: User primary key as UUID or string.
            password: Plaintext password to verify.
            **kwargs: Passed through to ``setup_password_manager`` when rebuilding
                the manager from stored algorithm parameters.

        Returns:
            ``True`` when verification succeeds.

        Raises:
            ValueError: If credentials do not match a valid user (generic message).
        """
        user = self.get(obj=user_id)
        if not user:
            return False

        password_manager = self.setup_password_manager(user=user, **kwargs)
        if not password_manager.verify_password(password, user.password):
            return False

        return True

    def change_password(self, *, user_id: uuid.UUID | str, old_password: str, new_password: str, **kwargs) -> Self:
        """Rotate a user's password after verifying the current one.

        Ensures the old password matches, rejects reuse of the same password,
        generates a new salt via the active manager, hashes ``new_password``, and
        upserts the row with updated hash and salt fields.

        Args:
            user_id: User primary key as UUID or string.
            old_password: Current plaintext password.
            new_password: Replacement plaintext password.
            **kwargs: Forwarded to ``validate_password`` and password manager
                setup (merged with stored hashing parameters and ``pepper``).

        Returns:
            This service instance for method chaining.

        Raises:
            ValueError: If credentials are invalid, ``new_password`` matches the
                current password, or hashing configuration cannot be satisfied.
        """
        user = self.get(obj=user_id)
        if not user:
            raise ValueError("Invalid credentials")

        if not self.validate_password(user_id=user_id, password=old_password, **kwargs):
            raise ValueError("The old password is incorrect")

        if user.password_locked_until and user.password_locked_until >= datetime.now(timezone.utc):
            raise ValueError(f"The password is locked until {user.password_locked_until.isoformat()}")

        user.password_locked_until = datetime.now(timezone.utc) + timedelta(minutes=1)
        self.upsert(obj=user, **kwargs)

        password_manager = self.setup_password_manager(user=user, **kwargs)
        if password_manager.verify_password(new_password, user.password):
            raise ValueError("The new password cannot be the same as the old password")

        chg_keywords = password_manager.keywords()
        if not chg_keywords:
            raise ValueError("No hashing algorithm keywords exposed by the password manager")

        self.upsert(
            obj={
                "id": user.id,
                "password": password_manager.generate_new_salt().hash_password(new_password),
                "hashing_algorithm_salt": self._hashing_algorithm_salt_for_storage(password_manager),
                "hashing_algorithm_module": password_manager.__class__.__module__,
                "hashing_algorithm": next(iter(chg_keywords)),
                "hashing_algorithm_parameters": password_manager.algorithm_parameters_parser.model_dump(),
                "password_locked_until": None,
            },
            **kwargs,
        )
        return self
