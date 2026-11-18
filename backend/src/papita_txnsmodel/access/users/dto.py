"""User-related Data Transfer Objects (DTOs) for the Papita Transactions system.

This module defines the DTOs used for representing users and entities owned by
users. It handles data validation, normalization, and serialization for user
records and ownership-aware tables.

``UsersDTO.id`` aligns with Supabase Auth ``sub`` when ``auth_provider='supabase'``.
"""

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal, Self

from pydantic import Field, field_serializer, field_validator, model_serializer, model_validator

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.model.contstants import EMAIL_REGEX, PASSWORD_REGEX, USERNAME_REGEX
from papita_txnsmodel.model.enums import ProviderType
from papita_txnsmodel.model.users import Users
from papita_txnsmodel.utils.configutils import DEFAULT_ENCODING
from papita_txnsmodel.utils.hashutils import PasswordManagerFactory

AuthProvider = Literal["supabase", "local"]

_PHONE_REGEX = re.compile(r"^\+?[1-9]\d{6,14}$")


class UsersDTO(TableDTO):
    """Data Transfer Object for user account / tenant profile information.

    Attributes:
        username: Unique handle (6–255, ``USERNAME_REGEX``).
        email: Unique email (lowercased).
        password: Plain password for local auth, Argon2 hash from DB, or ``None`` when
            identity is owned by Supabase Auth.
        auth_provider: ``supabase`` (MVP IdP) or ``local`` (tests / transitional HS256).
        display_name: Optional human-readable name.
        phone: Optional E.164-style phone number.
        provider_type: Signup channel (``email``, ``google``, or ``github``).
    """

    __dao_type__ = Users

    username: Annotated[
        str, Field(strip_whitespace=True, to_lower=False, min_length=6, max_length=255, pattern=USERNAME_REGEX)
    ]
    email: Annotated[
        str, Field(strip_whitespace=True, to_lower=True, min_length=5, max_length=255, pattern=EMAIL_REGEX)
    ]
    password: str | None = None
    auth_provider: AuthProvider = "supabase"
    display_name: Annotated[str | None, Field(default=None, strip_whitespace=True, max_length=255)] = None
    phone: Annotated[str | None, Field(default=None, strip_whitespace=True, max_length=32)] = None
    provider_type: ProviderType = ProviderType.EMAIL

    @field_validator("provider_type", mode="before")
    @classmethod
    def _coerce_provider_type(cls, value: object) -> ProviderType | object:
        """Accept enum members, wire strings, and map legacy ``phone`` → ``email``."""
        if isinstance(value, ProviderType):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized == "phone":
                return ProviderType.EMAIL
            try:
                return ProviderType(normalized)
            except ValueError as exc:
                raise ValueError(
                    f"provider_type must be one of {[m.value for m in ProviderType]}, got {value!r}"
                ) from exc
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        """Validate a local password when present.

        Args:
            v: Plain password, existing Argon2 hash, or ``None`` (Supabase Auth).

        Returns:
            The validated password value.

        Raises:
            ValueError: If a plain password fails complexity rules.
        """
        if v is None or v == "":
            return None
        if v.startswith("$argon2"):
            return v
        if not re.match(PASSWORD_REGEX, v):
            raise ValueError(
                "Password must be 8-128 characters long, include at least one uppercase letter, "
                "one lowercase letter, one number, and one special character."
            )
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        """Normalize and validate an optional phone number.

        Args:
            v: Raw phone string or ``None``.

        Returns:
            Normalized phone or ``None``.

        Raises:
            ValueError: When the phone format is invalid.
        """
        if v is None or v == "":
            return None
        normalized = v.replace(" ", "").replace("-", "")
        if not _PHONE_REGEX.fullmatch(normalized):
            raise ValueError("phone must be an E.164-style number (e.g. +15551234567)")
        return normalized

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str | None) -> str | None:
        """Treat blank display names as unset.

        Args:
            v: Raw display name or ``None``.

        Returns:
            Stripped display name or ``None``.
        """
        if v is None or v == "":
            return None
        return v

    @model_validator(mode="before")
    @classmethod
    def _assign_username_based_id(cls, data: object) -> object:
        """Assign a deterministic username-based UUID when ``id`` is omitted (local only).

        Supabase Auth rows must pass ``id = Auth sub`` explicitly. Local/test users
        without an id still receive the historical uuid5(username) value.

        Args:
            data: Raw model input (dict or other).

        Returns:
            Input with ``id`` set from the username hash when missing for local auth.
        """
        if not isinstance(data, dict):
            return data
        if data.get("id") is not None:
            return data
        provider = data.get("auth_provider") or "supabase"
        if provider != "local":
            return data
        username = data.get("username")
        if not username:
            return data
        assigned = dict(data)
        assigned["id"] = uuid.uuid5(
            uuid.NAMESPACE_URL,
            hashlib.sha256(str(username).encode(DEFAULT_ENCODING)).hexdigest(),
        )
        return assigned

    @model_validator(mode="after")
    def _normalize_model(self) -> Self:
        """Normalize timestamps and enforce password rules by provider.

        Returns:
            Self: The normalized user DTO instance.

        Raises:
            ValueError: When ``auth_provider=local`` and password is missing.
        """
        now = datetime.now(timezone.utc)
        self.created_at = self.created_at or now
        self.updated_at = self.updated_at or now
        if self.auth_provider == "local" and not self.password:
            raise ValueError("Local auth users require a password")
        if self.auth_provider == "supabase":
            self.password = None
        return self

    @model_serializer()
    def _serialize(self) -> dict:
        """Serialize the user DTO to a dictionary.

        Hashes a plain local password before persistence. Supabase rows store
        ``password=None``.

        Returns:
            dict: The serialized user data.
        """
        password_value = self.password
        if password_value is not None and not password_value.startswith("$argon2"):
            password_value = PasswordManagerFactory().password_manager.hash_password(password_value)
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "password": password_value,
            "auth_provider": self.auth_provider,
            "display_name": self.display_name,
            "phone": self.phone,
            "provider_type": (
                self.provider_type.value if isinstance(self.provider_type, ProviderType) else self.provider_type
            ),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deleted_at": self.deleted_at,
            "active": self.active,
        }


class OwnedTableDTO(TableDTO):
    """Base DTO for core entities that are owned by a user.

    This class extends TableDTO to include an owner reference, ensuring that
    entities can be associated with specific user accounts.

    Attributes:
        owner_id (uuid.UUID | UsersDTO): Reference to the owner, can be a UUID
            or a full UsersDTO object.
    """

    owner_id: uuid.UUID | UsersDTO

    @field_serializer("owner_id")
    def _serialize_owner_id(self, value: uuid.UUID | UsersDTO) -> uuid.UUID:
        """Serialize owner_id field to its ID value.

        This serializer ensures that the owner_id field is consistently represented as a UUID
        in the serialized output, regardless of whether it was provided as a full UsersDTO
        object or just a UUID.

        Args:
            value: The owner_id value to serialize, either a UUID or a UsersDTO instance.

        Returns:
            uuid.UUID: The UUID of the owner.
        """
        return value.id if isinstance(value, UsersDTO) else value  # type: ignore
