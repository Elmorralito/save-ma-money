# type: ignore
"""
Excel file plugin module for transaction registration.
This module provides a plugin for loading and processing transaction data from Excel files.
It integrates the Excel file loader with the transaction tracking system, enabling the
loading, processing, and registration of transaction data from Excel spreadsheets.
"""

# from typing import Dict, Self, Tuple, Type
import logging
from typing import Self

from papita_txnsregistrar_plugins.core.builders import ExcelContractBuilder

from papita_txnsregistrar import LIB_NAME
from papita_txnsregistrar.contracts.loader import plugin
from papita_txnsregistrar.contracts.meta import PluginMetadata
from papita_txnsregistrar.contracts.plugin import PluginContract
from papita_txnsregistrar.loaders.file.impl import ExcelFileLoader

logger = logging.getLogger(f"{LIB_NAME}.plugin.core.excel")


@plugin(
    meta=PluginMetadata(
        name="excel_loader_plugin",
        version="1.0.0",
        feature_tags=["excel_file_loader", "excel_transactions", "excel_accounts"],
        dependencies=[ExcelFileLoader, ExcelContractBuilder],
        description="Loading transactions and accounts from Excel files.",
        enabled=True,
    ),
)
class ExcelFilePlugin(PluginContract[ExcelFileLoader, ExcelContractBuilder]):
    """Plugin for handling Excel file transactions.

    This plugin integrates the Excel file loader with the transaction tracking system,
    providing capabilities to load and process transaction data from Excel files.
    It utilizes the ExcelFileLoader for data loading and a specified handler for
    transaction processing. The plugin acts as a bridge between Excel data sources
    and the transaction registration system.

    The plugin workflow includes:
    1. Loading data from Excel files through the configured loader
    2. Distributing data to appropriate handlers registered in the builder
    3. Executing each handler's load and dump operations to process the data

    Attributes:
        _loader (ExcelFileLoader): Instance that loads and parses Excel files.
        _builder (ExcelContractBuilder): Builder containing registered handlers for processing data.
    """

    def start(self, **kwargs) -> Self:
        """Start the plugin execution process.

        Initiates the plugin's data loading and processing workflow by:
        1. Calling the parent class's start method to initialize the plugin
        2. Retrieving data for each registered handler from the loader results
        3. Passing the appropriate data to each handler for processing
        4. Executing the handler's load and dump operations sequentially

        Args:
            **kwargs: Additional keyword arguments passed to handlers.
                These arguments are forwarded to the handlers' load and dump methods,
                except for 'data_source' which is removed before passing.

        Returns:
            Self: The plugin instance for method chaining.
        """
        super().start(**kwargs)
        kwargs.pop("data_source", None)
        for handler_name, handler in self._builder.handlers.items():
            logger.debug("Loading data into handler %s", handler_name)
            data = self._loader.result.get(handler_name)
            if not data:
                logger.warning("Data for handler %s not found in the loader result.", handler_name)
                continue

            logger.debug("Running handler %s", handler_name)
            handler.load(data=data, **kwargs).dump(**kwargs)
            logger.debug("Handler operation on %s completed", handler_name)

        logger.debug("Plugin execution on %s completed", self.__meta__.name)
        return self
