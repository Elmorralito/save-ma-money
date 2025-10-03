"""Base handler module for the Papita Transactions system.

This module provides the foundation for all handlers in the Papita Transactions system.
It defines the BaseHandler class which implements common functionality for interacting
with services and managing error handling across the application's handler layer.

Classes:
    BaseHandler: Generic base class for all handlers in the Papita Transactions system.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.utils.classutils import FallbackAction

T = TypeVar("T", bound=BaseService)


class BaseHandler(BaseModel, Generic[T]):
    """Base handler class for interacting with services in the Papita Transactions system.

    This class serves as the foundation for all handler classes in the system,
    providing common functionality for service management and error handling.
    It uses a generic type parameter to ensure type safety when working with
    different service types.

    Attributes:
        service (T | None): The service instance this handler works with.
            Defaults to None and must be set via setup_service before use.
        error_handler (FallbackAction): Strategy to use when errors occur.
            Defaults to FallbackAction.RAISE which will propagate exceptions.
    """

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    service: T | None = None
    error_handler: FallbackAction = FallbackAction.RAISE

    def setup_service(self, service: T, **kwargs) -> "BaseHandler":
        """Configure the handler with a service instance.

        This method sets up the handler with a service instance that will be used
        for all subsequent operations. It validates that the service is of the
        correct type before assigning it.

        Args:
            service: The service instance to use with this handler.
            **kwargs: Additional keyword arguments for future extensibility.

        Returns:
            BaseHandler: The handler instance with the service configured.

        Raises:
            TypeError: If the provided service is not a subclass of BaseService.
        """
        if not isinstance(service, BaseService):
            raise TypeError("Service type not compatible with this handler.")

        self.service = service
        return self

    @property
    def checked_service(self) -> T:
        """Get the service instance with validation.

        This property provides access to the service instance after performing
        validation checks to ensure it's properly configured and connected.

        Returns:
            T: The validated service instance.

        Raises:
            ValueError: If the service has not been loaded via setup_service.
            Various exceptions: Depending on the error_handler configuration,
                connection issues may raise exceptions.
        """
        if not self.service:
            raise ValueError("The service has not being loaded.")

        self.connector.connected(on_disconnected=self.error_handler)
        return self.service
