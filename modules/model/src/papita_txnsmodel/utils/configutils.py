"""Logging configuration utilities for the transaction model library.

This module provides utilities for configuring Python's logging system within the
papita_txnsmodel library. It supports loading logging configurations from YAML files
and applying them to specific loggers with customizable log levels.

The module is primarily used to set up consistent logging across the library and
integrated systems, allowing for centralized configuration management through YAML
files while maintaining the flexibility to override log levels programmatically.

Key Components:
    configure_logger: Function to configure a logger from a YAML configuration file
                      and set its log level.
    DEFAULT_ENCODING: Default file encoding used when reading configuration files.
    LOGGER_NAME: Default logger name, set to the library name.
    DEFAULT_LOGGER_CONFIG_PATH: Default path to the logger configuration YAML file.
"""

import importlib.resources as importlib_resources
import logging
import logging.config
import os

import yaml

from papita_txnsmodel import LIB_NAME

DEFAULT_ENCODING = "utf-8"
LOGGER_NAME = LIB_NAME
DEFAULT_LOGGER_CONFIG_PATH = str(importlib_resources.files(f"{LIB_NAME}.configs").joinpath("logger.yaml"))


def configure_logger(
    logger_name: str, config: os.PathLike | str = DEFAULT_LOGGER_CONFIG_PATH, level: int = logging.INFO
) -> None:
    """Configure a logger from a YAML configuration file and set its log level.

    This function loads a logging configuration from a YAML file, applies it using
    Python's logging.config.dictConfig, retrieves the specified logger, and sets its
    log level. The configuration file should follow the standard Python logging
    configuration dictionary format as defined in the logging.config module.

    The function first applies the entire logging configuration from the YAML file,
    which may configure multiple loggers, handlers, and formatters. Then it retrieves
    the specific logger by name and sets its level to the provided value, allowing
    for programmatic override of the level specified in the configuration file.

    Args:
        logger_name: The name of the logger to configure. This should match the
                    logger name used throughout the application (typically the module
                    or package name).
        config: Path to the YAML configuration file containing the logging
                configuration dictionary. The file should be readable and contain
                a valid logging configuration structure. Defaults to the library's
                default logger configuration file path.
        level: The log level to set for the specified logger. Must be one of the
               standard logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) or
               an integer value. Defaults to logging.INFO.

    Returns:
        None. The function modifies the logging configuration in place.

    Raises:
        FileNotFoundError: If the specified configuration file does not exist.
        yaml.YAMLError: If the YAML file cannot be parsed or contains invalid YAML
                        syntax.
        ValueError: If the YAML content does not represent a valid logging
                    configuration dictionary.
        OSError: If the configuration file cannot be read (e.g., permission issues).

    Note:
        The function uses yaml.SafeLoader to parse the YAML file, which provides
        safe YAML parsing without arbitrary code execution risks. The configuration
        dictionary is applied globally using logging.config.dictConfig, which may
        affect other loggers configured in the same process.

    Example:
        Configure a logger with default settings:

        .. code-block:: python

            configure_logger("my_module")

        Configure a logger with a custom config file and debug level:

        .. code-block:: python

            configure_logger(
                logger_name="my_module",
                config="/path/to/custom_logger.yaml",
                level=logging.DEBUG
            )
    """
    with open(config, mode="r", encoding=DEFAULT_ENCODING) as freader:
        logger_config = yaml.load(freader, Loader=yaml.SafeLoader)
        logging.config.dictConfig(logger_config)

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    # Update handler levels to match the logger level
    for handler in logger.handlers:
        handler.setLevel(level)

    logger.debug("Logger '%s' setup with level '%s' from config '%s'", logger_name, level, logger_config)
