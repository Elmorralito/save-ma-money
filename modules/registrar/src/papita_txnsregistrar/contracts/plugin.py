# type: ignore
"""
Plugin contract definition for the transaction tracker system.

This module defines the abstract base class that all plugins in the transaction tracking
system must implement, as well as a concrete implementation of this contract. It establishes
the standard interface for plugin lifecycle management, including initialization, starting,
and stopping operations.

Classes:
    AbstractPluginContract: Abstract base class defining the plugin interface.
    PluginContract: Concrete implementation of the plugin contract interface.
"""

import abc
import logging
from typing import Generic, Self, Type, TypeVar, get_args

from pydantic import BaseModel

from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.handlers.abstract import AbstractHandler
from papita_txnsmodel.utils.enums import FallbackAction
from papita_txnsregistrar.builders.abstract import AbstractContractBuilder, L
from papita_txnsregistrar.loaders.abstract import AbstractDataLoader

from .meta import PluginMetadata

B = TypeVar("B", bound=AbstractContractBuilder)

logger = logging.getLogger(__name__)


class AbstractPluginContract(BaseModel, Generic[L, B], metaclass=abc.ABCMeta):
    """
    Abstract base class defining the contract that all plugins must implement.

    This class establishes the required interface for plugins in the transaction tracking
    system, including lifecycle methods and metadata handling. Every plugin must extend
    this class and implement its abstract methods to ensure consistent behavior within
    the transaction tracking ecosystem.

    The plugin lifecycle typically follows this sequence:
    1. Load - Create the plugin instance via load or safe_load
    2. Init - Perform initialization tasks
    3. Start - Begin active operation
    4. Stop - Terminate operation gracefully

    Attributes:
        __meta__ (PluginMetadata): Metadata associated with the plugin including identification
                                   and capability information.
        loader_type (Type[L]): Type of loader used by this plugin.
        builder_type (Type[B]): Type of builder used by this plugin.
        _handler (AbstractHandler | None): Handler used by the plugin for processing transactions.
        _loader (L | None): Loader instance for this plugin.
        _builder (B | None): Builder instance for this plugin.
    """

    __meta__: PluginMetadata
    loader_generic_type: Type[L] = L
    builder_generic_type: Type[B] = B
    on_conflict_do: OnUpsertConflictDo = OnUpsertConflictDo.UPDATE
    on_failure_do: FallbackAction = FallbackAction.RAISE
    _handler: AbstractHandler | None = None
    _loader: L | None = None
    _builder: B | None = None

    @property
    @abc.abstractmethod
    def builder(self) -> B:
        """
        Get the plugin's builder.

        Returns:
            B: The builder associated with this plugin for transaction processing.

        Raises:
            TypeError: If the builder has not been loaded or is corrupt.
        """

    @property
    @abc.abstractmethod
    def handler(self) -> AbstractHandler:
        """
        Get the plugin's handler.

        Returns:
            AbstractHandler: The handler associated with this plugin for transaction processing.

        Raises:
            TypeError: If the handler has not been loaded or is corrupt.
        """

    @property
    @abc.abstractmethod
    def loader(self) -> L:
        """
        Get the plugin's loader.

        Returns:
            L: The loader associated with this plugin for transaction processing.

        Raises:
            TypeError: If the loader has not been loaded or is corrupt.
        """

    @property
    @abc.abstractmethod
    def loader_type(self) -> Type[L]:
        """Get the loader type class from the plugin's generic type parameters.

        This property extracts and returns the concrete loader type class that was
        specified as the first generic parameter when the plugin class was defined.
        For example, if a plugin is defined as
        `ExcelFilePlugin(PluginContract[ExcelFileLoader, ExcelContractBuilder])`,
        this property will return the `ExcelFileLoader` class.

        The implementation should extract the loader type from the plugin's generic
        type parameters, typically by inspecting the class's type annotations or
        using typing introspection utilities like `get_args()` to retrieve the
        generic type arguments.

        Returns:
            The loader type class (a subclass of AbstractDataLoader) that was specified
            as the first generic parameter in the plugin's class definition. This
            class can be used to instantiate loader instances or perform type checking.

        Raises:
            TypeError: If the extracted type is not a valid subclass of AbstractDataLoader,
                      indicating that the generic type parameter was incorrectly specified
                      or the type extraction failed.

        Note:
            Concrete implementations should extract the type from the plugin's generic
            parameters using typing introspection. The type is typically stored in the
            `loader_generic_type` field annotation and can be extracted using `get_args()`.
        """

    @property
    @abc.abstractmethod
    def builder_type(self) -> Type[B]:
        """Get the builder type class from the plugin's generic type parameters.

        This property extracts and returns the concrete builder type class that was
        specified as the second generic parameter when the plugin class was defined.
        For example, if a plugin is defined as
        `ExcelFilePlugin(PluginContract[ExcelFileLoader, ExcelContractBuilder])`,
        this property will return the `ExcelContractBuilder` class.

        The implementation should extract the builder type from the plugin's generic
        type parameters, typically by inspecting the class's type annotations or
        using typing introspection utilities like `get_args()` to retrieve the
        generic type arguments.

        Returns:
            The builder type class (a subclass of AbstractContractBuilder) that was
            specified as the second generic parameter in the plugin's class definition.
            This class can be used to instantiate builder instances or perform type
            checking.

        Raises:
            TypeError: If the extracted type is not a valid subclass of
                      AbstractContractBuilder, indicating that the generic type parameter
                      was incorrectly specified or the type extraction failed.

        Note:
            Concrete implementations should extract the type from the plugin's generic
            parameters using typing introspection. The type is typically stored in the
            `builder_generic_type` field annotation and can be extracted using `get_args()`.
        """

    @abc.abstractmethod
    def init(self, *, connector: Type[SQLDatabaseConnector], **kwargs) -> Self:
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
    @abc.abstractmethod
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
    Concrete implementation of the plugin contract interface.

    This class provides a concrete implementation of the AbstractPluginContract interface,
    allowing for the creation of concrete plugin instances. It handles the lifecycle of
    plugins including initialization, operation, and proper cleanup of resources when
    stopping. It manages the builder, loader, and handler components required for
    transaction processing.
    """

    @property
    def builder(self) -> B:
        """
        Get the plugin's builder.

        Returns:
            B: The builder associated with this plugin for transaction processing.

        Raises:
            TypeError: If the builder has not been loaded or is corrupt.
        """
        if not isinstance(self._builder, AbstractContractBuilder):
            raise TypeError("Builder not loaded or corrupt.")

        return self._builder

    @property
    def handler(self) -> AbstractHandler:
        """
        Get the plugin's handler.

        Returns:
            AbstractHandler: The handler associated with this plugin for transaction processing.

        Raises:
            TypeError: If the handler has not been loaded or is corrupt.
        """
        if not isinstance(self._handler, AbstractHandler):
            raise TypeError("Handler not loaded or corrupt.")

        return self._handler

    @property
    def loader(self) -> L:
        """
        Get the plugin's loader.

        Returns:
            L: The loader associated with this plugin for transaction processing.

        Raises:
            TypeError: If the loader has not been loaded or is corrupt.
        """
        if not isinstance(self._loader, AbstractDataLoader):
            raise TypeError("Loader not loaded or corrupt.")

        return self._loader

    @property
    def loader_type(self) -> Type[L]:
        """Get the loader type class from the plugin's generic type parameters.

        This property extracts and returns the concrete loader type class that was
        specified as the first generic parameter when the plugin class was defined.

        Returns:
            Type[L]: The loader type class associated with the plugin.

        Raises:
            TypeError: If the extracted type is not a valid subclass of AbstractDataLoader.
        """
        loader_type = next(iter(get_args(self.__class__.model_fields["loader_generic_type"].annotation)))
        if not issubclass(loader_type, AbstractDataLoader):
            raise TypeError("Loader type is not a subclass of AbstractDataLoader.")

        return loader_type

    @property
    def builder_type(self) -> Type[B]:
        """Get the builder type class from the plugin's generic type parameters.

        This property extracts and returns the concrete builder type class that was
        specified as the second generic parameter when the plugin class was defined.

        Returns:
            Type[B]: The builder type class associated with the plugin.

        Raises:
            TypeError: If the extracted type is not a valid subclass of AbstractContractBuilder.
        """
        builder_type = next(iter(get_args(self.__class__.model_fields["builder_generic_type"].annotation)))
        if not issubclass(builder_type, AbstractContractBuilder):
            raise TypeError("Builder type is not a subclass of AbstractContractBuilder.")

        return builder_type

    # TODO: Add a way to automatically handle attributes from children contracts.
    def init(self, *, connector: Type[SQLDatabaseConnector], **kwargs) -> Self:
        """
        Initialize the plugin by setting up the builder and connections.

        This method creates the builder, verifies database connectivity, and initializes
        the loader. It performs validation to ensure that the components are of the correct
        type and properly connected.

        Args:
            **kwargs: Initialization parameters that are passed to the builder,
                      such as connection details and configuration options.

        Returns:
            Self: The plugin instance for method chaining.

        Raises:
            ValueError: If connection to the database fails.
            TypeError: If the loader is not of the correct type.
        """
        logger.info("Building the builder...")
        logger.debug("Loader type: %s", self.loader_type)
        logger.debug("Builder type: %s", self.builder_type)
        kwargs_ = {
            "connector": connector,
            "on_failure_do": self.on_failure_do,
            "on_conflict_do": self.on_conflict_do,
            **kwargs,
        }
        self._builder = self.builder_type[self.loader_type].load(**kwargs_).build(**kwargs_)
        logger.info("Checking connection to the database...")
        if not self.builder.connector.connected(on_disconnected=self.on_failure_do, custom_logger=logger):
            raise ValueError("Failed to connect to the database.")

        logger.info("The plugin is connected to the database.")
        if not isinstance(self.builder.loader, self.loader_type):
            raise TypeError("The loader is not of the correct type.")

        self._loader = self.builder.loader
        logger.info("Plugin is initialized successfully.")
        return self

    def start(self, **kwargs) -> Self:
        """
        Start the plugin operation.

        This method begins the plugin's primary functionality after verifying that
        the necessary components have been initialized. It checks for on_conflict_do proper initialization
        of the builder and loader before allowing the plugin to start.

        Args:
            **kwargs: Parameters for the start operation, which may include runtime options
                      or conditional activation settings.

        Returns:
            Self: The plugin instance for method chaining.

        Raises:
            ValueError: If the plugin has not been initialized or the loader has not been built.
        """
        if not self.builder:
            raise ValueError("The plugin has not been initialized.")

        if not self.loader:
            raise ValueError("The loader has not been built.")

        return self

    def stop(self, **kwargs) -> Self:
        """
        Stop the plugin operation and clean up resources.

        This method gracefully terminates the plugin's functionality by closing on_conflict_do database
        connections and unloading the loader. It ensures proper cleanup of all resources
        to prevent memory leaks or orphaned connections.

        Args:
            **kwargs: Parameters for the stop operation, such as timeout values
                      or specific shutdown options.

        Returns:
            Self: The plugin instance for method chaining.
        """
        self.builder.connector.close()
        self.loader.unload()
        logger.info("The plugin is stopped successfully.")
        return self

    @classmethod
    def meta(cls) -> PluginMetadata:
        """
        Retrieve the plugin's metadata.

        This method provides access to the plugin's metadata, which includes information
        about the plugin's identity and capabilities. It retrieves the metadata from the
        class's __meta__ attribute.

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
    def load(cls, **kwargs) -> Self:
        """
        Load the plugin using Pydantic's model construction.

        This method creates a new plugin instance using Pydantic's model_construct method,
        which directly initializes the model fields without additional validation.

        Args:
            **kwargs: Parameters for loading the plugin, such as configuration options
                      or dependencies.

        Returns:
            Self: A new instance of the plugin.
        """
        raise NotImplementedError()

    @classmethod
    def safe_load(cls, **kwargs) -> Self:
        """
        Safely load the plugin with full validation.

        This method creates a new plugin instance using Pydantic's model_validate method,
        which performs complete validation of input data according to the model schema.
        This provides additional safety compared to the standard load method.

        Args:
            **kwargs: Parameters for loading the plugin, such as configuration options
                      or dependencies.

        Returns:
            Self: A new validated instance of the plugin.
        """
        raise NotImplementedError()
