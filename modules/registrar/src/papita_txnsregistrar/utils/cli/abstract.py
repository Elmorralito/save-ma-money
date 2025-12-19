"""Abstract base class for CLI utility implementations.

This module provides the AbstractCLIUtils class, which serves as the foundation for all
command-line interface utilities within the transaction registrar system. It combines
Pydantic's BaseModel for data validation and configuration management with Python's
abstract base class mechanism to enforce a consistent interface for CLI utility classes.

The abstract class defines a factory method pattern through the load() class method,
which subclasses must implement to provide their own instantiation logic. This allows
for flexible configuration loading from various sources such as command-line arguments,
configuration files, or environment variables.

Key Components:
    AbstractCLIUtils: Abstract base class that defines the interface for CLI utility
                      classes, requiring implementation of a load() factory method.
"""

import abc
from typing import Any, Dict, Self

from pydantic import BaseModel


class AbstractCLIUtils(BaseModel, abc.ABC):
    """Abstract base class for CLI utility implementations.

    This class serves as the foundation for all command-line interface utilities in the
    transaction registrar system. It combines Pydantic's BaseModel capabilities for data
    validation and configuration management with Python's abstract base class mechanism
    to enforce a consistent interface.

    Subclasses must implement the load() class method to provide their own instantiation
    logic. This factory method pattern allows for flexible configuration loading from
    various sources such as command-line arguments, configuration files, or environment
    variables.

    The class is designed to be extended by utility classes that need to integrate with
    the CLI system, such as MainCLIUtils for main CLI operations, BaseCLIConnectorWrapper
    for database connector management, and plugin-specific CLI utilities.

    Note:
        This is an abstract class and cannot be instantiated directly. Subclasses must
        implement the load() method to be usable.

    Example:
        Subclasses should implement the load() method to provide their own instantiation
        logic:

        .. code-block:: python

            class MyCLIUtils(AbstractCLIUtils):
                @classmethod
                def load(cls, **kwargs) -> Self:
                    # Custom instantiation logic
                    return cls(**kwargs)
    """

    @classmethod
    @abc.abstractmethod
    def parse_cli_args(cls, **kwargs) -> Dict[str, Any]:
        """Factory method to create and configure an instance of the CLI utility class with error handling."""

    @classmethod
    @abc.abstractmethod
    def load(cls, **kwargs) -> Self:
        """Factory method to create and configure an instance of the CLI utility class.

        This abstract method must be implemented by subclasses to provide their own
        instantiation and configuration logic. The method typically parses keyword
        arguments (often from command-line arguments or configuration sources) and
        returns a configured instance of the class.

        Args:
            **kwargs: Arbitrary keyword arguments used for configuration. The specific
                     arguments required depend on the subclass implementation. Common
                     sources include command-line arguments, configuration files, or
                     environment variables.

        Returns:
            Self: An instance of the subclass with configuration applied. The instance
                  is typically validated using Pydantic's model validation mechanisms.

        Raises:
            NotImplementedError: This method is abstract and must be implemented by
                                 subclasses. Direct calls to this method on
                                 AbstractCLIUtils will raise this error.

        Note:
            Subclasses should use Pydantic's model validation features to ensure the
            configuration is valid before returning the instance. The method may also
            perform additional setup such as initializing database connections or
            loading plugins.

        Example:
            A typical implementation might look like:

            .. code-block:: python

                @classmethod
                def load(cls, **kwargs) -> Self:
                    # Parse and validate arguments
                    instance = cls(**kwargs)
                    # Perform additional setup if needed
                    return instance
        """

    @abc.abstractmethod
    def run(self) -> Self:
        """Run the CLI utility.

        This abstract method must be implemented by subclasses to provide their own
        run logic. The method typically performs the main operation of the CLI utility,
        such as loading data, processing input, or generating output.

        Returns:
            Self: The CLI utility instance for method chaining.
        """

    @abc.abstractmethod
    def stop(self) -> Self:
        """Shutdown the CLI utility.

        This abstract method must be implemented by subclasses to provide their own
        shutdown logic. The method typically performs the necessary cleanup operations,
        such as closing database connections or releasing resources. This method should
        be called when the CLI utility is no longer needed and should be the last method
        called before exiting the program.

        Returns:
            Self: The CLI utility instance for method chaining.
        """
