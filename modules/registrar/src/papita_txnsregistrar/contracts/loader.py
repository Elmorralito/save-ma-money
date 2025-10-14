"""
Plugin Decorator Module.

This module provides a decorator for registering plugin classes with the system.
It handles the validation of plugin types and their metadata, and performs
the registration of plugins with the central Registry.

Classes:
    plugin: A decorator class for registering plugin implementations.
"""

from typing import Any, Type

from papita_txnsregistrar.handlers.abstract import AbstractLoadHandler
from papita_txnsregistrar.loaders.abstract import AbstractLoader

from .meta import PluginMetadata
from .plugin import PluginContract
from .registry import Registry


class plugin:  # pylint: disable=C0103
    """
    Decorator for registering plugin implementations.

    This decorator validates that a class is a proper plugin implementation
    and registers it with the system's registry along with its metadata.
    When used to decorate a plugin class, it validates both the class type
    and the provided metadata, then registers the plugin in the central registry.

    Args:
        cls (type[PluginContract]): The plugin class to register.
        meta (PluginMetadata | dict[str, Any]): Metadata about the plugin, either
            as a PluginMetadata object or a dictionary that can be validated into one.

    Raises:
        TypeError: If the class is not a valid PluginContract implementation.
        ValueError: If the metadata is not in a supported format.

    Example:
        >>> @plugin(MyPluginClass, {"name": "my_plugin", "version": "1.0.0"})
        ... class MyPluginImplementation(PluginContract):
        ...     pass
    """

    def __init__(
        self,
        cls: Type[PluginContract],
        *,
        handler_type: Type[AbstractLoadHandler],
        loader_type: Type[AbstractLoader],
        meta: PluginMetadata | dict[str, Any],
    ):
        """
        Initialize the plugin decorator.

        Args:
            cls (type[PluginContract]): The plugin class to register.
            meta (PluginMetadata | dict[str, Any]): Metadata about the plugin.

        Raises:
            TypeError: If the class is not a valid PluginContract implementation.
            ValueError: If the metadata is not in a supported format.
        """
        if not isinstance(cls, PluginContract):
            raise TypeError("Plugin type not supported.")

        if not isinstance(meta, (dict, PluginMetadata)):
            raise ValueError("Metadata not supported.")

        if handler_type == AbstractLoadHandler:
            raise TypeError("The handler descriptor cannot be abstract.")

        if handler_type == AbstractLoader:
            raise TypeError("The loader descriptor cannot be abstract.")

        self.cls = cls[handler_type, loader_type]  # type: ignore[index]
        self.meta = PluginMetadata.model_validate(meta, strict=True)
        self.cls.__meta__ = self.meta
        Registry().register(self.cls, self.meta)

    def __call__(self, *args, **kwargs):
        """
        Create an instance of the decorated plugin class.

        This method allows the decorated class to be instantiated normally,
        passing through any arguments to the class constructor.

        Args:
            *args: Positional arguments to pass to the plugin class constructor.
            **kwargs: Keyword arguments to pass to the plugin class constructor.

        Returns:
            An instance of the decorated plugin class.
        """
        return self.cls(*args, **kwargs)
