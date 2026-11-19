"""Utility module for class manipulation, introspection, and management.

This module provides utilities for working with Python classes in a dynamic way,
including class discovery, loading, and introspection. It features a metaclass for
implementing the Singleton pattern, an enum for handling validation failures, and
a comprehensive class selection toolkit.

The module provides the following key components:
    - MetaSingleton: A metaclass for implementing the Singleton design pattern
    - FallbackAction: An enum defining strategies for handling validation failures
    - ClassDiscovery: Utilities for discovering, loading, and filtering classes
"""

import importlib
import inspect
import logging
import pkgutil
import sys
import traceback
import warnings
from types import ModuleType
from typing import Any, Callable, Dict, List, Tuple, Type, Union

_UTILS_LOGGER = logging.getLogger(__name__)


class MetaSingleton(type):
    """
    Static singleton metaclass.

    Ensures that a class has only one instance and provides a global point of access to it.
    """

    _instances: dict[type, type] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance

        return cls._instances[cls]


class ClassDiscovery:
    """
    Class discovery fetcher.

    This class provides methods to select and load classes from modules
    and packages. It includes utilities to check if an object is a
    built-in, retrieve classes from a module, get child classes of a
    certain type, and more.
    """

    # pylint: disable=C0301
    builtin_mods = list(set(sys.builtin_module_names).union(set(__builtins__)).union(["builtins"]))  # type: ignore[arg-type] # noqa

    @classmethod
    def is_builtin(cls, obj):
        """
        Check if an object is a built-in.

        Args:
            obj: The object to check.

        Returns:
            bool: True if the object is a built-in, False otherwise.
        """
        with warnings.catch_warnings(action="ignore"):
            if inspect.isbuiltin(obj) or obj in cls.builtin_mods:
                return True

        obj_mod = getattr(obj, "__module__", "")
        obj_name = str(getattr(obj, "__name__", ""))
        obj_class = obj.__name__ if inspect.isclass(obj) else obj.__class__.__name__
        if not obj_mod:
            return False

        for bltn in cls.builtin_mods:
            if obj_mod.find(bltn) > -1:
                return True

            if obj_name.find(bltn) > -1:
                return True

            if obj_class.find(bltn) > -1:
                return True

        return False

    @staticmethod
    def get_classes(mod: Union[str, ModuleType], debug: bool = False) -> Dict[str, object]:
        """
        Retrieve all the classes from a package/module.

        Args:
            mod: The module or package to retrieve classes from.
            debug: Whether to enable debug logging.

        Returns:
            dict: A dictionary of class names and class objects.
        """

        def _(mod_):
            return dict([(name, obj) for name, obj in inspect.getmembers(mod_, inspect.isclass)])

        if isinstance(mod, (str, ModuleType)):
            mod = ClassDiscovery.get_module(mod)
        else:
            raise ValueError(f"The provided object is not supported {type(mod)}: {mod}.")

        try:
            mods = pkgutil.walk_packages(mod.__path__, mod.__name__ + ".", onerror=lambda x: None)
        except (ImportError, AttributeError):
            return _(mod)

        classes_ = {}
        for mod_info in mods:
            if not mod_info:
                continue

            try:
                if mod_info.ispkg:
                    classes_.update(ClassDiscovery.get_classes(mod_info.name, debug=debug))

                classes_.update(_(importlib.import_module(mod_info.name)))
            except (ImportError, ValueError, SystemExit, TypeError, OSError, SystemError) as ex:
                if not debug:
                    continue

                message = "Could not fetch module << %s >> for classes, due to the following error:\n%s"
                try:
                    _UTILS_LOGGER.debug(message, mod_info, traceback.format_exc())
                except Exception:
                    _UTILS_LOGGER.debug(message, mod_info, ex)

        return dict(classes_)

    @staticmethod
    def get_children(module: Union[str, ModuleType], *class_types: Type, debug: bool = False) -> List[Type]:
        """
        Get the classes that belong to certain type or metaclass.

        Args:
            module: The module or package to retrieve child classes from.
            class_types: The types or metaclasses to filter by.

        Returns:
            list: A list of classes that belong to the specified types or metaclasses.
        """
        classes = []
        mod = ClassDiscovery.get_module(module)
        for clazz in ClassDiscovery.get_classes(mod=mod, debug=debug).values():
            try:
                if issubclass(clazz, class_types):  # type: ignore[arg-type]
                    if clazz in class_types:
                        continue

                    classes.append(clazz)
            except TypeError:
                if issubclass(clazz.__class__, class_types):
                    if clazz in class_types:
                        continue

                    classes.append(clazz)

        return [cls_ for cls_ in classes if inspect.isclass(cls_)]

    @classmethod
    def get_objects(
        cls,
        mod: Union[str, ModuleType],
        obj_filter: Callable[[Any], bool] = lambda x: x,
        debug: bool = False,
    ) -> List[Type]:
        """
        Get any type of objects recursively within the provided module.

        Args:
            mod: The module or package to retrieve objects from.
            obj_filter: A callable to filter objects.
            debug: Whether to enable debug logging.

        Returns:
            list: A list of objects that pass the filter.
        """
        mod = ClassDiscovery.get_module(mod)
        output: set[Type] = set()
        mod_names = set(
            map(
                lambda cls: cls.__module__,
                ClassDiscovery.get_classes(mod, debug=debug).values(),
            )
        ).difference(cls.builtin_mods)
        for name in mod_names:
            try:
                objs = inspect.getmembers(
                    ClassDiscovery.get_module(name),
                    predicate=lambda o: not cls.is_builtin(o) and obj_filter(o),
                )
                output.update(map(lambda x: x[1], objs))
            except (ImportError, ValueError, SystemExit, TypeError) as ex:
                if not debug:
                    continue

                message = "Could not fetch module << %s >> for objects, due to the following error:\n%s"
                try:
                    _UTILS_LOGGER.debug(message, name, traceback.format_exc())
                except Exception:
                    _UTILS_LOGGER.debug(message, name, ex)

        return list(output)

    @staticmethod
    def load_class(class_name: str, module: ModuleType):
        """
        Load a class by giving its canonical name.

        Args:
            class_name: The name of the class to load.
            module: The module to load the class from.

        Returns:
            type: The loaded class, or None if not found.
        """
        for attrib in dir(module):
            obj = getattr(module, attrib)
            if inspect.isclass(obj) and obj.__name__ == class_name:
                return obj

        return None

    @staticmethod
    def get_module(obj: Union[str, Type, ModuleType, Any]):
        """
        Get the module object.

        Args:
            obj: The module path, class, module, or any object to get the module from.

        Returns:
            module: The module object.
        """
        if isinstance(obj, str):
            module_path = obj
        elif inspect.isclass(obj):
            module_path, _ = ClassDiscovery.decompose_class(obj)  # type: ignore
        elif isinstance(obj, ModuleType) or not obj:
            return obj
        else:
            module_path, _ = ClassDiscovery.decompose_class(obj.__class__)  # type: ignore

        try:
            return importlib.import_module(module_path)
        except (OSError, ModuleNotFoundError):
            return None

    @staticmethod
    def decompose_class(class_name: Union[str, Type]) -> Tuple[str | None, str]:
        """
        Decompose the class name into module and name.

        Args:
            class_name: The class name or class object to decompose.

        Returns:
            tuple: A tuple containing the module path and class name.
        """
        if inspect.isclass(class_name):
            module_name_ = getattr(inspect.getmodule(class_name), "__name__", getattr(class_name, "__module__", ""))
            class_name = f"{module_name_}.{class_name.__name__}" if module_name_ else class_name.__name__

        decomposed = class_name.split(".")
        if len(decomposed) == 1:
            return None, decomposed[0]

        return ".".join(decomposed[:-1]), decomposed[-1]

    @staticmethod
    def get_canonical_class_name(class_name: Union[str, Type]) -> str:
        """
        Get the canonical class name.

        Args:
            class_name: The class name or class object.

        Returns:
            str: The canonical class name.
        """
        decomposed = ClassDiscovery.decompose_class(class_name)
        return ".".join(filter(None, decomposed))

    @staticmethod
    def select(
        class_name: Union[str, Type],
        class_type: Type | None = None,
        default_module: Union[str, ModuleType] | None = None,
        path: str | None = None,
        debug: bool = False,
    ) -> Type | None:
        """
        Select a class from a given name after validating its type if provided.

        Args:
            class_name: The name or type of the class to select.
            class_type: The type to validate the class against.
            default_module: The default module to search in if the class is not found.
            path: The path to append to sys.path for module search.

        Returns:
            type: The selected class, or None if not found or validation fails.

        Raises:
            ValueError: If the class is not found and no default module is provided.
            TypeError: If the class_name is not a class or string, or if the class does not match the class_type.
        """
        if path:
            sys.path.append(path)

        if isinstance(class_name, str):
            module_path, name = ClassDiscovery.decompose_class(class_name)
            module = ClassDiscovery.get_module(module_path)
            if module:
                class_object = ClassDiscovery.load_class(name, module)
            elif default_module:
                class_object = ClassDiscovery.get_classes(default_module, debug=debug)[name]
            else:
                raise ValueError("Cannot find the class, provide a default module where to start searching.")
        elif inspect.isclass(class_name):
            class_object = class_name
        else:
            raise TypeError("Class objects or class names are only allowed.")

        if class_type:
            if not issubclass(class_object if inspect.isclass(class_object) else class_object.__class__, class_type):
                raise TypeError(f"Class {class_object} is not type {class_type}")

        return class_object
