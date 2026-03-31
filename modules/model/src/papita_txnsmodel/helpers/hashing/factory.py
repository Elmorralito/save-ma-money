import sys
from typing import Type

from papita_txnsmodel.utils.classutils import ClassDiscovery, MetaSingleton

from .abstract import AbstractPasswordManager


class PasswordManagerFactory(metaclass=MetaSingleton):
    """Factory for creating and managing password manager implementations.

    Uses discovery to find password manager classes. The :attr:`password_manager`
    property returns a lazily built Argon2 manager (keyword ``argon2``) for
    callers that need a default instance.
    """

    def get_password_manager(self, *modules, keyword: str | None = None, **kwargs) -> AbstractPasswordManager:
        """Retrieve or create a password manager instance.

        Args:
            *modules: Modules to search for password manager implementations.
            keyword: The identifying keyword for the desired manager type.
            **kwargs: Configuration arguments for the manager constructor.

        Returns:
            AbstractPasswordManager: The initialized password manager.

        Raises:
            ValueError: If ``keyword`` is missing/empty or no implementation is found.
        """
        if keyword is None or not str(keyword).strip():
            raise ValueError("Password manager keyword was not specified")
        password_manager_type = self.get_password_manager_type(keyword, *modules)
        return password_manager_type(**kwargs).setup_algorithm(**kwargs)

    @classmethod
    def get_password_manager_type(
        cls,
        keyword: str,
        *modules,
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
        kw_norm = str(keyword).lower()
        for mod in set(modules) | {sys.modules[__name__]}:
            for password_manager in ClassDiscovery.get_children(mod, AbstractPasswordManager):
                keywords = {kw.lower() for kw in password_manager.keywords()}
                path_norm = ".".join(filter(None, ClassDiscovery.decompose_class(password_manager))).lower()
                if kw_norm in keywords or kw_norm == path_norm:
                    return password_manager

        raise ValueError(f"Password manager type {keyword} not found in modules: {modules}")
