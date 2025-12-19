"""Test suite for MainCLIUtils class.

This module contains unit tests for the MainCLIUtils class, which provides the primary
command-line interface for the transaction registrar system. The tests verify plugin
discovery, database connector management, argument parsing, logging configuration, and
the complete lifecycle of CLI utility operations. All database connections are mocked
to ensure test isolation without actual database interactions.
"""

import logging
from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest
from papita_txnsregistrar.contracts.plugin import PluginContract
from papita_txnsregistrar.utils.cli.abstract import AbstractCLIUtils
from papita_txnsregistrar.utils.cli.main import MainCLIUtils


@pytest.fixture
def mock_plugin_class():
    """Provide a mocked plugin class that supports CLI utilities."""
    # Create a mock class that appears to be a PluginContract subclass
    # We use a MagicMock configured to pass isinstance checks
    plugin_class = MagicMock(spec=PluginContract)
    plugin_class.meta.return_value = MagicMock(name="TestPlugin")
    plugin_class.load.return_value = MagicMock()
    # Make it appear as a class (not an instance)
    plugin_class.__class__ = type
    # Make it appear to be a subclass of both PluginContract and AbstractCLIUtils
    plugin_class.__bases__ = (PluginContract, AbstractCLIUtils)
    return plugin_class


@pytest.fixture
def mock_connector_wrapper():
    """Provide a mocked connector wrapper with database connector."""
    wrapper = MagicMock()
    mock_connector = MagicMock()
    wrapper.load.return_value.connector = mock_connector
    return wrapper


@patch("papita_txnsregistrar.utils.main.ClassDiscovery")
@patch("papita_txnsregistrar.utils.main.Registry")
def test_load_plugin_class_success(mock_registry_class, mock_class_discovery, mock_plugin_class):
    """Test that _load_plugin_class successfully discovers and returns plugin class from registry."""
    # Arrange
    mock_registry = MagicMock()
    mock_registry_class.return_value = mock_registry
    mock_registry.discover.return_value = mock_registry
    mock_registry.get.return_value = mock_plugin_class
    mock_plugin_class.__class__ = type
    mock_plugin_class.__bases__ = (AbstractCLIUtils,)

    # Act
    result = MainCLIUtils._load_plugin_class("test_plugin", ["test_module"])

    # Assert
    assert result == mock_plugin_class
    mock_registry.discover.assert_called_once()
    mock_registry.get.assert_called_once()


@patch("papita_txnsregistrar.utils.main.ClassDiscovery")
@patch("papita_txnsregistrar.utils.main.Registry")
def test_load_plugin_class_raises_runtime_error_when_plugin_not_found(mock_registry_class, mock_class_discovery):
    """Test that _load_plugin_class raises RuntimeError when plugin cannot be found in registry."""
    # Arrange
    mock_registry = MagicMock()
    mock_registry_class.return_value = mock_registry
    mock_registry.discover.return_value = mock_registry
    mock_registry.get.return_value = None

    # Act & Assert
    with pytest.raises(RuntimeError, match="Error loading plugin"):
        MainCLIUtils._load_plugin_class("nonexistent_plugin", ["test_module"])


@pytest.mark.parametrize("verbose_count,expected_level", [(0, logging.WARNING), (1, logging.INFO), (2, logging.DEBUG), (3, logging.NOTSET)])
@patch("papita_txnsregistrar.utils.main.configure_logger")
def test_setup_logger_configures_correct_level(mock_configure_logger, verbose_count, expected_level):
    """Test that _setup_logger configures logging at the correct level based on verbosity count."""
    # Arrange
    args = Namespace(verbose=verbose_count, log_config="/path/to/config.yaml")

    # Act
    MainCLIUtils._setup_logger(args)

    # Assert
    assert mock_configure_logger.call_count == 3
    for call in mock_configure_logger.call_args_list:
        assert call.kwargs["level"] == expected_level


@patch("papita_txnsregistrar.utils.main.MainCLIUtils._setup_logger")
@patch("papita_txnsregistrar.utils.main.MainCLIUtils._load_plugin_class")
@patch("papita_txnsregistrar.utils.main.ClassDiscovery")
@patch("papita_txnsregistrar.utils.main.ArgumentParser")
def test_load_parses_arguments_and_creates_instance(
    mock_parser_class, mock_class_discovery, mock_load_plugin_class, mock_setup_logger
):
    """Test that load method parses command-line arguments and creates MainCLIUtils instance."""
    # Arrange
    mock_parser = MagicMock()
    mock_parser_class.return_value = mock_parser
    mock_parsed_args = Namespace(
        script="test_script",
        plugin="test_plugin",
        modules=["test_module"],  # Provide at least one module for connector wrapper discovery
        connector_wrapper="test.connector",
        case_sensitive=True,
        strict_exact=False,
        fuzzy_threshold=95,
        safe_mode=False,
        verbose=0,
        log_config="/path/to/config.yaml",
    )
    mock_parser.parse_known_args.return_value = (mock_parsed_args, [])
    # Mock the plugin class and connector wrapper discovery
    mock_plugin_class = MagicMock()
    mock_plugin_class.meta.return_value = MagicMock(name="TestPlugin")
    mock_load_plugin_class.return_value = mock_plugin_class
    mock_class_discovery.decompose_class.return_value = ("test.module", "CLIDefaultConnectorWrapper")
    mock_connector_wrapper = MagicMock()
    mock_connector_wrapper.load.return_value.connector = MagicMock()
    # Mock select to return connector wrapper when called with the module
    mock_class_discovery.select.return_value = mock_connector_wrapper

    # Act
    result = MainCLIUtils.load(args=["script", "test_plugin"])

    # Assert
    assert isinstance(result, MainCLIUtils)
    assert result.plugin == mock_plugin_class
    mock_parser.add_argument.assert_called()
    mock_parser.parse_known_args.assert_called_once()
    mock_setup_logger.assert_called_once()
    mock_load_plugin_class.assert_called_once()


@patch("papita_txnsregistrar.utils.main.ClassDiscovery")
@patch("papita_txnsregistrar.utils.main.Registry")
def test_build_model_loads_plugin_from_string(mock_registry_class, mock_class_discovery, mock_plugin_class):
    """Test that _build_model successfully loads plugin from string name using registry."""
    # Arrange
    mock_class_discovery.decompose_class.return_value = ("test.module", "CLIDefaultConnectorWrapper")
    mock_class_discovery.select.return_value = MagicMock()
    mock_registry = MagicMock()
    mock_registry_class.return_value = mock_registry
    mock_registry.discover.return_value = mock_registry
    mock_registry.get.return_value = mock_plugin_class
    mock_plugin_class.__class__ = type
    mock_plugin_class.__bases__ = (AbstractCLIUtils,)
    mock_connector_wrapper = MagicMock()
    mock_connector_wrapper.load.return_value.connector = MagicMock()
    mock_class_discovery.select.return_value = mock_connector_wrapper

    instance = MainCLIUtils(
        plugin="test_plugin",
        modules=["test_module"],
        connector_wrapper="test.connector",
        case_sensitive=True,
        strict_exact=False,
        fuzzy_threshold=95,
        safe_mode=False,
    )

    # Act
    result = instance._build_model()

    # Assert
    assert result == instance
    assert instance.plugin == mock_plugin_class
    mock_registry.get.assert_called_once()


@patch("papita_txnsregistrar.utils.main.ClassDiscovery")
def test_build_model_raises_value_error_when_no_connector_wrapper(mock_class_discovery, mock_plugin_class):
    """Test that _build_model raises ValueError when connector wrapper cannot be found."""
    # Arrange
    mock_class_discovery.decompose_class.return_value = (None, None)
    # Use model_construct to bypass initial validation, then test _build_model directly
    instance = MainCLIUtils.model_construct(
        plugin=mock_plugin_class,
        modules=["test_module"],
        connector_wrapper=None,
        case_sensitive=True,
        strict_exact=False,
        fuzzy_threshold=95,
        safe_mode=False,
    )

    # Act & Assert
    with pytest.raises(ValueError, match="No valid connector wrapper could be found"):
        instance._build_model()


@patch("papita_txnsregistrar.utils.main.ClassDiscovery")
def test_build_model_raises_runtime_error_on_connector_wrapper_discovery_failure(
    mock_class_discovery, mock_plugin_class
):
    """Test that _build_model raises RuntimeError when connector wrapper discovery fails."""
    # Arrange
    mock_class_discovery.decompose_class.return_value = ("test.module", "CLIDefaultConnectorWrapper")
    mock_class_discovery.select.return_value = None
    # Use model_construct to bypass initial validation, then test _build_model directly
    instance = MainCLIUtils.model_construct(
        plugin=mock_plugin_class,
        modules=["test_module"],
        connector_wrapper="test.connector",
        case_sensitive=True,
        strict_exact=False,
        fuzzy_threshold=95,
        safe_mode=False,
    )

    # Act & Assert
    with pytest.raises(RuntimeError, match="Error building model"):
        instance._build_model()


def test_run_instantiates_plugin_and_returns_self(mock_plugin_class):
    """Test that run method instantiates plugin using load method and returns self for chaining."""
    # Arrange
    mock_plugin_instance = MagicMock()
    mock_plugin_class.load.return_value = mock_plugin_instance
    # Use model_construct to bypass validation since we're testing run() directly
    instance = MainCLIUtils.model_construct(
        plugin=mock_plugin_class,
        modules=["test_module"],
        connector_wrapper="test.connector",
        case_sensitive=True,
        strict_exact=False,
        fuzzy_threshold=95,
        safe_mode=False,
    )
    instance.connector = MagicMock()

    # Act
    result = instance.run()

    # Assert
    assert result == instance
    assert instance._plugin_instance == mock_plugin_instance
    mock_plugin_class.load.assert_called_once()


def test_stop_closes_connector_and_plugin(mock_plugin_class):
    """Test that stop method properly closes both plugin instance and database connector."""
    # Arrange
    # Use model_construct to bypass validation since we're testing stop() directly
    instance = MainCLIUtils.model_construct(
        plugin=mock_plugin_class,
        modules=["test_module"],
        connector_wrapper="test.connector",
        case_sensitive=True,
        strict_exact=False,
        fuzzy_threshold=95,
        safe_mode=False,
    )
    mock_connector = MagicMock()
    instance.connector = mock_connector
    mock_plugin_instance = MagicMock()
    instance._plugin_instance = mock_plugin_instance

    # Act
    result = instance.stop()

    # Assert
    assert result == instance
    mock_plugin_instance.stop.assert_called_once()
    mock_connector.close.assert_called_once()


@patch("papita_txnsregistrar.utils.main.MainCLIUtils._setup_logger")
@patch("papita_txnsregistrar.utils.main.ArgumentParser")
def test_load_raises_value_error_when_args_not_list(mock_parser_class, mock_setup_logger):
    """Test that load method raises ValueError when args parameter is not a list of strings."""
    # Arrange
    mock_parser = MagicMock()
    mock_parser_class.return_value = mock_parser

    # Act & Assert
    with pytest.raises(ValueError, match="args must be"):
        MainCLIUtils.load(args="not_a_list")
