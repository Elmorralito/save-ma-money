"""
Handler Factory Module.

This module provides a factory pattern implementation for loading and creating handler instances.
The HandlerFactory is a singleton class responsible for discovering, registering, and instantiating
handler classes that extend the AbstractLoadHandler base class. It enables dynamic discovery of
handlers from specified modules and provides a centralized access point for handler creation.
"""

from typing import Dict, Type

from papita_txnsmodel.utils.classutils import ClassDiscovery, MetaSingleton
from papita_txnsregistrar import LIB_NAME
from papita_txnsregistrar.handlers.abstract import AbstractLoadHandler
from papita_txnsregistrar.utils.modelutils import validate_tags


class HandlerFactory(metaclass=MetaSingleton):
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

    __slots__ = ("handlers",)

    def __init__(self):
        """
        Initialize a new HandlerFactory instance with an empty handlers dictionary.
        """
        self.handlers: Dict[str, Type[AbstractLoadHandler]] = {}

    def load(self, *modules, **kwargs) -> "HandlerFactory":
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
        handlers = self.handlers
        if isinstance(handlers, dict) and not modules:
            return self

        for mod_ in set(modules) | {LIB_NAME}:
            for cls_ in ClassDiscovery.get_children(mod_, AbstractLoadHandler):
                if cls_ == AbstractLoadHandler:
                    continue

                try:
                    handlers.update({label: cls_ for label in tuple(validate_tags(cls_.labels())) + (cls_.__name__,)})
                except NotImplementedError:
                    continue

        self.handlers = handlers
        return self

    def get(self, handler_type: str, **kwargs) -> AbstractLoadHandler:
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
        if handler_type not in self.handlers:
            raise ValueError(f"Handler type '{handler_type}' is not recognized.")

        handler_class = self.handlers[handler_type]
        return handler_class(**kwargs)
