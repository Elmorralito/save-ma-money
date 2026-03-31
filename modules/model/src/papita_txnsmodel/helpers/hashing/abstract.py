"""Hashing and password management utilities for the Papita Transactions system."""

import abc
from typing import Self, Set


class AbstractPasswordManager(abc.ABC):
    """Abstract base class defining the interface for password managers.

    This class establishes the required methods for hashing passwords,
    verifying they match a hash, and retrieving the salt from a hash.
    """

    @classmethod
    @abc.abstractmethod
    def keywords(cls) -> Set[str]:
        """Return the set of keywords identifying this manager type.

        Returns:
            Set[str]: A set of string keywords (e.g., {"argon2"}).
        """

    @property
    @abc.abstractmethod
    def pepper(self) -> bytes | None:
        """Return the pepper.

        Returns:
            bytes | None: The pepper bytes or None if not set.
        """

    @property
    @abc.abstractmethod
    def salt(self) -> bytes:
        """Return the salt.

        Returns:
            bytes: The salt.
        """

    @abc.abstractmethod
    def get_salt(self, hashed_password: str) -> bytes:
        """Extract the salt from a hashed password string.

        Args:
            hashed_password: The encoded password hash.

        Returns:
            bytes: The salt extracted from the hash.
        """

    @abc.abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash a plain text password.

        Args:
            password: The plain text password to hash.

        Returns:
            str: The resulting password hash.
        """

    @abc.abstractmethod
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify if a password matches a given hash.

        Args:
            password: The plain text password to verify.
            hashed_password: The hash to compare against.

        Returns:
            bool: True if the password matches the hash, False otherwise.
        """

    @abc.abstractmethod
    def setup_algorithm(self, **kwargs) -> Self:
        """Setup the algorithm with specific parameters.

        Args:
            **kwargs: Configuration arguments for the algorithm.

        Returns:
            Self: The instance of the algorithm.
        """

    @abc.abstractmethod
    def generate_new_salt(self) -> Self:
        """Generate a new salt.

        Returns:
            Self: The instance of the password manager.
        """
