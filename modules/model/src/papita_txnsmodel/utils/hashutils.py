"""Hashing and password management utilities for the Papita Transactions system.

This module provides an abstraction layer for password hashing and verification,
supporting multiple algorithms via a factory pattern. It currently implements
Argon2-based password management.

Classes:
    AbstractPasswordManager: Abstract base class for password managers.
    Argon2PasswordManager: Password manager using the Argon2 hashing algorithm.
    PasswordManagerFactory: Factory class for creating and managing password managers.
"""
import logging

from types import ModuleType
import abc
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from .classutils import MetaSingleton, ClassDiscovery
from typing import Set, Sequence, Type

logger = logging.getLogger(__name__)


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
        pass

    @abc.abstractmethod
    def get_salt(self, hashed_password: str) -> str:
        """Extract the salt from a hashed password string.

        Args:
            hashed_password: The encoded password hash.

        Returns:
            str: The salt extracted from the hash.
        """
        pass

    @abc.abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash a plain text password.

        Args:
            password: The plain text password to hash.

        Returns:
            str: The resulting password hash.
        """
        pass

    @abc.abstractmethod
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify if a password matches a given hash.

        Args:
            password: The plain text password to verify.
            hashed_password: The hash to compare against.

        Returns:
            bool: True if the password matches the hash, False otherwise.
        """
        pass


class Argon2PasswordManager(AbstractPasswordManager):
    """Password manager implementation using the Argon2 algorithm.

    This class uses the argon2-cffi library to provide secure password
    hashing and verification.

    Attributes:
        salt_len (int): Length of the salt to use.
        ph (PasswordHasher): The underlying Argon2 hasher instance.
    """

    def __init__(
        self,
        memory_cost: int = 65536,
        time_cost: int = 3,
        parallelism: int = 4,
        hash_len: int = 32,
        salt_len: int = 32,
    ):
        """Initialize the Argon2 password manager with specific costs.

        Args:
            memory_cost: Memory usage in KiB.
            time_cost: Number of iterations.
            parallelism: Number of parallel threads.
            hash_len: Length of the generated hash.
            salt_len: Length of the salt.
        """
        self.salt_len = salt_len
        self.ph = PasswordHasher(
            memory_cost=memory_cost,
            time_cost=time_cost,
            parallelism=parallelism,
            hash_len=hash_len,
            salt_len=salt_len,
        )

    @classmethod
    def keywords(cls) -> Set[str]:
        """Return the identification keywords for Argon2.

        Returns:
            Set[str]: The set {"argon2"}.
        """
        return {"argon2"}

    def get_salt(self, hashed_password: str) -> str:
        """Get the salt from an Argon2 hash string.

        Args:
            hashed_password: The Argon2 hash string.

        Returns:
            str: The extracted salt.
        """
        return self.ph.get_salt(hashed_password)

    def hash_password(self, password: str) -> str:
        """Hash a password using Argon2.

        Args:
            password: Plain text password.

        Returns:
            str: Argon2 hash string.
        """
        return self.ph.hash(password)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify an Argon2 password hash.

        Args:
            password: Plain text password.
            hashed_password: Argon2 hash to verify.

        Returns:
            bool: True if verification succeeds, False otherwise.
        """
        try:
            self.ph.verify(hashed_password, password)
            return True
        except VerifyMismatchError:
            logger.error("Password verification failed")
            return False


class PasswordManagerFactory(metaclass=MetaSingleton):
    """Factory for creating and managing password manager instances.

    This class uses discovery to find available password manager implementations
    and provides a singleton-like access to the active manager.
    """

    _password_manager: AbstractPasswordManager | None = None

    @property
    def password_manager(self) -> AbstractPasswordManager:
        """Return the currently configured password manager.

        Returns:
            AbstractPasswordManager: The active password manager instance.
        """
        return self.get_password_manager()

    def get_password_manager(
        self, *modules: "Sequence[ModuleType]", keyword: str | None = None, **kwargs
    ) -> AbstractPasswordManager:
        """Retrieve or create a password manager instance.

        Args:
            *modules: Modules to search for password manager implementations.
            keyword: The identifying keyword for the desired manager type.
            **kwargs: Configuration arguments for the manager constructor.

        Returns:
            AbstractPasswordManager: The initialized password manager.

        Raises:
            ValueError: If the keyword is not provided and no manager is cached.
        """
        if isinstance(self._password_manager, AbstractPasswordManager):
            return self._password_manager

        if not keyword:
            raise ValueError("Password manager type not specified")

        password_manager_type = self.get_password_manager_type(keyword, *modules)
        self._password_manager = password_manager_type(**kwargs)
        return self._password_manager

    def reset(self):
        """Reset the cached password manager instance."""
        self._password_manager = None

    @classmethod
    def get_password_manager_type(
        cls, keyword: str, *modules: "Sequence[ModuleType]"
    ) -> Type[AbstractPasswordManager]:
        """Discover and return a password manager class by keyword.

        Args:
            keyword: The identifying keyword to search for.
            *modules: Specific modules to search within.

        Returns:
            Type[AbstractPasswordManager]: The matching password manager class.

        Raises:
            ValueError: If no matching password manager is found.
        """
        for mod in set(modules) | {__import__(__name__)}:
            for password_manager in ClassDiscovery.get_children(mod, AbstractPasswordManager):
                keywords = {kw.lower() for kw in password_manager.keywords()}
                if keyword.lower() in keywords or keyword == ".".join(filter(None, ClassDiscovery.decompose_class(password_manager))):
                    return password_manager

        raise ValueError(f"Password manager type {keyword} not found")
