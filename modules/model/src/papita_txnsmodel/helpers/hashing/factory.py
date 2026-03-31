from typing import Type

from papita_txnsmodel.utils.classutils import ClassDiscovery, MetaSingleton

from .abstract import AbstractPasswordManager


class PasswordManagerFactory(metaclass=MetaSingleton):
    """Factory for creating and managing password manager implementations.

    Uses discovery to find password manager classes and exposes a singleton-style
    cache for the active manager. The ``password_manager`` property defaults to
    Argon2 when nothing is cached yet.
    """

    def get_password_manager(self, *modules, keyword: str, **kwargs) -> AbstractPasswordManager:
        """Retrieve or create a password manager instance.

        Args:
            *modules: Modules to search for password manager implementations.
            keyword: The identifying keyword for the desired manager type.
            **kwargs: Configuration arguments for the manager constructor.

        Returns:
            AbstractPasswordManager: The initialized password manager.

        Raises:
            RuntimeError: If the password manager is not initialized.
        """
        password_manager_type = self.get_password_manager_type(keyword, *modules)
        return password_manager_type(**kwargs).setup_algorithm(**kwargs)

    @classmethod
    def get_password_manager_type(cls, keyword: str, *modules) -> Type[AbstractPasswordManager]:
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
                if keyword.lower() in keywords or keyword == ".".join(
                    filter(None, ClassDiscovery.decompose_class(password_manager))
                ):
                    return password_manager

        raise ValueError(f"Password manager type {keyword} not found in modules: {modules}")
