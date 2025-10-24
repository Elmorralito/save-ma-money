from typing import Dict, Type

from papita_txnsmodel.utils.classutils import ClassDiscovery, MetaSingleton
from papita_txnsregistrar import LIB_NAME
from papita_txnsregistrar.handlers.abstract import AbstractLoadHandler
from papita_txnsregistrar.utils.modelutils import validate_tags


class HandlerFactory(metaclass=MetaSingleton):
    __slots__ = ("handlers",)

    def __init__(self):
        self.handlers: Dict[str, Type[AbstractLoadHandler]] = {}

    def load(self, *modules, **kwargs) -> "HandlerFactory":
        """
        Factory method to create handler instances based on the specified type.

        Args:
            handler_type (str): The type of handler to create.
            **kwargs: Additional parameters to pass to the handler constructor.

        Returns:
            AbstractLoadHandler: An instance of the requested handler type.

        Raises:
            ValueError: If the specified handler type is not recognized.
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

        Args:
            handler_type (str): The type of handler to create.
            **kwargs: Additional parameters to pass to the handler constructor.

        Returns:
            AbstractLoadHandler: An instance of the requested handler type.

        Raises:
            ValueError: If the specified handler type is not recognized.
        """
        if handler_type not in self.handlers:
            raise ValueError(f"Handler type '{handler_type}' is not recognized.")

        handler_class = self.handlers[handler_type]
        return handler_class(**kwargs)
