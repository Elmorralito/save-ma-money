"""
Abstract builder interface for transaction contract construction.

This module defines the base abstract builder class for creating transaction contracts
in the transaction registration system. It establishes a common interface for building
loaders, services, and handlers that work together to process transaction data.
The builder pattern implemented here allows for step-by-step construction of complex
contract objects with proper dependency injection.
"""

import abc
from typing import Generic, Self, TypeVar

from pydantic import BaseModel, ConfigDict

from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.services.base import BaseService
from papita_txnsregistrar.contracts.plugin import L
from papita_txnsregistrar.handlers.abstract import AbstractLoadHandler

H = TypeVar("H", bound=AbstractLoadHandler)


class AbstractContractBuilder(BaseModel, Generic[H, L], metaclass=abc.ABCMeta):
    """
    Abstract base class for transaction contract builders.

    This class combines Pydantic's validation capabilities with a generic abstract interface
    for building transaction processing components. Concrete builder implementations must
    inherit from this class and implement its abstract methods to provide specific building
    behavior for different types of transaction contracts.

    The builder follows a fluent interface pattern, allowing method chaining for a
    step-by-step construction process of loader, service, and handler components.

    Attributes:
        connection: SQL database connector for database operations.
        handler: Handler instance for processing loaded data, initialized as None.
        loader: Loader instance for loading transaction data, initialized as None.
        service: Service instance for business logic operations, initialized as None.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    connection: SQLDatabaseConnector
    handler: H | None = None
    loader: L | None = None
    service: BaseService | None = None

    @abc.abstractmethod
    def build_loader(self, **kwargs) -> Self:
        """
        Build and configure the loader component.

        This method should implement the logic for creating and configuring
        a loader instance that will be responsible for loading transaction data
        from appropriate sources.

        Args:
            **kwargs: Implementation-specific parameters needed for loader configuration.

        Returns:
            Self: The builder instance for method chaining.
        """

    @abc.abstractmethod
    def build_service(self, **kwargs) -> Self:
        """
        Build and configure the service component.

        This method should implement the logic for creating and configuring
        a service instance that will contain the business logic for processing
        transaction data.

        Args:
            **kwargs: Implementation-specific parameters needed for service configuration.

        Returns:
            Self: The builder instance for method chaining.
        """

    @abc.abstractmethod
    def build_handler(self, **kwargs) -> Self:
        """
        Build and configure the handler component.

        This method should implement the logic for creating and configuring
        a handler instance that will be responsible for processing the loaded
        transaction data.

        Args:
            **kwargs: Implementation-specific parameters needed for handler configuration.

        Returns:
            Self: The builder instance for method chaining.
        """

    def build(self, **kwargs) -> Self:
        """
        Build the complete contract by creating all components in sequence.

        This method orchestrates the building process by calling the three
        specialized build methods in order: build_service, build_handler, and build_loader.

        Args:
            **kwargs: Implementation-specific parameters passed to all build methods.

        Returns:
            Self: The builder instance with all components fully configured.
        """
        return self.build_service(**kwargs).build_handler(**kwargs).build_loader(**kwargs)
