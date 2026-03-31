"""Hashing and password management utilities for the Papita Transactions system.

This module provides an abstraction layer for password hashing and verification,
Argon2-based password management.
"""

import base64
import logging
import secrets
from typing import Annotated, Self, Set, Type

from argon2 import PasswordHasher
from argon2 import Type as Argon2Type
from argon2.exceptions import VerifyMismatchError
from pydantic import AliasChoices, BaseModel, Field

from .abstract import AbstractPasswordManager

logger = logging.getLogger(__name__)


class Argon2AlgorithmParameters(BaseModel):
    """Parameters for the Argon2 algorithm.

    Attributes:
        memory_cost: Memory usage in KiB.
        time_cost: Number of iterations.
        parallelism: Number of parallel threads.
        hash_len: Length of the generated hash.
        salt_len: Length of the salt.
    """

    model_config = {"populate_by_name": True}

    memory_cost: Annotated[int, Field(ge=1024, le=1048576, multiple_of=2)] = 65536
    time_cost: Annotated[int, Field(ge=1, le=16)] = 3
    parallelism: Annotated[int, Field(ge=1, le=16)] = 4
    hash_len: Annotated[int, Field(ge=16, le=64, multiple_of=2)] = 32
    salt_len: Annotated[int, Field(ge=16, le=64, multiple_of=2)] = 32
    encoding: Annotated[str, Field(min_length=1, max_length=32)] = "utf-8"
    argon2_type: Annotated[Argon2Type, Field(validation_alias=AliasChoices("type", "argon2_type"))] = Argon2Type.ID
    salt: bytes | None = None
    pepper: bytes | None = None


class Argon2PasswordManager(AbstractPasswordManager):
    """Password manager implementation using the Argon2 algorithm.

    This class uses the argon2-cffi library to provide secure password
    hashing and verification.

    Attributes:
        salt_len (int): Length of the salt to use.
        ph (PasswordHasher): The underlying Argon2 hasher instance.
    """

    __slots__ = ("password_hasher", "algorithm_parameters_parser", "salt_len", "_salt", "_pepper")

    def __init__(
        self, *, algorithm_parameters_parser: Type[Argon2AlgorithmParameters] = Argon2AlgorithmParameters, **_
    ) -> None:
        """Initialize the Argon2 password manager.

        Args:
            algorithm_parameters_parser: The parser to use for the algorithm parameters.
            Defaults to Argon2AlgorithmParameters.
        """
        if not isinstance(algorithm_parameters_parser, type) or not issubclass(
            algorithm_parameters_parser, Argon2AlgorithmParameters
        ):
            raise ValueError("algorithm_parameters_parser must be a subclass of Argon2AlgorithmParameters")

        self.password_hasher: PasswordHasher | None = None
        self.algorithm_parameters_parser: Type[Argon2AlgorithmParameters] = algorithm_parameters_parser
        self.salt_len: int | None = None
        self._salt: bytes | None = None
        self._pepper: bytes | None = None

    @classmethod
    def keywords(cls) -> Set[str]:
        """Return identifiers used to select this manager in the factory."""
        return {"argon2", ".".join(filter(None, (cls.__module__, cls.__name__)))}

    @property
    def pepper(self) -> bytes | None:
        """Return the pepper.

        Returns:
            bytes | None: The pepper or None if not set.
        """
        return self._pepper

    @property
    def salt(self) -> bytes:
        """Return salt bytes for hashing (optionally combined with pepper).

        Returns:
            bytes: Salt bytes passed to the Argon2 hasher.
        """
        if not self._salt:
            self.generate_new_salt()

        if not isinstance(self._salt, bytes):
            raise TypeError("Salt is not a bytes object")

        if not isinstance(self._pepper, bytes):
            return self._salt

        return self._salt + self._pepper

    def setup_algorithm(self, **kwargs) -> Self:
        """Setup the algorithm with specific parameters.

        Args:
            **kwargs: Configuration arguments for the algorithm.
        """
        algorithm_parameters = self.algorithm_parameters_parser.model_validate(kwargs, extra="ignore")
        self.salt_len = algorithm_parameters.salt_len
        self._salt = algorithm_parameters.salt
        self._pepper = algorithm_parameters.pepper
        self.password_hasher = PasswordHasher(
            time_cost=algorithm_parameters.time_cost,
            memory_cost=algorithm_parameters.memory_cost,
            parallelism=algorithm_parameters.parallelism,
            hash_len=algorithm_parameters.hash_len,
            salt_len=algorithm_parameters.salt_len,
            type=algorithm_parameters.argon2_type,
        )
        return self

    def get_salt(self, hashed_password: str) -> bytes:
        """Get the salt from an Argon2 hash string.

        Args:
            hashed_password: The Argon2 hash string.

        Returns:
            bytes: The extracted salt (base64url segment from the PHC string).

        Raises:
            ValueError: If the string is not a recognized Argon2 encoding.
        """
        segments = hashed_password.split("$")
        if len(segments) >= 5 and segments[1].startswith("argon2"):
            salt_b64 = segments[4]
            pad = "=" * ((4 - len(salt_b64) % 4) % 4)
            self._salt = base64.urlsafe_b64decode(salt_b64 + pad)
            return self._salt

        raise ValueError("Expected an Argon2-encoded password hash string")

    def hash_password(self, password: str) -> str:
        """Hash a password using Argon2.

        Args:
            password: Plain text password.

        Returns:
            str: Argon2 hash string.

        Raises:
            RuntimeError: If :meth:`setup_algorithm` was not called first.
        """
        if self.password_hasher is None:
            raise RuntimeError("Password hasher is not initialized; call setup_algorithm first.")
        return self.password_hasher.hash(password, salt=self.salt)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify an Argon2 password hash.

        Args:
            password: Plain text password.
            hashed_password: Argon2 hash to verify.

        Returns:
            bool: True if verification succeeds, False otherwise.
        """
        if self.password_hasher is None:
            raise RuntimeError("Password hasher is not initialized; call setup_algorithm first.")
        try:
            self.password_hasher.verify(hashed_password, password)
            return True
        except VerifyMismatchError:
            logger.debug("Argon2 password verification failed (mismatch).")
            return False

    def generate_new_salt(self) -> Self:
        """Generate a new salt.

        Returns:
            Self: The instance of the password manager.

        Raises:
            ValueError: If ``salt_len`` is not set (``setup_algorithm`` not run).
        """
        if self.salt_len is None:
            raise ValueError("salt_len is not set; call setup_algorithm before generate_new_salt.")
        self._salt = secrets.token_bytes(self.salt_len)
        return self

    def raw_salt_hex_for_storage(self) -> str:
        """Return the raw Argon2 salt as hex for persistence (``Users.hashing_algorithm_salt``).

        This is only the random salt bytes, not any optional pepper concatenation used
        when calling the hasher.

        Returns:
            Lowercase hex string.

        Raises:
            RuntimeError: If ``_salt`` has not been set yet.
        """
        if not isinstance(self._salt, bytes):
            raise RuntimeError("Raw salt is not set; run hashing or salt generation first.")
        return self._salt.hex()
