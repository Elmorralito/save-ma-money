# from typing import Dict, Self, Tuple, Type
from typing import Dict, Self, Type

from papita_txnsregistrar.contracts.loader import plugin
from papita_txnsregistrar.contracts.meta import PluginMetadata
from papita_txnsregistrar.contracts.plugin import PluginContract
from papita_txnsregistrar.handlers.abstract import AbstractLoadHandler

# from papita_txnsregistrar.handlers.factory import HandlerFactory
from papita_txnsregistrar.loaders.file.impl import ExcelFileLoader


@plugin(
    loader_type=ExcelFileLoader,
    meta=PluginMetadata(
        name="excel_loader_plugin",
        version="1.0.0",
        feature_tags=["excel_file_loader", "excel_transactions", "excel_accounts"],
        description="Loading transactions and accounts from Excel files.",
    ),
)
class ExcelFilePlugin(PluginContract[ExcelFileLoader]):
    """
    Plugin for handling Excel file transactions.

    This plugin integrates the Excel file loader with the transaction tracking system,
    providing capabilities to load and process transaction data from Excel files.
    It utilizes the ExcelFileLoader for data loading and a specified handler for
    transaction processing.

    """

    handlers: Dict[str, Type[AbstractLoadHandler]] = {}

    # TODO: Change this for the builder...

    # def build_handler(self, label: str, *labels: Tuple[str, ...], **kwargs) -> Self:
    #     """
    #     Build and configure the handler for this plugin.

    #     This method should create and configure a AbstractLoadHandler instance that will be
    #     used by the plugin to process transactions. The handler typically defines how
    #     transactions are interpreted and managed by this specific plugin.

    #     Args:
    #         **kwargs: Configuration parameters for the handler such as connection details,
    #                   processing rules, or other plugin-specific settings.

    #     Returns:
    #         Self: The plugin instance for method chaining.
    #     """
    #     factory = HandlerFactory.load(*tuple(kwargs.get("handler_modules", [])))
    #     self.handlers = {
    #         label_.strip(): factory.get(label_.strip(), **kwargs) for label_ in (labels + (label,)) if label_.strip()
    #     }
    #     return self

    # def build_loader(self, **kwargs) -> Self:
    #     """
    #     """
    #     path = kwargs.pop("path")
    #     self._loader = self.loader_type.model_validate({"path": path, **kwargs})
    #     return self

    # def build_service(self, handler: Type[AbstractLoadHandler], **kwargs):
    #     pass

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

        sheets = self._loader.check_source(**kwargs).load(**kwargs).result.keys()
        return self.build_handler(*sheets, **kwargs)

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
        if not self._loader:
            raise ValueError("The plugin has not been initialized.")

        # for sheet_name in self.
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
        return cls(**kwargs)

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
        return cls(**kwargs)
