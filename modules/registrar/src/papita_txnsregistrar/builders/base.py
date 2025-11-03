"""
Base implementation of the contract builder interface.

This module provides a base implementation of the AbstractContractBuilder interface
that serves as a foundation for specific contract builder implementations. It offers
default implementations for some builder methods while requiring concrete subclasses
to implement the core building logic.
"""

import logging
from typing import Generic, Self, TypeVar

from papita_txnsregistrar.builders.abstract import AbstractContractBuilder
from papita_txnsregistrar.loaders.abstract import AbstractLoader

logger = logging.getLogger(__name__)

L = TypeVar("L", bound=AbstractLoader)


class BaseContractBuilder(AbstractContractBuilder, Generic[L]):
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
        self.loader = self.loader_type().model_validate(**kwargs)
        return self

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
        if not self.handler:
            raise ValueError("Handler not built.")

        logger.debug("Building service for handler %s", self.handler.labels())
        for remove_key in "handler_modules", "connector", "connection":
            kwargs.pop(remove_key, None)

        on_failure_do = kwargs.pop("on_failure_do", None) or self.on_failure_do
        missing_upsertions_tol = kwargs.pop("missing_upsertions_tol", None)
        self.service = self.handler.service_type().model_validate(
            {
                "connector": self.connector,
                "on_failure_do": on_failure_do,
                **({} if missing_upsertions_tol is None else {"missing_upsertions_tol": missing_upsertions_tol}),
                **kwargs,
            }
        )
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
        raise NotImplementedError("Subclasses must implement build_handler method")
