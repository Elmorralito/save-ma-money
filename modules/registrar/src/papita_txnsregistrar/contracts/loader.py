# type: ignore
"""
Plugin Decorator Module.

This module provides a decorator for registering plugin classes with the system.
It handles the validation of plugin types and their metadata, and performs
the registration of plugins with the central Registry.

Functions:
    plugin: A decorator function for registering plugin implementations.
"""

from typing import Any, Callable, Type, TypeVar

from .meta import PluginMetadata
from .plugin import PluginContract
from .registry import Registry

P = TypeVar("P", bound=PluginContract)


def plugin(
    *,
    meta: PluginMetadata | dict[str, Any],
) -> Callable[[Type[P]], Type[P]]:
    """
    Decorator for registering plugin implementations.

    This decorator validates that a class is a proper plugin implementation
    and registers it with the system's registry along with its metadata.
    When used to decorate a plugin class, it validates both the class type
    and the provided metadata, then registers the plugin in the central registry.

    Args:
        loader_type (Type[AbstractLoader] | None): The loader type to associate with this plugin.
        meta (PluginMetadata | dict[str, Any]): Metadata about the plugin, either
            as a PluginMetadata object or a dictionary that can be validated into one.

    Raises:
        TypeError: If the class is not a valid PluginContract implementation.
        ValueError: If the metadata is not in a supported format.

    Example:
        >>> @plugin(meta={"name": "my_plugin", "version": "1.0.0"}, loader_type=MyLoader)
        ... class MyPluginImplementation(PluginContract):
        ...     pass
    """
    if not isinstance(meta, (dict, PluginMetadata)):
        raise ValueError("Metadata not supported.")

    validated_meta = PluginMetadata.model_validate(meta, strict=True)

    def decorator(cls: P) -> P:
        if not issubclass(cls, PluginContract):
            raise TypeError("Plugin type not supported.")

        setattr(cls, "__meta__", validated_meta)
        Registry().register(cls, validated_meta)
        return cls

    return decorator
