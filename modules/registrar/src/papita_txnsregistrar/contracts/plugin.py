"""
Plugin contract definition for the transaction tracker system.

This module defines the abstract base class that all plugins in the transaction tracking
system must implement. It establishes the standard interface for plugin lifecycle
management, including initialization, starting, and stopping operations.
"""

import abc

from papita_txnstracker.handlers.base import BaseLoadHandler

from .meta import PluginMetadata


class PluginContract(abc.ABC):
    """
    Abstract base class defining the contract that all plugins must implement.

    This class establishes the required interface for plugins in the transaction tracking
    system, including lifecycle methods and metadata handling. Every plugin must extend
    this class and implement its abstract methods to ensure consistent behavior.

    Attributes:
        __meta__ (PluginMetadata): Metadata associated with the plugin.
        _handler (BaseLoadHandler): Handler used by the plugin for processing transactions.
    """

    __meta__: PluginMetadata

    def __init__(self, *args, **kwargs):
        """
        Initialize a new plugin instance.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        self._handler: BaseLoadHandler | None = None

    @property
    def handler(self) -> BaseLoadHandler:
        """
        Get the plugin's handler.

        Returns:
            BaseLoadHandler: The handler associated with this plugin.

        Raises:
            TypeError: If the handler has not been loaded or is corrupt.
        """
        if not isinstance(self._handler, BaseLoadHandler):
            raise TypeError("Handler not loaded or corrupt.")

        return self._handler

    @abc.abstractmethod
    def build_handler(self, **kwargs) -> "PluginContract":
        """
        Build and configure the handler for this plugin.

        Args:
            **kwargs: Configuration parameters for the handler.

        Returns:
            PluginContract: The plugin instance for method chaining.
        """

    @abc.abstractmethod
    def init(self, **kwargs) -> "PluginContract":
        """
        Initialize the plugin.

        This method should perform any necessary setup before the plugin starts.

        Args:
            **kwargs: Initialization parameters.

        Returns:
            PluginContract: The plugin instance for method chaining.
        """

    @abc.abstractmethod
    def start(self, **kwargs) -> "PluginContract":
        """
        Start the plugin operation.

        This method should begin the plugin's primary functionality.

        Args:
            **kwargs: Parameters for the start operation.

        Returns:
            PluginContract: The plugin instance for method chaining.
        """

    @abc.abstractmethod
    def stop(self, **kwargs) -> "PluginContract":
        """
        Stop the plugin operation.

        This method should gracefully terminate the plugin's functionality.

        Args:
            **kwargs: Parameters for the stop operation.

        Returns:
            PluginContract: The plugin instance for method chaining.
        """

    @classmethod
    def meta(cls) -> PluginMetadata:
        """
        Retrieve the plugin's metadata.

        Returns:
            PluginMetadata: The metadata associated with this plugin.

        Raises:
            ValueError: If the metadata has not been loaded into the plugin.
        """
        meta = getattr(cls, "__meta__", None)
        if not meta:
            raise ValueError("The metadata has not been loaded into the plugin.")

        return meta
