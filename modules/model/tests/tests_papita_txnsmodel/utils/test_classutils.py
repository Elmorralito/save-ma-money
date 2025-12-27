"""Unit tests for the classutils module in the Papita Transactions system.

This test suite validates class manipulation utilities including singleton metaclass,
fallback action handlers, and class discovery functionality. All tests use mocking
to ensure isolation and avoid external dependencies.
"""

import logging
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from papita_txnsmodel.utils.classutils import ClassDiscovery, MetaSingleton
from papita_txnsmodel.utils.enums import FallbackAction


@pytest.fixture
def mock_logger():
    """Provide a mocked logger for testing logging operations."""
    logger = MagicMock(spec=logging.Logger)
    return logger


@pytest.fixture
def sample_class():
    """Provide a sample class for testing class discovery operations."""

    class TestClass:
        pass

    return TestClass


def test_meta_singleton_creates_single_instance():
    """Test that MetaSingleton ensures only one instance is created per class."""
    # Arrange
    class TestSingleton(metaclass=MetaSingleton):
        def __init__(self, value=0):
            self.value = value

    # Act
    instance1 = TestSingleton(10)
    instance2 = TestSingleton(20)
    instance3 = TestSingleton(30)

    # Assert
    assert instance1 is instance2
    assert instance2 is instance3
    assert instance1.value == 10  # First initialization value is preserved


def test_fallback_action_handle_raise_raises_value_error():
    """Test that FallbackAction.RAISE.handle raises ValueError with string message."""
    # Arrange
    message = "Test error message"

    # Act & Assert
    with pytest.raises(ValueError, match="Test error message"):
        FallbackAction.RAISE.handle(message)


def test_fallback_action_handle_raise_raises_exception_directly():
    """Test that FallbackAction.RAISE.handle raises exception directly when message is Exception."""
    # Arrange
    test_exception = RuntimeError("Direct exception")

    # Act & Assert
    with pytest.raises(RuntimeError, match="Direct exception"):
        FallbackAction.RAISE.handle(test_exception)


@pytest.mark.parametrize(
    "action,expected_log_level",
    [
        (FallbackAction.IGNORE, "debug"),
        (FallbackAction.LOG, "warning"),
    ],
)
def test_fallback_action_handlers_log_appropriately(action, expected_log_level, mock_logger):
    """Test that FallbackAction handlers log messages at appropriate levels."""
    # Arrange
    message = "Test message"

    # Act
    if action == FallbackAction.IGNORE:
        action.handle_ignore(message, logger=mock_logger)
        mock_logger.debug.assert_called_once_with("Ignoring message: %s", message)
    elif action == FallbackAction.LOG:
        action.handle_log(message, mock_logger)
        mock_logger.warning.assert_called_once_with(message)


def test_fallback_action_handle_dispatches_to_correct_handler(mock_logger):
    """Test that FallbackAction.handle dynamically dispatches to the correct handler method."""
    # Arrange
    message = "Test dispatch message"

    # Act
    FallbackAction.IGNORE.handle(message, logger=mock_logger)

    # Assert
    mock_logger.debug.assert_called_once_with("Ignoring message: %s", message)


def test_class_discovery_is_builtin_returns_true_for_builtin_objects():
    """Test that ClassDiscovery.is_builtin returns True for built-in Python objects."""
    # Arrange
    builtin_obj = len  # Built-in function

    # Act
    result = ClassDiscovery.is_builtin(builtin_obj)

    # Assert
    assert result is True


def test_class_discovery_is_builtin_returns_false_for_custom_objects(sample_class):
    """Test that ClassDiscovery.is_builtin returns False for custom class objects."""
    # Arrange
    custom_obj = sample_class()

    # Act
    result = ClassDiscovery.is_builtin(custom_obj)

    # Assert
    assert result is False


def test_class_discovery_decompose_class_splits_fully_qualified_name():
    """Test that ClassDiscovery.decompose_class correctly splits fully qualified class names."""
    # Arrange
    class_name = "papita_txnsmodel.utils.classutils.ClassDiscovery"

    # Act
    module_path, name = ClassDiscovery.decompose_class(class_name)

    # Assert
    assert module_path == "papita_txnsmodel.utils.classutils"
    assert name == "ClassDiscovery"


def test_class_discovery_decompose_class_handles_simple_class_name():
    """Test that ClassDiscovery.decompose_class handles simple class names without module path."""
    # Arrange
    class_name = "SimpleClass"

    # Act
    module_path, name = ClassDiscovery.decompose_class(class_name)

    # Assert
    assert module_path is None
    assert name == "SimpleClass"


@patch("papita_txnsmodel.utils.classutils.importlib.import_module")
@patch("papita_txnsmodel.utils.classutils.ClassDiscovery.load_class")
def test_class_discovery_select_loads_class_from_string_name(mock_load_class, mock_import_module, sample_class):
    """Test that ClassDiscovery.select successfully loads a class from a string class name."""
    # Arrange
    class_name = "test_module.TestClass"
    mock_module = MagicMock(spec=ModuleType)
    mock_import_module.return_value = mock_module
    mock_load_class.return_value = sample_class

    # Act
    result = ClassDiscovery.select(class_name)

    # Assert
    assert result == sample_class
    mock_import_module.assert_called_once_with("test_module")
    mock_load_class.assert_called_once_with("TestClass", mock_module)


def test_class_discovery_select_raises_value_error_when_class_not_found():
    """Test that ClassDiscovery.select raises ValueError when class cannot be found without default module."""
    # Arrange
    class_name = "nonexistent.module.NonExistentClass"

    # Act & Assert
    with pytest.raises(ValueError, match="Cannot find the class, provide a default module where to start searching."):
        ClassDiscovery.select(class_name)


def test_class_discovery_select_raises_type_error_for_invalid_input():
    """Test that ClassDiscovery.select raises TypeError when provided with non-class, non-string input."""
    # Arrange
    invalid_input = 12345

    # Act & Assert
    with pytest.raises(TypeError, match="Class objects or class names are only allowed"):
        ClassDiscovery.select(invalid_input)


def test_class_discovery_select_raises_type_error_when_class_type_mismatch(sample_class):
    """Test that ClassDiscovery.select raises TypeError when class does not match specified class_type."""
    # Arrange
    class_name = sample_class

    # Act & Assert
    with pytest.raises(TypeError, match="is not type"):
        ClassDiscovery.select(class_name, class_type=str)


def test_class_discovery_get_canonical_class_name_returns_fully_qualified_name(sample_class):
    """Test that ClassDiscovery.get_canonical_class_name returns fully qualified class name."""
    # Arrange
    sample_class.__module__ = "test_module"
    sample_class.__name__ = "TestClass"

    # Act
    result = ClassDiscovery.get_canonical_class_name(sample_class)

    # Assert
    assert result == "test_module.TestClass"
