"""
Handler Factory Module.

This module provides a factory pattern implementation for loading and creating handler instances.
The HandlerFactory is a singleton class responsible for discovering, registering, and instantiating
handler classes that extend the AbstractLoadHandler base class. It enables dynamic discovery of
handlers from specified modules and provides a centralized access point for handler creation.
"""

import logging
from typing import ClassVar, Dict, Iterable, Tuple, Type

from papita_txnsmodel.utils.classutils import ClassDiscovery, MetaSingleton
from papita_txnsregistrar import LIB_NAME
from papita_txnsregistrar.handlers.abstract import AbstractLoadHandler
from papita_txnsregistrar.utils.modelutils import validate_tags

logger = logging.getLogger(__name__)


class HandlerRegistry(metaclass=MetaSingleton):
    """
    A singleton registry class for managing and creating handler instances.
    """

    __slots__ = ("handlers",)

    def __init__(self):
        self.handlers: Dict[str, Type[AbstractLoadHandler]] = {}

    def set_handlers(self, handlers: Dict[str, Type[AbstractLoadHandler]]) -> "HandlerRegistry":
        """
        Set the handlers dictionary.
        """
        self.handlers = handlers
        return self

    def get_handler(self, labels: Iterable[str]) -> Type[AbstractLoadHandler]:
        """
        Get a handler by type.
        """
        if isinstance(labels, str):
            labels = validate_tags((labels,))

        logger.info("Searching for handlers with labels %s", labels)
        for label in validate_tags(labels):
            if label in self.handlers:
                return self.handlers[label]

        raise ValueError(f"Handler type '{validate_tags(labels)}' is not recognized.")

    def get_handlers(self) -> Dict[str, Type[AbstractLoadHandler]]:
        """
        Get the handlers dictionary.
        """
        return self.handlers

    def register_handler(self, handler_type: str, handler: Type[AbstractLoadHandler]) -> "HandlerRegistry":
        """
        Register a handler by type.
        """
        self.handlers[handler_type] = handler
        return self

    def register_handlers_on_multiple_labels(
        self, labels: Iterable[str], handler: Type[AbstractLoadHandler]
    ) -> "HandlerRegistry":
        """
        Register a handler by multiple labels.
        """
        for label in labels:
            self.register_handler(label, handler)

        return self

    def unregister_handler(self, handler_type: str) -> "HandlerRegistry":
        """
        Unregister a handler by type.
        """
        self.handlers.pop(handler_type, None)
        return self

    def clear_handlers(self) -> "HandlerRegistry":
        """
        Clear the handlers dictionary.
        """
        self.handlers.clear()
        return self


class HandlerFactory:
    """
    A singleton factory class for managing and creating handler instances.

    This factory discovers, registers, and instantiates handler classes that extend the
    AbstractLoadHandler base class. It uses the MetaSingleton metaclass to ensure only one
    instance exists throughout the application. Handlers can be registered with multiple
    labels to allow flexible access by different identifiers.

    Attributes:
        handlers (Dict[str, Type[AbstractLoadHandler]]): Dictionary mapping handler names/labels
            to their respective handler classes.
    """

    registry: ClassVar[HandlerRegistry] = HandlerRegistry()

    @classmethod
    def load(cls, *modules, **kwargs) -> Type["HandlerFactory"]:
        """
        Load and register handlers from the specified modules.

        Discovers all classes that inherit from AbstractLoadHandler in the given modules
        and registers them in the handlers dictionary. Each handler can be registered under
        multiple labels defined by its labels() method, as well as its class name.

        Args:
            *modules: Variable length list of module names to search for handlers.
            **kwargs: Additional parameters (unused).

        Returns:
            HandlerFactory: Self reference for method chaining.

        Notes:
            If no modules are specified, the LIB_NAME module is always included in the search.
            Handlers without a valid labels() implementation are skipped.
        """
        for mod_ in set(modules) | {LIB_NAME}:
            for cls_ in ClassDiscovery.get_children(mod_, AbstractLoadHandler):
                if cls_ == AbstractLoadHandler or getattr(cls_, "labels", None) is None:
                    continue

                try:
                    labels = validate_tags(cls_.labels() + (cls_.__name__,))
                    cls.registry = cls.registry.register_handlers_on_multiple_labels(labels, cls_)
                    logger.debug("Registered handler %s with labels %s", cls_.__name__, labels)
                except NotImplementedError:
                    continue

        return cls

    @classmethod
    def get(cls, labels: Tuple[str, ...], **_) -> Type[AbstractLoadHandler]:
        """
        Get an instance of the specified handler type.

        Retrieves the handler class corresponding to the provided handler_type and
        instantiates it with the given kwargs.

        Args:
            handler_type (str): The type or label of handler to create.
            **kwargs: Additional parameters to pass to the handler constructor.

        Returns:
            AbstractLoadHandler: An instance of the requested handler type.

        Raises:
            ValueError: If the specified handler type is not recognized or registered.
        """
        return cls.registry.get_handler(labels)
