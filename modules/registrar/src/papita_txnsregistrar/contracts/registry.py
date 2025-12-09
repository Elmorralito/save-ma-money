# type: ignore
"""
Plugin registry system for the transaction tracker.

This module provides a singleton registry for managing plugin contracts in the
transaction tracker system. It handles plugin discovery, registration, and
retrieval, with support for fuzzy matching when looking up plugins by name or tags.
"""

from types import ModuleType
from typing import Sequence, Type

from rapidfuzz import fuzz, process

from papita_txnsmodel.utils.classutils import ClassDiscovery, MetaSingleton
from papita_txnsregistrar import LIB_NAME

from .meta import PluginMetadata
from .plugin import PluginContract


class Registry(metaclass=MetaSingleton):
    """
    A singleton registry for managing plugin contracts.

    This class maintains a collection of plugin classes that extend PluginContract.
    It provides methods to discover plugins from specified modules, register plugins
    with associated metadata, and retrieve plugins by name or tags with optional
    fuzzy matching capabilities.

    Attributes:
        _plugins: A set containing plugin classes that extend PluginContract.
    """

    _plugins: set[Type[PluginContract]]

    @property
    def plugins(self) -> set[Type[PluginContract]]:
        """
        Get the registered plugin classes.
        Returns:
            A set of plugin classes that extend PluginContract.

        Raises:
            RuntimeError: If no plugins have been discovered or registered.
        """
        plugins = getattr(self, "_plugins", None)
        if not plugins:
            raise RuntimeError("No plugins have been found.")

        return plugins

    def discover(self, *modules: Sequence[str | ModuleType], debug: bool = False) -> "Registry":
        """
        Discover plugin classes from specified modules.

        Scans the provided modules to find classes that extend PluginContract,
        and adds them to the registry. Also includes the base package of this module.

        Args:
            *modules: Sequence of module names (strings) or module objects to scan.
            debug: Whether to enable debug mode during discovery. Defaults to False.

        Returns:
            The Registry instance for method chaining.
        """
        modules_ = set(modules) | {LIB_NAME} | {f"{LIB_NAME}_plugins"}
        self._plugins = getattr(self, "_plugins", None) or set()
        for module_ in modules_:
            if not isinstance(module_, (ModuleType, str)):
                continue

            self._plugins |= {
                class_
                for class_ in ClassDiscovery.get_children(module_, PluginContract, debug=debug)
                if class_.__class__ != PluginContract and getattr(class_, "__name__", None)
            }

        return self

    def register(self, class_: Type[PluginContract], meta: PluginMetadata) -> "Registry":
        """
        Register a plugin class with metadata.

        Args:
            class_: The plugin class to register, must extend PluginContract.
            meta: Metadata for the plugin, must be a PluginMetadata instance.

        Returns:
            The Registry instance for method chaining.

        Raises:
            TypeError: If the class is not a subclass of PluginContract or
                        if the metadata is not an instance of PluginMetadata.
        """
        if not issubclass(class_, PluginContract):
            raise TypeError("Plugin not compatible.")

        if not isinstance(meta, PluginMetadata):
            raise TypeError("Metadata not compatible.")

        class_.__meta__ = meta
        self._plugins |= {class_}
        return self

    def get(
        self, label: str, case_sensitive: bool = True, strict_exact: bool = False, fuzz_threshold: int = 90
    ) -> Type[PluginContract] | None:
        """
        Get a plugin by name or tag.

        Searches for a plugin that matches the provided label by name or tag.
        Supports fuzzy matching for more flexible lookups.

        Args:
            label: The name or tag to search for.
            case_sensitive: Whether the search should be case-sensitive. Defaults to True.
            strict_exact: If True, only exact matches are returned. Defaults to False.
            fuzz_threshold: Minimum fuzzy matching score (0-100) to consider a match.
                            Defaults to 90.

        Returns:
            The matching plugin class, or None if no match is found.
        """
        for plugin in self.plugins:
            if not plugin.meta().enabled:
                continue

            name = plugin.meta().name
            tags = plugin.meta().feature_tags
            if not case_sensitive:
                label = label.lower()
                name = name.lower()
                tags = [str.lower(tag) for tag in tags]

            if strict_exact:
                if label == name or label in tags:
                    return plugin
            else:
                matches = [
                    match_
                    for match_, score, _ in (process.extract(label, tags, limit=1) or [])
                    if score >= fuzz_threshold
                ]
                if fuzz.ratio(name, label) >= fuzz_threshold or matches:
                    return plugin

        return None
