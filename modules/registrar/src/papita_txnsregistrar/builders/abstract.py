"""
Abstract builder interface for transaction contract construction.

This module defines the base abstract builder class for creating transaction contracts
in the transaction registration system. It establishes a common interface for building
components that work together to process transaction data:

- Loaders: Responsible for retrieving transaction data from various sources
- Services: Contain business logic for processing transaction data
- Handlers: Process and transform the loaded transaction data

The builder pattern implemented here allows for step-by-step construction of complex
transaction contract objects with proper dependency injection and follows a fluent
interface design for method chaining.
"""

import abc
from typing import Generic, Self, Type, TypeVar

from pydantic import BaseModel, ConfigDict

from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.utils.classutils import FallbackAction
from papita_txnsregistrar.handlers.abstract import AbstractLoadHandler
from papita_txnsregistrar.loaders.abstract import AbstractLoader

L = TypeVar("L", bound=AbstractLoader)


class AbstractContractBuilder(BaseModel, Generic[L], metaclass=abc.ABCMeta):
    """Abstract base class for building transaction processing contracts.

    This abstract builder defines the interface for constructing transaction contracts
    with all necessary components. It implements the builder design pattern to create
    complex objects step by step, allowing for separation of construction logic from
    representation and enabling the same construction process to create different
    representations.

    The builder manages three primary components:
    - Loader: For retrieving data from various sources
    - Handler: For processing and transforming data
    - Service: For implementing business logic and interactions

    This class is intended to be subclassed by concrete builders that implement the
    abstract methods for specific transaction processing scenarios.

    Attributes:
        connector: Database connector for accessing transaction data storage.
        handler: The handler instance or type for processing transaction data.
        loader: The loader instance for retrieving transaction data.
        service: The service instance containing business logic implementation.
        on_failure_do: Action to take when operations fail, defaults to raising exceptions.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    connector: SQLDatabaseConnector
    handler: Type[AbstractLoadHandler] | AbstractLoadHandler | None = None
    loader: L | None = None
    service: BaseService | None = None
    on_failure_do: FallbackAction = FallbackAction.RAISE

    @classmethod
    def loader_type(cls) -> Type[L]:
        """Get the loader type associated with this builder.

        Retrieves the expected type of the loader from the class's type annotations.
        This is useful for type checking and dependency resolution in the builder
        framework.

        Returns:
            Type[L]: The loader type class that this builder is parameterized with.
        """
        return cls.model_fields["loader"].annotation

    @abc.abstractmethod
    def build_loader(self, **kwargs) -> Self:
        """
        Build and configure the loader component.

        This method should implement the logic for creating and configuring
        a loader instance that will be responsible for loading transaction data
        from appropriate sources. The loader is typically responsible for data
        retrieval operations.

        Args:
            **kwargs: Implementation-specific parameters needed for loader configuration.
                These vary based on the concrete builder implementation.

        Returns:
            Self: The builder instance for method chaining.

        Note:
            Concrete implementations should set the `loader` attribute and return self.
        """

    @abc.abstractmethod
    def build_handler(self, **kwargs) -> Self:
        """
        Build and configure the handler component.

        This method should implement the logic for creating and configuring
        a handler instance that will be responsible for processing the loaded
        transaction data. Handlers typically transform, validate, or perform
        operations on data provided by loaders.

        Args:
            **kwargs: Implementation-specific parameters needed for handler configuration.
                These vary based on the concrete builder implementation.

        Returns:
            Self: The builder instance for method chaining.

        Note:
            Concrete implementations should set the `handler` attribute and return self.
        """

    @abc.abstractmethod
    def build_service(self, **kwargs) -> Self:
        """
        Build and configure the service component.

        This method should implement the logic for creating and configuring
        a service instance that will contain the business logic for processing
        transaction data. Services typically implement domain-specific operations
        and may interact with repositories or other external systems.

        Args:
            **kwargs: Implementation-specific parameters needed for service configuration.
                These vary based on the concrete builder implementation.

        Returns:
            Self: The builder instance for method chaining.

        Note:
            Concrete implementations should set the `service` attribute and return self.
        """

    @abc.abstractmethod
    def build(self, **kwargs) -> Self:
        """
        Build the complete contract by creating all components in sequence.

        This method orchestrates the building process by calling the three
        specialized build methods in order: build_service, build_handler, and build_loader.
        This ensures proper dependency injection and initialization order.

        Args:
            **kwargs: Implementation-specific parameters passed to all build methods.
                These parameters will be forwarded to each component's build method.

        Returns:
            Self: The builder instance with all components fully configured.

        Example:
            ```python
            # Create a complete contract with a single call
            contract = ConcreteBuilder(connection=db_conn).build(param1="value")
            ```
        """
