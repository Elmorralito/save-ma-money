"""
Plugin contract definition for the transaction tracker system.

This module defines the abstract base class that all plugins in the transaction tracking
system must implement. It establishes the standard interface for plugin lifecycle
management, including initialization, starting, and stopping operations.

Classes:
    PluginContract: Abstract base class defining the plugin interface for the transaction tracking system.
"""

import abc
from typing import Generic, TypeVar

from pydantic import BaseModel

from papita_txnsregistrar.handlers.abstract import AbstractLoadHandler
from papita_txnsregistrar.loaders.abstract import AbstractLoader

from .meta import PluginMetadata

H = TypeVar("H", bound=AbstractLoadHandler)
L = TypeVar("L", bound=AbstractLoader)


class PluginContract(BaseModel, Generic[H, L], metaclass=abc.ABCMeta):
    """
    Abstract base class defining the contract that all plugins must implement.

    This class establishes the required interface for plugins in the transaction tracking
    system, including lifecycle methods and metadata handling. Every plugin must extend
    this class and implement its abstract methods to ensure consistent behavior within
    the transaction tracking ecosystem.

    The plugin lifecycle typically follows this sequence:
    1. Load - Create the plugin instance via load or safe_load
    2. Build handler - Configure the transaction processing handler
    3. Init - Perform initialization tasks
    4. Start - Begin active operation
    5. Stop - Terminate operation gracefully

    Attributes:
        __meta__ (PluginMetadata): Metadata associated with the plugin including identification
                                   and capability information.
        _handler (AbstractLoadHandler): Handler used by the plugin for processing transactions.
    """

    __meta__: PluginMetadata
    _handler: H | None = None
    _loader: L | None = None

    @property
    def handler(self) -> H:
        """
        Get the plugin's handler.

        Returns:
            AbstractLoadHandler: The handler associated with this plugin for transaction processing.

        Raises:
            TypeError: If the handler has not been loaded or is corrupt.
        """
        if not isinstance(self._handler, AbstractLoadHandler):
            raise TypeError("Handler not loaded or corrupt.")

        return self._handler

    @property
    def loader(self) -> L:
        """
        Get the plugin's loader.

        Returns:
            AbstractLoadHandler: The loader associated with this plugin for transaction processing.

        Raises:
            TypeError: If the loader has not been loaded or is corrupt.
        """
        if not isinstance(self._loader, AbstractLoader):
            raise TypeError("Handler not loaded or corrupt.")

        return self._loader

    @abc.abstractmethod
    def build_handler(self, **kwargs) -> "PluginContract":
        """
        Build and configure the handler for this plugin.

        This method should create and configure a AbstractLoadHandler instance that will be
        used by the plugin to process transactions. The handler typically defines how
        transactions are interpreted and managed by this specific plugin.

        Args:
            **kwargs: Configuration parameters for the handler such as connection details,
                      processing rules, or other plugin-specific settings.

        Returns:
            PluginContract: The plugin instance for method chaining.
        """

    @abc.abstractmethod
    def init(self, **kwargs) -> "PluginContract":
        """
        Initialize the plugin.

        This method should perform any necessary setup before the plugin starts, such as
        establishing connections, loading configurations, preparing resources, or
        validating the environment.

        Args:
            **kwargs: Initialization parameters specific to the plugin implementation,
                      which may include configuration paths, feature flags, or other
                      setup options.

        Returns:
            PluginContract: The plugin instance for method chaining.
        """

    @abc.abstractmethod
    def start(self, **kwargs) -> "PluginContract":
        """
        Start the plugin operation.

        This method should begin the plugin's primary functionality, such as starting
        listeners, initiating transaction processing, activating services, or beginning
        any ongoing operations the plugin is responsible for.

        Args:
            **kwargs: Parameters for the start operation specific to the plugin
                      implementation, which may include runtime options or conditional
                      activation settings.

        Returns:
            PluginContract: The plugin instance for method chaining.
        """

    @abc.abstractmethod
    def stop(self, **kwargs) -> "PluginContract":
        """
        Stop the plugin operation.

        This method should gracefully terminate the plugin's functionality, including
        cleaning up resources, closing connections, finalizing any pending operations,
        and ensuring that no data is lost during shutdown.

        Args:
            **kwargs: Parameters for the stop operation specific to the plugin
                      implementation, such as timeout values or shutdown options.

        Returns:
            PluginContract: The plugin instance for method chaining.
        """

    @classmethod
    def meta(cls) -> PluginMetadata:
        """
        Retrieve the plugin's metadata.

        This method provides access to the plugin's metadata, which includes information
        such as the plugin's name, version, capabilities, dependencies, and other
        descriptive attributes used for registration and management.

        Returns:
            PluginMetadata: The metadata associated with this plugin.

        Raises:
            ValueError: If the metadata has not been loaded into the plugin.
        """
        meta = getattr(cls, "__meta__", None)
        if not meta:
            raise ValueError("The metadata has not been loaded into the plugin.")

        return meta

    @classmethod
    @abc.abstractmethod
    def load(cls, **kwargs) -> "PluginContract":
        """
        Load the plugin.

        This class method should create and return a properly initialized instance of
        the plugin. It may perform validation and setup operations necessary before
        the plugin can be used.
        Args:
            **kwargs: Parameters for loading the plugin, which may include configuration
                      options, dependencies, or context information.

        Returns:
            PluginContract: A new instance of the plugin.
        """

    @classmethod
    @abc.abstractmethod
    def safe_load(cls, **kwargs) -> "PluginContract":
        """
        Safely load the plugin with error handling.

        This class method should create and return a properly initialized instance of
        the plugin with additional error handling for robustness. It provides a safer
        alternative to the standard load method by implementing fault tolerance and
        appropriate fallback mechanisms.

        Args:
            **kwargs: Parameters for loading the plugin, which may include configuration
                      options, dependencies, or context information.

        Returns:
            PluginContract: A new instance of the plugin.
        """
