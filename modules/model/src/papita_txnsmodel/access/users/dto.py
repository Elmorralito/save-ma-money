"""User-related Data Transfer Objects (DTOs) for the Papita Transactions system.

This module defines the DTOs used for representing users and entities owned by
users. It handles data validation, normalization, and serialization for user
records and ownership-aware tables.

Classes:
    UsersDTO: DTO for representing user account information.
    OwnedTableDTO: Base DTO for entities that belong to a specific user.
"""

import uuid
import hashlib
from typing import TYPE_CHECKING, Any, Annotated, Self
from pydantic import model_serializer, model_validator, Field, field_validator, field_serializer
import re

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.model.contstants import EMAIL_REGEX, PASSWORD_REGEX, USERNAME_REGEX
from papita_txnsmodel.utils.configutils import DEFAULT_ENCODING
from papita_txnsmodel.utils.datautils import convert_dto_obj_on_serialize
from papita_txnsmodel.utils.hashutils import PasswordManagerFactory

if TYPE_CHECKING:
    from papita_txnsmodel.model.users import Users


class UsersDTO(TableDTO):
    """Data Transfer Object for user account information.

    This DTO handles validation and normalization for user data, including
    username, email, and password. It automatically generates a unique ID
    based on the hashed username.

    Attributes:
        username (str): The user's unique username.
        email (str): The user's email address.
        password (str): The user's plain text password (hashed on serialization).
    """

    __dao_type__: "Users"

    username: Annotated[str, Field(strip_whitespace=True, to_lower=False, min_length=6, max_length=255, pattern=USERNAME_REGEX)]
    email: Annotated[str, Field(strip_whitespace=True, to_lower=True, min_length=5, max_length=255, pattern=EMAIL_REGEX)]
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate the password using Python's re module.

        Args:
            v: The password to validate.

        Returns:
            str: The validated password.

        Raises:
            ValueError: If the password does not match the complexity requirements.
        """
        if not re.match(PASSWORD_REGEX, v):
            raise ValueError(
                "Password must be 8-128 characters long, include at least one uppercase letter, "
                "one lowercase letter, one number, and one special character."
            )
        return v

    @model_validator(mode="after")
    def _normalize_model(self) -> Self:
        """Normalize the user model after initialization.

        Generates a deterministic UUID based on the username hash to ensure
        consistency across the system.

        Returns:
            Self: The normalized user DTO instance.
        """
        self.id = uuid.uuid5(
            uuid.NAMESPACE_URL,
            hashlib.sha256(self.username.encode(DEFAULT_ENCODING)).hexdigest(),
        )
        return self

    @model_serializer()
    def _serialize(self) -> dict:
        """Serialize the user DTO to a dictionary.

        Hashes the password before serialization to ensure security.

        Returns:
            dict: The serialized user data.
        """
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "password": PasswordManagerFactory.password_manager.hash_password(self.password),
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

    @field_validator("owner_id", mode="before")
    @classmethod
    def validate_owner_id(cls, v: Any) -> Any:
        """Validate owner_id and ensure it's a UUID or UsersDTO.
        
        Args:
            v: The value to validate.
            
        Returns:
            The validated value.
        """
        if isinstance(v, str):
            return uuid.UUID(v)
        return v

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
        return value.id if isinstance(value, TableDTO) else value
