"""
Base implementation of the contract builder interface.

This module provides a base implementation of the AbstractContractBuilder interface
that serves as a foundation for specific contract builder implementations. It offers
default implementations for some builder methods while requiring concrete subclasses
to implement the core building logic.
"""

from typing import Generic, Self

from papita_txnsregistrar.builders.abstract import AbstractContractBuilder, H
from papita_txnsregistrar.contracts.plugin import L


class BaseContractBuilder(AbstractContractBuilder, Generic[H, L]):
    """
    Base implementation of the contract builder.

    This class provides a minimal implementation of the AbstractContractBuilder
    interface with default no-op implementations for build_service and build_handler
    methods, while requiring subclasses to implement the build_loader method.
    The base implementation facilitates method chaining by returning self for
    methods that don't require specific implementation at this level.

    Attributes:
        Inherits all attributes from AbstractContractBuilder.
    """

    def build_loader(self, **kwargs) -> Self:
        """
        Build and configure the loader component.

        This method must be implemented by concrete subclasses to create
        and configure a loader instance specific to their requirements.

        Args:
            **kwargs: Implementation-specific parameters needed for loader configuration.

        Returns:
            Self: The builder instance for method chaining.

        Raises:
            NotImplementedError: Always raised as this method must be overridden.
        """
        raise NotImplementedError("Subclasses must implement build_loader method")

    def build_service(self, **kwargs) -> Self:
        """
        Build and configure the service component.

        This base implementation is a no-op that simply returns the builder instance.
        Subclasses can override this method to provide specific service building logic.

        Args:
            **kwargs: Implementation-specific parameters needed for service configuration.

        Returns:
            Self: The builder instance for method chaining.
        """
        return self

    def build_handler(self, **kwargs) -> Self:
        """
        Build and configure the handler component.

        This base implementation is a no-op that simply returns the builder instance.
        Subclasses can override this method to provide specific handler building logic.

        Args:
            **kwargs: Implementation-specific parameters needed for handler configuration.

        Returns:
            Self: The builder instance for method chaining.
        """
        return self
