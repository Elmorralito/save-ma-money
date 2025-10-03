"""Unit tests for the classutils module.

This module tests the following components:
- MetaSingleton: Singleton pattern implementation through metaclass
- FallbackAction: Strategies for handling validation failures
- ClassSelector: Utilities for working with classes and modules
"""
import importlib
import inspect
import logging
import pkgutil
import sys
from enum import Enum
from types import ModuleType
from unittest import mock

import pytest

from papita_txnsmodel.utils.classutils import (
    ClassSelector,
    FallbackAction,
    MetaSingleton
)


# --- MetaSingleton Tests ---

def test_meta_singleton_basic():
    """Test that classes with MetaSingleton create only one instance."""
    class TestSingleton(metaclass=MetaSingleton):
        def __init__(self, value=None):
            self.value = value

    # Create two instances
    instance1 = TestSingleton(1)
    instance2 = TestSingleton(2)

    # Verify they're the same object
    assert instance1 is instance2
    # Verify only first initialization applies
    assert instance1.value == 1


def test_meta_singleton_multiple_classes():
    """Test that different classes with MetaSingleton have separate instances."""
    class SingletonA(metaclass=MetaSingleton):
        pass

    class SingletonB(metaclass=MetaSingleton):
        pass

    instance_a = SingletonA()
    instance_b = SingletonB()

    assert SingletonA() is instance_a
    assert SingletonB() is instance_b
    assert instance_a is not instance_b


def test_meta_singleton_inheritance():
    """Test that MetaSingleton works correctly with class inheritance."""
    class BaseSingleton(metaclass=MetaSingleton):
        def __init__(self):
            self.name = "base"

    class DerivedSingleton(BaseSingleton):
        def __init__(self):
            super().__init__()
            self.name = "derived"

    base = BaseSingleton()
    derived = DerivedSingleton()

    assert BaseSingleton() is base
    assert DerivedSingleton() is derived
    assert base is not derived
    assert base.name == "base"
    assert derived.name == "derived"


# --- FallbackAction Tests ---

def test_fallback_action_enum_values():
    """Test that FallbackAction enum has the expected values."""
    assert FallbackAction.LOG.value == "LOG"
    assert FallbackAction.RAISE.value == "RAISE"
    assert FallbackAction.IGNORE.value == "IGNORE"


def test_fallback_action_get_logger_custom():
    """Test that get_logger returns the provided logger."""
    custom_logger = logging.getLogger("custom")
    assert FallbackAction.LOG.get_logger(logger=custom_logger) is custom_logger


def test_fallback_action_get_logger_default():
    """Test that get_logger returns the default logger when none is provided."""
    assert isinstance(FallbackAction.LOG.get_logger(), logging.Logger)


def test_fallback_action_get_logger_invalid():
    """Test that get_logger handles non-logger inputs correctly."""
    assert isinstance(FallbackAction.LOG.get_logger(logger="not_a_logger"), logging.Logger)


@mock.patch("logging.Logger.debug")
def test_fallback_action_handle_ignore(mock_debug):
    """Test that handle_ignore logs at debug level."""
    FallbackAction.IGNORE.handle_ignore("Test message")
    mock_debug.assert_called_once()
    assert "Test message" in mock_debug.call_args[0][1]


@mock.patch("logging.Logger.warning")
def test_fallback_action_handle_log_string(mock_warning):
    """Test that handle_log logs string messages as warnings."""
    logger = logging.getLogger("test")
    FallbackAction.LOG.handle_log("Test warning", logger)
    mock_warning.assert_called_once_with("Test warning")


@mock.patch("logging.Logger.exception")
def test_fallback_action_handle_log_exception(mock_exception):
    """Test that handle_log logs exceptions appropriately."""
    logger = logging.getLogger("test")
    exception = ValueError("Test exception")
    FallbackAction.LOG.handle_log(exception, logger)
    mock_exception.assert_called_once_with(exception, stack_info=True)


def test_fallback_action_handle_raise_string():
    """Test that handle_raise raises ValueError with string messages."""
    with pytest.raises(ValueError, match="Test error"):
        FallbackAction.RAISE.handle_raise("Test error")


def test_fallback_action_handle_raise_exception():
    """Test that handle_raise raises the provided exception."""
    exception = RuntimeError("Custom exception")
    with pytest.raises(RuntimeError) as excinfo:
        FallbackAction.RAISE.handle_raise(exception)
    assert excinfo.value is exception


@mock.patch.object(FallbackAction.LOG, "handle_log")
def test_fallback_action_handle_dispatch_log(mock_handle_log):
    """Test that handle method dispatches to handle_log for LOG action."""
    message = "Test log message"
    logger = logging.getLogger("test")
    FallbackAction.LOG.handle(message, logger=logger)
    mock_handle_log.assert_called_once_with(message, logger=logger)


@mock.patch.object(FallbackAction.RAISE, "handle_raise")
def test_fallback_action_handle_dispatch_raise(mock_handle_raise):
    """Test that handle method dispatches to handle_raise for RAISE action."""
    message = "Test raise message"
    FallbackAction.RAISE.handle(message)
    mock_handle_raise.assert_called_once_with(message)


@mock.patch.object(FallbackAction.IGNORE, "handle_ignore")
def test_fallback_action_handle_dispatch_ignore(mock_handle_ignore):
    """Test that handle method dispatches to handle_ignore for IGNORE action."""
    message = "Test ignore message"
    FallbackAction.IGNORE.handle(message)
    mock_handle_ignore.assert_called_once_with(message)


# --- ClassSelector Tests ---

def test_is_builtin_with_builtin_functions():
    """Test is_builtin identifies built-in functions correctly."""
    assert ClassSelector.is_builtin(len)
    assert ClassSelector.is_builtin(print)
    assert ClassSelector.is_builtin(str)


def test_is_builtin_with_custom_objects():
    """Test is_builtin correctly identifies non-built-in objects."""
    class CustomClass:
        pass

    def custom_function():
        pass

    assert not ClassSelector.is_builtin(CustomClass)
    assert not ClassSelector.is_builtin(CustomClass())
    assert not ClassSelector.is_builtin(custom_function)


def test_is_builtin_with_builtin_module_name():
    """Test is_builtin with objects from built-in modules."""
    # Mock an object with __module__ set to a built-in
    mock_obj = mock.MagicMock()
    mock_obj.__module__ = "builtins"
    mock_obj.__name__ = "mock_builtin"
    mock_obj.__class__.__name__ = "MockBuiltin"

    assert ClassSelector.is_builtin(mock_obj)


@pytest.fixture
def test_module():
    """Create a test module with known classes for testing."""
    module = ModuleType("test_module")

    class TestClass:
        pass

    class AnotherClass:
        pass

    module.TestClass = TestClass
    module.AnotherClass = AnotherClass
    module.not_a_class = "string"

    return module


def test_get_classes_with_module_object(test_module):
    """Test get_classes retrieves classes from a module object."""
    classes = ClassSelector.get_classes(test_module)

    assert len(classes) == 2
    assert "TestClass" in classes
    assert "AnotherClass" in classes
    assert inspect.isclass(classes["TestClass"])
    assert inspect.isclass(classes["AnotherClass"])


def test_get_classes_with_invalid_input():
    """Test get_classes raises ValueError with invalid input."""
    with pytest.raises(ValueError, match="The provided object is not supported"):
        ClassSelector.get_classes(123)


@mock.patch("pkgutil.walk_packages")
def test_get_classes_with_package(mock_walk_packages, test_module):
    """Test get_classes when walking through a package."""
    # Setup mock module info
    mock_module_info = mock.Mock()
    mock_module_info.name = "test_module"
    mock_module_info.ispkg = False

    mock_walk_packages.return_value = [mock_module_info]

    # Setup module path attribute required for pkgutil.walk_packages
    test_module.__path__ = ["dummy_path"]

    # Mock importlib.import_module to return our test module
    with mock.patch("importlib.import_module", return_value=test_module):
        classes = ClassSelector.get_classes(test_module)

    assert len(classes) == 2
    assert "TestClass" in classes
    assert "AnotherClass" in classes


@mock.patch("pkgutil.walk_packages")
def test_get_classes_handles_import_errors(mock_walk_packages):
    """Test get_classes gracefully handles import errors."""
    # Setup mock module that raises ImportError
    mock_module = mock.Mock()
    mock_module.__path__ = ["dummy_path"]
    mock_module.__name__ = "error_module"

    # Setup mock module info
    mock_module_info = mock.Mock()
    mock_module_info.name = "error_submodule"
    mock_module_info.ispkg = False

    mock_walk_packages.return_value = [mock_module_info]

    classes = {}
    # Mock importlib.import_module to raise ImportError
    with mock.patch("importlib.import_module", side_effect=ImportError("Test import error")):
        # Should not raise exception when debug=False
        with pytest.raises(ValueError):
            classes = ClassSelector.get_classes(mock_module, debug=False)

        assert isinstance(classes, dict)
        assert len(classes) == 0


@pytest.fixture
def class_hierarchy():
    """Create a class hierarchy for testing get_children."""
    class Base:
        pass

    class Child1(Base):
        pass

    class Child2(Base):
        pass

    class GrandChild(Child1):
        pass

    class Unrelated:
        pass

    # Create a module with these classes
    module = ModuleType("test_hierarchy")
    module.Base = Base
    module.Child1 = Child1
    module.Child2 = Child2
    module.GrandChild = GrandChild
    module.Unrelated = Unrelated

    return module


def test_get_children(class_hierarchy):
    """Test get_children returns subclasses of specified types."""
    # Get all children of Base
    with mock.patch("papita_txnsmodel.utils.classutils.ClassSelector.get_module", return_value=class_hierarchy):
        with mock.patch("papita_txnsmodel.utils.classutils.ClassSelector.get_classes",
                       return_value={name: getattr(class_hierarchy, name) for name in dir(class_hierarchy)
                                    if inspect.isclass(getattr(class_hierarchy, name))}):
            children = ClassSelector.get_children(class_hierarchy, class_hierarchy.Base)

    # Should find Child1, Child2, GrandChild but not Base or Unrelated
    assert len(children) == 3
    assert class_hierarchy.Child1 in children
    assert class_hierarchy.Child2 in children
    assert class_hierarchy.GrandChild in children
    assert class_hierarchy.Base not in children
    assert class_hierarchy.Unrelated not in children


def test_get_objects_with_filter():
    """Test get_objects applies the filter function correctly."""
    module = ModuleType("test_module")

    def func1():
        pass

    def func2():
        pass

    class TestClass:
        pass

    module.func1 = func1
    module.func2 = func2
    module.TestClass = TestClass

    # Mock dependencies
    with mock.patch("papita_txnsmodel.utils.classutils.ClassSelector.get_module", return_value=module):
        with mock.patch("papita_txnsmodel.utils.classutils.ClassSelector.get_classes",
                       return_value={"TestClass": TestClass}):
            with mock.patch("inspect.getmembers", return_value=[("func1", func1), ("func2", func2)]):
                # Get only functions
                objects = ClassSelector.get_objects(module, obj_filter=inspect.isfunction)

    assert len(objects) == 2
    assert func1 in objects
    assert func2 in objects
    assert TestClass not in objects


def test_load_class_success(test_module):
    """Test load_class finds a class by name."""
    cls = ClassSelector.load_class("TestClass", test_module)
    assert cls is test_module.TestClass


def test_load_class_not_found(test_module):
    """Test load_class returns None when class not found."""
    cls = ClassSelector.load_class("NonExistentClass", test_module)
    assert cls is None


def test_get_module_from_string():
    """Test get_module can get a module from its name."""
    with mock.patch("importlib.import_module", return_value="mocked_module") as mock_import:
        module = ClassSelector.get_module("module.path")
        mock_import.assert_called_once_with("module.path")
        assert module == "mocked_module"


def test_get_module_from_class():
    """Test get_module can get a module from a class."""
    class TestClass:
        pass

    # Mock the decompose_class and importlib functions
    with mock.patch("papita_txnsmodel.utils.classutils.ClassSelector.decompose_class",
                   return_value=("test.module", "TestClass")):
        with mock.patch("importlib.import_module", return_value="mocked_module") as mock_import:
            module = ClassSelector.get_module(TestClass)
            mock_import.assert_called_once_with("test.module")
            assert module == "mocked_module"


def test_get_module_from_module():
    """Test get_module returns the module if provided a module."""
    module = ModuleType("test_module")
    result = ClassSelector.get_module(module)
    assert result is module


def test_get_module_handles_error():
    """Test get_module handles import errors gracefully."""
    with mock.patch("importlib.import_module", side_effect=OSError("Test error")):
        result = ClassSelector.get_module("problem.module")
        assert result is None


def test_decompose_class_string():
    """Test decomposing a class name from a string."""
    module_path, class_name = ClassSelector.decompose_class("module.submodule.ClassName")
    assert module_path == "module.submodule"
    assert class_name == "ClassName"


def test_decompose_class_single_name():
    """Test decomposing a class name with no module path."""
    module_path, class_name = ClassSelector.decompose_class("ClassName")
    assert module_path is None
    assert class_name == "ClassName"


def test_decompose_class_from_class_object():
    """Test decomposing a class name from a class object."""
    class TestClass:
        pass

    with mock.patch("inspect.getmodule", return_value=ModuleType("test.module")):
        module_path, class_name = ClassSelector.decompose_class(TestClass)
        assert module_path == "test.module"
        assert class_name == "TestClass"


def test_get_canonical_class_name_with_string():
    """Test getting canonical name from a string."""
    with mock.patch("papita_txnsmodel.utils.classutils.ClassSelector.decompose_class",
                   return_value=("module.path", "ClassName")):
        name = ClassSelector.get_canonical_class_name("module.path.ClassName")
        assert name == "module.path.ClassName"


def test_get_canonical_class_name_no_module():
    """Test getting canonical name for a class with no module."""
    with mock.patch("papita_txnsmodel.utils.classutils.ClassSelector.decompose_class",
                   return_value=(None, "ClassName")):
        name = ClassSelector.get_canonical_class_name("ClassName")
        assert name == "ClassName"


def test_select_with_class_object():
    """Test select with an actual class object."""
    class TestClass:
        pass

    result = ClassSelector.select(TestClass)
    assert result is TestClass


def test_select_with_class_name():
    """Test select with a class name string."""
    with mock.patch("papita_txnsmodel.utils.classutils.ClassSelector.decompose_class",
                   return_value=("test.module", "TestClass")):
        with mock.patch("papita_txnsmodel.utils.classutils.ClassSelector.get_module",
                       return_value="module_obj"):
            with mock.patch("papita_txnsmodel.utils.classutils.ClassSelector.load_class",
                           return_value="class_obj"):
                result = ClassSelector.select("test.module.TestClass")
                assert result == "class_obj"


def test_select_with_default_module():
    """Test select using the default module when class not found in specified module."""
    with mock.patch("papita_txnsmodel.utils.classutils.ClassSelector.decompose_class",
                   return_value=("test.module", "TestClass")):
        with mock.patch("papita_txnsmodel.utils.classutils.ClassSelector.get_module",
                       return_value=None):
            with mock.patch("papita_txnsmodel.utils.classutils.ClassSelector.get_classes",
                           return_value={"TestClass": "class_obj"}):
                result = ClassSelector.select("TestClass", default_module="default.module")
                assert result == "class_obj"


def test_select_with_invalid_type():
    """Test select raises TypeError for non-class, non-string inputs."""
    with pytest.raises(TypeError, match="Class objects or class names are only allowed"):
        ClassSelector.select(123)


def test_select_with_class_type_validation():
    """Test select performs class type validation correctly."""
    class BaseClass:
        pass

    class ValidClass(BaseClass):
        pass

    class InvalidClass:
        pass

    # Should succeed - ValidClass is a subclass of BaseClass
    result = ClassSelector.select(ValidClass, class_type=BaseClass)
    assert result is ValidClass

    # Should fail - InvalidClass is not a subclass of BaseClass
    with pytest.raises(TypeError, match="is not type"):
        ClassSelector.select(InvalidClass, class_type=BaseClass)


def test_select_with_path():
    """Test select can modify sys.path."""
    with mock.patch("sys.path") as mock_path:
        mock_path.append = mock.Mock()

        with mock.patch("papita_txnsmodel.utils.classutils.ClassSelector.decompose_class",
                       return_value=("test.module", "TestClass")):
            with mock.patch("papita_txnsmodel.utils.classutils.ClassSelector.get_module",
                           return_value="module_obj"):
                with mock.patch("papita_txnsmodel.utils.classutils.ClassSelector.load_class",
                               return_value="class_obj"):
                    ClassSelector.select("test.module.TestClass", path="/custom/path")
                    mock_path.append.assert_called_once_with("/custom/path")


def test_select_no_class_no_default():
    """Test select raises ValueError when class not found and no default module provided."""
    with mock.patch("papita_txnsmodel.utils.classutils.ClassSelector.decompose_class",
                   return_value=("test.module", "TestClass")):
        with mock.patch("papita_txnsmodel.utils.classutils.ClassSelector.get_module",
                       return_value=None):
            with pytest.raises(ValueError, match="Cannot find the class"):
                ClassSelector.select("test.module.TestClass")
