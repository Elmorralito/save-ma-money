# type: ignore
"""
Plugin registration and loading utilities for the transaction tracker system.

This module provides core functionality for managing plugin lifecycle in the transaction tracking
system. It includes a decorator for registering plugin classes with metadata validation, and a
function for dynamically discovering and loading plugins from specified modules with retry logic
and error handling.

The module integrates with the central Registry singleton to maintain a collection of available
plugins, enabling dynamic plugin discovery and retrieval by name with optional fuzzy matching
capabilities.

Key Components:
    plugin: Decorator function that validates and registers plugin implementations with the
            central registry, ensuring proper metadata validation and type checking.
    load_plugin: Function that discovers plugins from specified modules and retrieves a plugin
                 class by name, with built-in retry logic for handling intermittent registration
                 issues and comprehensive error handling.
"""

import contextlib
import inspect
import logging
from typing import Any, Callable, List, Type, TypeVar

from .meta import PluginMetadata
from .plugin import PluginContract
from .registry import Registry

logger = logging.getLogger(__name__)

P = TypeVar("P", bound=PluginContract)


def plugin(
    *,
    meta: PluginMetadata | dict[str, Any],
) -> Callable[[Type[P]], Type[P]]:
    """Decorator for registering plugin implementations with the central registry.

    This decorator validates that a class is a proper plugin implementation and registers it
    with the system's registry along with its metadata. When applied to a plugin class, it
    performs validation of both the class type (ensuring it extends PluginContract) and the
    provided metadata (validating it against the PluginMetadata model), then registers the
    plugin in the central Registry singleton for later discovery and retrieval.

    The decorator uses keyword-only arguments to ensure explicit metadata specification and
    performs strict validation of the metadata structure using Pydantic's model validation.

    Args:
        meta: Metadata about the plugin, either as a PluginMetadata object or a dictionary
              that can be validated into a PluginMetadata instance. The dictionary must contain
              required fields such as 'name' and 'version', and may include optional fields
              like 'feature_tags', 'description', and 'enabled'.

    Returns:
        A decorator function that takes a plugin class and returns the same class after
        registration. The returned class is unchanged, allowing the decorator to be used
        without affecting the class definition.

    Raises:
        ValueError: If the metadata is not in a supported format (not a dict or
                    PluginMetadata instance), or if metadata validation fails during
                    Pydantic model validation.
        TypeError: If the decorated class is not a subclass of PluginContract, indicating
                   that it does not implement the required plugin interface.

    Note:
        The decorator modifies the class by registering it with the Registry singleton,
        but does not modify the class definition itself. The registration occurs at class
        definition time, making the plugin immediately available for discovery.
    """
    if not isinstance(meta, (dict, PluginMetadata)):
        raise ValueError("Metadata not supported.")

    validated_meta = PluginMetadata.model_validate(meta, strict=True)

    def decorator(cls: P) -> P:
        if not issubclass(cls, PluginContract):
            raise TypeError("Plugin type not supported.")

        Registry().register(cls, validated_meta)
        return cls

    return decorator


def list_plugins(modules: List[str], discover_disabled: bool = False, **kwargs) -> List[Type[PluginContract]]:
    """List all available plugins from specified modules."""
    registry = Registry().discover(
        *modules, discover_disabled=discover_disabled, add_modules=kwargs.get("add_modules", False)
    )
    return list(registry.plugins)


def load_plugin(plugin_name: str, modules: List[str], **kwargs) -> Type[PluginContract]:
    """Discover and load a plugin class from specified modules by name.

    This function performs dynamic plugin discovery and retrieval, scanning the specified
    modules for plugin classes that match the given plugin name. It uses the Registry
    singleton to discover plugins, then retrieves the matching plugin class using
    configurable matching strategies (exact match, case-insensitive, or fuzzy matching).

    The function includes built-in retry logic to handle intermittent registration issues
    where plugins may not be immediately available in the registry after module discovery.
    It logs detailed information during discovery and retrieval operations, and provides
    comprehensive error handling with appropriate exception types.

    Args:
        plugin_name: The name of the plugin to load, used to match against plugin metadata
                     names in the registry. Matching behavior is controlled by kwargs.
        modules: List of module names (as strings) to scan for plugin discovery. Module
                 names can be comma-separated strings, which will be automatically split
                 and processed. The function also automatically includes the base package
                 modules in the discovery process.
        **kwargs: Additional keyword arguments for customizing plugin retrieval behavior:
            - max_retries: Maximum number of retry attempts when plugin loading fails
                           due to validation errors. Defaults to 1 if not specified.
            - case_sensitive: Whether plugin name matching should be case-sensitive.
                             Defaults to True.
            - strict_exact: Whether to require exact matching of plugin names, disabling
                           fuzzy matching. Defaults to False.
            - fuzzy_threshold: Similarity threshold (0-100) for fuzzy matching when
                              strict_exact is False. Defaults to 95.

    Returns:
        The plugin class (a subclass of PluginContract) that matches the specified
        plugin_name according to the matching criteria. The returned class can be
        instantiated to create plugin instances.

    Raises:
        ValueError: If the specified plugin name cannot be found in the registry after
                    discovery, or if the found plugin is not a valid class object.
        TypeError: If the found plugin class is not a subclass of PluginContract,
                   indicating an invalid plugin implementation.
        RuntimeError: If plugin loading fails after exhausting all retry attempts due
                     to metadata validation errors, or if an unexpected error occurs
                     during the loading process. The original exception is preserved
                     as the cause of the RuntimeError.

    Note:
        This function uses recursive retry logic internally, tracking retry attempts
        via the _retries parameter (which should not be set manually). The function
        automatically handles module name parsing, splitting comma-separated module
        names, and includes the base package modules in discovery automatically.

        There is a known issue (documented as TODO) where plugins may intermittently
        not be registered in the registry immediately after discovery, which is why
        retry logic is implemented. The function enables debug mode during discovery
        to aid in troubleshooting registration issues.
    """
    retries = int(float(kwargs.pop("_retries", None) or 0))
    max_retries = int(float(kwargs.get("max_retries") or 1))
    try:
        with contextlib.suppress(AttributeError):
            modules = [mod.strip() for mods in modules for mod in mods.strip().split(",")]

        logger.info("Discovering plugin from modules: %s", modules)
        # TODO: Fix issue where plugin is intermitently not registered in the registry and not loaded.
        registry = Registry().discover(*modules)
        logger.debug("Discovered plugins: %s", registry.plugins)
        logger.debug("Getting plugin '%s' from registry", plugin_name)
        plugin = registry.get(
            label=plugin_name,
            case_sensitive=kwargs.get("case_sensitive", True),
            strict_exact=kwargs.get("strict_exact", False),
            fuzz_threshold=kwargs.get("fuzzy_threshold", 95),
        )
        if not plugin or not inspect.isclass(plugin):
            raise ValueError(f"The specified plugin '{plugin_name}' could not be found.")

        if not issubclass(plugin, PluginContract):
            raise TypeError(
                f"The specified plugin '{plugin_name}({plugin.__class__.__name__})' is not a valid plugin "
                "                                                implementation."
            )

        return plugin
    except (ValueError, TypeError) as err:
        retries += 1
        if retries < max_retries:
            logger.warning(
                "Error loading plugin due to meta validation: %s, retrying... (%d/%d)", err, retries, max_retries
            )
            return load_plugin(plugin_name, modules, _retries=retries, **kwargs)

        if logger.isEnabledFor(logging.DEBUG):
            logger.exception(
                "Error loading plugin due to meta validation: %s, max retries reached (%d/%d)",
                err,
                retries,
                max_retries,
            )
        else:
            logger.error(
                "Error loading plugin due to meta validation: %s, max retries reached (%d/%d)",
                err,
                retries,
                max_retries,
            )

        raise RuntimeError(f"Error loading plugin due to meta validation: {err}") from err
    except Exception as err:
        if logger.isEnabledFor(logging.DEBUG):
            logger.exception("Error loading plugin due to unexpected error: %s", err)
        else:
            logger.error("Error loading plugin due to unexpected error: %s", err)

        raise RuntimeError(f"Error loading plugin due to unexpected error: {err}") from err
