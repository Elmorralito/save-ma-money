"""Unit tests for the configutils module in the Papita Transactions system.

This test suite validates logging configuration functionality including YAML file loading,
logger setup, and error handling. All tests use mocking to ensure isolation and avoid
external file system dependencies.
"""

import logging
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

from papita_txnsmodel.utils import configutils


@pytest.fixture
def sample_logger_config():
    """Provide a sample logger configuration dictionary for testing."""
    return {
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "simple": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "simple",
                "stream": "ext://sys.stdout",
            }
        },
        "loggers": {
            "test_logger": {
                "level": "DEBUG",
                "handlers": ["console"],
                "propagate": False,
            }
        },
    }


@pytest.fixture
def mock_logger():
    """Provide a mocked logger for testing logger configuration operations."""
    logger = MagicMock(spec=logging.Logger)
    logger.handlers = [MagicMock(spec=logging.Handler)]
    return logger


@patch("papita_txnsmodel.utils.configutils.logging.config.dictConfig")
@patch("papita_txnsmodel.utils.configutils.logging.getLogger")
@patch("builtins.open", new_callable=mock_open)
@patch("papita_txnsmodel.utils.configutils.yaml.load")
def test_configure_logger_loads_config_and_sets_level(
    mock_yaml_load, mock_file_open, mock_get_logger, mock_dict_config, sample_logger_config, mock_logger
):
    """Test that configure_logger successfully loads YAML config and configures logger with specified level."""
    # Arrange
    logger_name = "test_logger"
    config_path = "/path/to/logger.yaml"
    level = logging.DEBUG
    mock_yaml_load.return_value = sample_logger_config
    mock_get_logger.return_value = mock_logger

    # Act
    configutils.configure_logger(logger_name, config=config_path, level=level)

    # Assert
    mock_file_open.assert_called_once_with(config_path, mode="r", encoding=configutils.DEFAULT_ENCODING)
    mock_yaml_load.assert_called_once()
    mock_dict_config.assert_called_once_with(sample_logger_config)
    mock_get_logger.assert_called_once_with(logger_name)
    mock_logger.setLevel.assert_called_once_with(level)
    assert mock_logger.handlers[0].setLevel.call_count == len(mock_logger.handlers)
    mock_logger.debug.assert_called_once()


@patch("papita_txnsmodel.utils.configutils.logging.config.dictConfig")
@patch("papita_txnsmodel.utils.configutils.logging.getLogger")
@patch("builtins.open", new_callable=mock_open)
@patch("papita_txnsmodel.utils.configutils.yaml.load")
def test_configure_logger_uses_default_config_path_when_not_provided(
    mock_yaml_load, mock_file_open, mock_get_logger, mock_dict_config, sample_logger_config, mock_logger
):
    """Test that configure_logger uses DEFAULT_LOGGER_CONFIG_PATH when config parameter is not provided."""
    # Arrange
    logger_name = "test_logger"
    level = logging.INFO
    mock_yaml_load.return_value = sample_logger_config
    mock_get_logger.return_value = mock_logger

    # Act
    configutils.configure_logger(logger_name, level=level)

    # Assert
    mock_file_open.assert_called_once_with(
        configutils.DEFAULT_LOGGER_CONFIG_PATH, mode="r", encoding=configutils.DEFAULT_ENCODING
    )
    mock_dict_config.assert_called_once_with(sample_logger_config)
    mock_logger.setLevel.assert_called_once_with(level)


@patch("builtins.open", side_effect=FileNotFoundError("Config file not found"))
def test_configure_logger_raises_file_not_found_error_for_missing_config(mock_file_open):
    """Test that configure_logger raises FileNotFoundError when configuration file does not exist."""
    # Arrange
    logger_name = "test_logger"
    config_path = "/nonexistent/path/logger.yaml"

    # Act & Assert
    with pytest.raises(FileNotFoundError, match="Config file not found"):
        configutils.configure_logger(logger_name, config=config_path)
