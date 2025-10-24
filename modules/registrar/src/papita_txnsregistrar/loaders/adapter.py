"""
Loader Adapter Module.

This module provides a registry and discovery mechanism for loader classes in the
Papita transaction system. It defines the LoaderFlag class which serves as a central
registry for loader implementations, allowing them to be tagged, discovered, and
retrieved at runtime.

The module enables a plugin-like architecture for data loaders by:
1. Registering loader implementations with associated tags
2. Looking up appropriate loaders by tag or class type
3. Automatically discovering loader implementations in specified modules
"""

import functools
import inspect
from typing import Dict, Self, Tuple, Type

from papita_txnsmodel.utils.classutils import ClassDiscovery
from papita_txnsregistrar import LIB_NAME

from .abstract import AbstractLoader


class LoaderFlag:
    """
    Registry for loader implementations with tag-based lookup functionality.

    This class provides mechanisms to register, discover, and retrieve loader
    implementations. It acts as a central registry where loader classes can be
    registered with associated tags, allowing the application to dynamically select
    appropriate loaders based on context or configuration.

    The class uses class methods exclusively and maintains a class-level dictionary
    of registered loaders and their associated tags.

    Attributes:
        loaders: Dictionary mapping loader classes to their associated tags.
    """

    loaders: Dict[Type[AbstractLoader], Tuple[str, ...]]

    @classmethod
    def acknowledge(cls, *tags):
        """
        Register a loader class with associated tags.

        This is a decorator method that registers a loader class in the registry
        with associated tags for later lookup. It validates that the class being
        registered is a subclass of AbstractLoader.

        Args:
            *tags: Variable number of string tags to associate with the loader class.

        Returns:
            A decorator function that registers the decorated class.

        Raises:
            TypeError: If the decorated class is not a subclass of AbstractLoader.

        Example:
            ```python
            @LoaderFlag.acknowledge("csv", "text")
            class CSVLoader(AbstractLoader):
                # Implementation...
            ```
        """

        def decorate(cls, cls_: Type[AbstractLoader]):
            @functools.wraps
            def _aux(*args, **kwargs) -> AbstractLoader:
                return cls_(*args, **kwargs)

            if not issubclass(cls_, AbstractLoader):
                raise TypeError(f"Expected AbstractLoader, got {cls_}")

            loaders = getattr(cls, "loaders", None) or {}
            loaders.update({cls_: tags})
            cls.loaders = loaders
            return _aux

        return decorate

    @classmethod
    def get(cls, tag: str | Type[AbstractLoader]) -> Type[AbstractLoader] | None:
        """
        Retrieve a loader class by tag or type.

        This method looks up and returns a registered loader class either by:
        1. Direct class comparison (if tag is a class)
        2. Tag lookup (if tag is a string)

        Args:
            tag: Either a string tag to look up, or a loader class to match.

        Returns:
            The matching loader class if found, None otherwise.

        Example:
            ```python
            # Get by tag
            csv_loader_class = LoaderFlag.get("csv")

            # Get by class
            loader_class = LoaderFlag.get(CSVFileLoader)
            ```
        """
        loaders = getattr(cls, "loaders", None) or {}
        for cls_, tags in loaders:
            if inspect.isclass(tag):
                if issubclass(tag, cls_):
                    return cls_

            if isinstance(tag, str) and tag in tags:
                return cls_

        return None

    @classmethod
    def scout(cls, *modules) -> Type[Self]:
        """
        Discover loader implementations in the specified modules.

        This method searches the provided modules and the library's own namespace
        for classes that inherit from AbstractLoader. Found loader classes are
        automatically added to the registry.

        Args:
            *modules: Variable number of module names to scan for loader implementations.

        Returns:
            The LoaderFlag class itself, allowing for method chaining.

        Example:
            ```python
            # Discover loaders in custom modules
            LoaderFlag.scout("my_app.loaders", "plugins.loaders")
            ```
        """
        for mod_ in set(modules) | {LIB_NAME}:
            ClassDiscovery.get_children(mod_, Type[AbstractLoader], debug=True)

        return cls
