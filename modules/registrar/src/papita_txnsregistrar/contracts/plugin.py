# type: ignore
"""
Plugin contract definition for the transaction tracker system.

This module defines the abstract base class that all plugins in the transaction tracking
system must implement. It establishes the standard interface for plugin lifecycle
management, including initialization, starting, and stopping operations.

Classes:
    Self: Abstract base class defining the plugin interface for the transaction tracking system.
"""

import abc
import logging
from typing import Generic, Self, Type, TypeVar

from pydantic import BaseModel

from papita_txnsregistrar.builders.base import AbstractContractBuilder
from papita_txnsregistrar.handlers.abstract import AbstractLoadHandler
from papita_txnsregistrar.loaders.abstract import AbstractLoader

from .meta import PluginMetadata

L = TypeVar("L", bound=AbstractLoader)
B = TypeVar("B", bound=AbstractContractBuilder)

logger = logging.getLogger(__name__)


class AbstractPluginContract(BaseModel, Generic[L], metaclass=abc.ABCMeta):
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
    loader_type: Type[L] = L
    builder_type: Type[B] = B
    _handler: AbstractLoadHandler | None = None
    _loader: L | None = None
    _builder: B | None = None

    @property
    def handler(self) -> AbstractLoadHandler:
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
    def init(self, **kwargs) -> Self:
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
            Self: The plugin instance for method chaining.
        """

    @abc.abstractmethod
    def start(self, **kwargs) -> Self:
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
            Self: The plugin instance for method chaining.
        """

    @abc.abstractmethod
    def stop(self, **kwargs) -> Self:
        """
        Stop the plugin operation.

        This method should gracefully terminate the plugin's functionality, including
        cleaning up resources, closing connections, finalizing any pending operations,
        and ensuring that no data is lost during shutdown.

        Args:
            **kwargs: Parameters for the stop operation specific to the plugin
                      implementation, such as timeout values or shutdown options.

        Returns:
            Self: The plugin instance for method chaining.
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
    def load(cls, **kwargs) -> Self:
        """
        Load the plugin.

        This class method should create and return a properly initialized instance of
        the plugin. It may perform validation and setup operations necessary before
        the plugin can be used.
        Args:
            **kwargs: Parameters for loading the plugin, which may include configuration
                      options, dependencies, or context information.

        Returns:
            Self: A new instance of the plugin.
        """

    @classmethod
    @abc.abstractmethod
    def safe_load(cls, **kwargs) -> Self:
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
            Self: A new instance of the plugin.
        """


class PluginContract(AbstractPluginContract):
    """
    Plugin contract implementation.

    This class provides a concrete implementation of the AbstractPluginContract interface,
    allowing for the creation of concrete plugin instances. It extends the abstract base
    class with concrete methods for loading and safe loading the plugin.
    """

    def init(self, **kwargs) -> Self:
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
            Self: The plugin instance for method chaining.
        """
        logger.info("Building the builder...")
        self._builder = self.builder_type[self.loader_type].build(**kwargs)
        logger.info("Checking connection to the database...")
        if not self._builder.connector.connected(on_disconnected=self.on_failure_do, custom_logger=logger):
            raise ValueError("Failed to connect to the database.")

        logger.info("The plugin is connected to the database.")
        if not isinstance(self._builder.loader, self.loader_type):
            raise TypeError("The loader is not of the correct type.")

        self._loader = self._builder.loader
        logger.info("Plugin is initialized successfully.")
        return self

    def start(self, **kwargs) -> Self:
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
            Self: The plugin instance for method chaining.
        """
        if not self._builder:
            raise ValueError("The plugin has not been initialized.")

        if not self._loader:
            raise ValueError("The loader has not been built.")

        return self

    def stop(self, **kwargs) -> Self:
        """
        Stop the plugin operation.

        This method should gracefully terminate the plugin's functionality, including
        cleaning up resources, closing connections, finalizing any pending operations,
        and ensuring that no data is lost during shutdown.

        Args:
            **kwargs: Parameters for the stop operation specific to the plugin
                      implementation, such as timeout values or shutdown options.

        Returns:
            Self: The plugin instance for method chaining.
        """
        self._builder.connector.close()
        self._loader.unload()
        logger.info("The plugin is stopped successfully.")
        return self

    @classmethod
    def load(cls, **kwargs) -> Self:
        """
        Load the plugin.

        This class method should create and return a properly initialized instance of
        the plugin. It may perform validation and setup operations necessary before
        the plugin can be used.
        Args:
            **kwargs: Parameters for loading the plugin, which may include configuration
                      options, dependencies, or context information.

        Returns:
            Self: A new instance of the plugin.
        """
        return cls.model_construct(cls.model_fields_set, **kwargs)

    @classmethod
    def safe_load(cls, **kwargs) -> Self:
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
            Self: A new instance of the plugin.
        """
        return cls.model_validate(kwargs)
