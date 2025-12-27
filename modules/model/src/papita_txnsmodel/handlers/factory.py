"""
Handler Factory Module.

This module provides a factory pattern implementation for loading and creating handler instances.
The module consists of two main components: HandlerRegistry, a singleton registry for managing
handler registrations, and HandlerFactory, a factory class that discovers and instantiates
handler classes extending AbstractHandler.

The factory enables dynamic discovery of handlers from specified modules, automatically
registering them with multiple labels (from their labels() method and class name) for flexible
lookup. This design allows handlers to be accessed by various identifiers while maintaining
a centralized registry of available handler types.

Key Features:
    - Singleton registry pattern for global handler management
    - Automatic discovery of handler classes from modules
    - Multi-label registration for flexible handler lookup
    - Tag validation and normalization for consistent labeling
"""

import logging
from typing import ClassVar, Dict, Iterable, Tuple, Type

from papita_txnsmodel import LIB_NAME
from papita_txnsmodel.utils.classutils import ClassDiscovery, MetaSingleton
from papita_txnsmodel.utils.modelutils import validate_tags

from .abstract import AbstractHandler
from .base import BaseTableHandler

logger = logging.getLogger(__name__)


class HandlerRegistry(metaclass=MetaSingleton):
    """
    Singleton registry for managing handler class registrations.

    This registry maintains a dictionary mapping handler labels to their corresponding handler
    classes. It implements the singleton pattern via MetaSingleton to ensure only one instance
    exists throughout the application lifecycle. The registry provides methods for registering,
    unregistering, and retrieving handlers by their labels.

    Attributes:
        handlers: Dictionary mapping string labels to handler class types. Each handler can
            be registered under multiple labels for flexible lookup.

    Note:
        This class uses __slots__ for memory optimization and implements the singleton pattern
        to ensure consistent handler registration across the application.
    """

    __slots__ = ("handlers",)

    def __init__(self):
        """Initialize an empty handler registry."""
        self.handlers: Dict[str, Type[AbstractHandler]] = {}

    def parse_labels(self, labels: Iterable[str] | str) -> Iterable[str]:
        """Parse and validate handler labels into a normalized iterable.

        Converts various input formats (string, iterable, or other types) into a validated
        tuple of normalized tag strings. The labels are validated using validate_tags to ensure
        they conform to the expected tag format (alphanumeric with hyphens/underscores).

        Args:
            labels: A single label string, an iterable of label strings, or any value that
                can be converted to a string. If a string is provided, it's wrapped in a tuple.
                If not an iterable, the value is converted to a string and wrapped.

        Returns:
            Iterable[str]: A tuple of validated and normalized label strings. All labels are
                converted to lowercase, stripped of whitespace, and validated for format.

        Raises:
            ValueError: If the labels cannot be validated or no valid tags are found after
                normalization.
        """
        if isinstance(labels, str):
            labels_ = [labels]
        elif not isinstance(labels, Iterable):
            labels_ = [str(labels)]
        else:
            labels_ = [str(label) for label in labels]

        return validate_tags(labels_)

    def set_handlers(self, handlers: Dict[str, Type[AbstractHandler]]) -> "HandlerRegistry":
        """Replace the entire handlers dictionary with a new one.

        This method replaces all existing handler registrations with the provided dictionary.
        Use with caution as it will remove all previously registered handlers.

        Args:
            handlers: Dictionary mapping label strings to handler class types that will
                replace the current handlers dictionary.

        Returns:
            HandlerRegistry: Self reference for method chaining.
        """
        self.handlers = handlers
        return self

    def get_handler(self, labels: Iterable[str] | str) -> Type[AbstractHandler]:
        """Retrieve a handler class by one of its registered labels.

        Searches through the parsed labels to find the first matching handler in the registry.
        The method attempts to match each label in order until a registered handler is found.
        This allows handlers to be retrieved using any of their registered labels.

        Args:
            labels: A single label string or iterable of label strings to search for. The
                labels are parsed and validated before searching.

        Returns:
            Type[AbstractHandler]: The handler class type associated with the first matching
                label found in the registry.

        Raises:
            ValueError: If none of the provided labels match any registered handler, or if
                the labels cannot be validated.
        """
        logger.info("Searching for handlers with labels %s", labels)
        labels_ = self.parse_labels(labels)
        for label in labels_:
            if label in self.handlers:
                return self.handlers[label]

        raise ValueError(f"Handler type with labels '{labels_}' is not recognized.")

    def get_handlers(self) -> Dict[str, Type[AbstractHandler]]:
        """Retrieve the complete handlers registry dictionary.

        Returns a reference to the internal handlers dictionary. Modifications to the
        returned dictionary will affect the registry state.

        Returns:
            Dict[str, Type[AbstractHandler]]: Dictionary mapping label strings to handler
                class types. This is the same dictionary used internally by the registry.
        """
        return self.handlers

    def register_handler(self, handler_type: str, handler: Type[AbstractHandler]) -> "HandlerRegistry":
        """Register a handler class under a specific label.

        Associates a handler class with a label string in the registry. If the label already
        exists, the previous handler is replaced. This allows manual registration of handlers
        or updating existing registrations.

        Args:
            handler_type: The label string under which to register the handler. This label
                will be used to retrieve the handler later.
            handler: The handler class type (subclass of AbstractHandler) to register.

        Returns:
            HandlerRegistry: Self reference for method chaining.
        """
        self.handlers[handler_type] = handler
        return self

    def register_handlers_on_multiple_labels(
        self, labels: Iterable[str], handler: Type[AbstractHandler]
    ) -> "HandlerRegistry":
        """Register a handler class under multiple labels simultaneously.

        Registers the same handler class under all provided labels, enabling flexible lookup
        by any of the registered labels. This is useful when a handler should be accessible
        by multiple identifiers (e.g., class name, aliases, or descriptive tags).

        Args:
            labels: Iterable of label strings under which to register the handler. Each label
                will be parsed and validated before registration.
            handler: The handler class type (subclass of AbstractHandler) to register under
                all provided labels.

        Returns:
            HandlerRegistry: Self reference for method chaining.

        Raises:
            ValueError: If the labels cannot be validated or no valid tags are found.
        """
        for label in self.parse_labels(labels):
            self.register_handler(label, handler)

        return self

    def unregister_handler(self, handler_type: str) -> "HandlerRegistry":
        """Remove a handler registration by its label.

        Removes the handler associated with the specified label from the registry. If the
        label does not exist, the operation completes without error (idempotent operation).

        Args:
            handler_type: The label string of the handler to unregister. If the label is
                not found, no error is raised.

        Returns:
            HandlerRegistry: Self reference for method chaining.
        """
        self.handlers.pop(handler_type, None)
        return self

    def clear_handlers(self) -> "HandlerRegistry":
        """Remove all handler registrations from the registry.

        Clears the entire handlers dictionary, removing all registered handlers. This
        operation cannot be undone and should be used with caution, typically for testing
        or reset scenarios.

        Returns:
            HandlerRegistry: Self reference for method chaining.
        """
        self.handlers.clear()
        return self


class HandlerFactory:
    """
    Factory class for discovering, registering, and retrieving handler instances.

    This factory provides a centralized mechanism for discovering handler classes that extend
    AbstractHandler from specified modules and registering them for later retrieval. The factory
    uses a HandlerRegistry singleton to maintain handler registrations across the application.

    The factory automatically discovers handler classes by scanning modules for classes that
    inherit from AbstractHandler. Each discovered handler is registered under multiple labels:
    the labels returned by its labels() class method and its class name. This multi-label
    registration enables flexible handler lookup using various identifiers.

    Attributes:
        registry: Class variable holding the singleton HandlerRegistry instance used for
            managing handler registrations. This registry is shared across all HandlerFactory
            operations.
    """

    registry: ClassVar[HandlerRegistry] = HandlerRegistry()

    @classmethod
    def load(cls, *modules, **kwargs) -> Type["HandlerFactory"]:
        """Discover and register handlers from specified modules.

        Scans the provided modules for classes that inherit from AbstractHandler and
        automatically registers them in the factory's registry. Each handler is registered
        under multiple labels: all labels returned by its labels() class method plus its
        class name. This enables flexible handler lookup using various identifiers.

        The discovery process:
            1. Scans each module for classes inheriting from AbstractHandler
            2. Skips abstract base classes (AbstractHandler, BaseTableHandler)
            3. Validates that each handler implements the labels() class method
            4. Registers valid handlers under all their labels and class name

        Args:
            *modules: Variable length list of module name strings to search for handlers.
                Module names should be fully qualified (e.g., 'papita_txnsmodel.handlers').
            **kwargs: Additional keyword arguments (currently unused, reserved for future
                configuration options).

        Returns:
            Type[HandlerFactory]: The HandlerFactory class itself, enabling method chaining.

        Note:
            If no modules are provided, the LIB_NAME module (papita_txnsmodel) is always
            included in the search. Handlers that raise NotImplementedError from their
            labels() method or lack the labels() method entirely are silently skipped.
            Only concrete handler implementations with valid labels are registered.
        """
        for mod_ in set(modules) | {LIB_NAME}:
            logger.debug("Loading handlers from module: %s", mod_)
            for cls_ in ClassDiscovery.get_children(mod_, AbstractHandler):
                if cls_ in (AbstractHandler, BaseTableHandler) or getattr(cls_, "labels", None) is None:
                    continue

                try:
                    labels = cls_.labels()
                    if not labels:
                        continue

                    labels_ = tuple(cls.registry.parse_labels(labels)) + (cls_.__name__,)
                    cls.registry = cls.registry.register_handlers_on_multiple_labels(labels_, cls_)
                    logger.debug("Registered handler %s with labels %s", cls_.__name__, labels_)
                except NotImplementedError:
                    continue

        return cls

    @classmethod
    def get(cls, labels: Tuple[str, ...], **_) -> Type[AbstractHandler]:
        """Retrieve a handler class type by its registered labels.

        Looks up a handler class in the registry using the provided labels. The method
        searches through the labels in order and returns the first matching handler class
        found. This returns the handler class type, not an instance, allowing callers to
        instantiate the handler with their own parameters.

        Args:
            labels: Tuple of label strings to search for. The method will attempt to match
                each label in sequence until a registered handler is found.
            **_: Additional keyword arguments (currently unused, reserved for future
                functionality). The underscore prefix indicates these are intentionally
                ignored.

        Returns:
            Type[AbstractHandler]: The handler class type associated with the first matching
                label. This is a class, not an instance, and must be instantiated separately.

        Raises:
            ValueError: If none of the provided labels match any registered handler in the
                registry. This typically indicates the handler has not been loaded or
                registered, or the label is incorrect.
        """
        return cls.registry.get_handler(labels)
