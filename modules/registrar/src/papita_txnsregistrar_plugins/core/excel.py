"""Excel file plugin module for transaction registration.

This module provides plugins for loading and processing transaction data from Excel files.
It integrates the Excel file loader with the transaction tracking system, enabling the
loading, processing, and registration of transaction data from Excel spreadsheets.

The module defines two main plugin classes:
    - ExcelFilePlugin: Base plugin for programmatic Excel file processing that integrates
      the ExcelFileLoader with the transaction registration system.
    - CLIExcelFilePlugin: CLI-enabled plugin that extends ExcelFilePlugin with
      command-line argument parsing capabilities, allowing users to specify Excel file
      paths and sheet names via command-line arguments.

Both plugins utilize the ExcelFileLoader for data loading and ExcelContractBuilder for
managing registered handlers that process the loaded data. The plugins act as bridges
between Excel data sources and the transaction registration system, automatically
distributing loaded data to appropriate handlers for processing and storage.
"""

import logging
import sys
from argparse import ArgumentError, ArgumentParser
from typing import Any, Dict, Self, Type

from papita_txnsregistrar_plugins.core.builders import ExcelContractBuilder
from pydantic import ValidationError

from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.classutils import FallbackAction
from papita_txnsregistrar import LIB_NAME
from papita_txnsregistrar.contracts.loader import plugin
from papita_txnsregistrar.contracts.meta import PluginMetadata
from papita_txnsregistrar.contracts.plugin import PluginContract
from papita_txnsregistrar.loaders.file.impl import ExcelFileLoader
from papita_txnsregistrar.utils.cli.abstract import AbstractCLIUtils

logger = logging.getLogger(f"{LIB_NAME}.plugin.core.excel")


@plugin(
    meta=PluginMetadata(
        name="Excel File Loader Plugin",
        version="1.0.0",
        feature_tags=["excel_file_loader", "excel_transactions", "excel_accounts"],
        # TODO: Add dependencies back in when we have a way to validate them, and define a better use for this field
        # dependencies=[ExcelFileLoader, ExcelContractBuilder],
        description=(
            "Plugin for loading and processing transactions and accounts from Excel files. "
            "This plugin integrates the Excel file loader with the transaction tracking system, "
            "providing capabilities to load and process transaction data from Excel files. "
            "It utilizes the ExcelFileLoader for data loading and a specified handler for "
            "transaction processing. The plugin acts as a bridge between Excel data sources "
            "and the transaction registration system."
        ),
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

    path: str
    sheet: str | None = None

    def init(self, *, connector: Type[SQLDatabaseConnector], **kwargs) -> Self:
        """Initialize the plugin."""
        return super().init(connector=connector, path=self.path, sheet=self.sheet, **kwargs)

    def start(self, **kwargs) -> Self:
        """Start the plugin execution process.

        Initiates the plugin's data loading and processing workflow by calling the parent
        class's start method, then distributing loaded data to registered handlers and
        executing their load and dump operations sequentially.

        The method performs the following steps:
        1. Calls the parent class's start method to initialize the plugin
        2. Retrieves data for each registered handler from the loader results
        3. Passes the appropriate data to each handler for processing
        4. Executes each handler's load and dump operations sequentially

        Args:
            **kwargs: Additional keyword arguments passed to handlers. These arguments
                are forwarded to the handlers' load and dump methods, except for
                'data_source' which is removed before passing.

        Returns:
            Self: The plugin instance for method chaining.

        Note:
            If data for a handler is not found in the loader results, a warning is
            logged and that handler is skipped. The method continues processing
            remaining handlers.
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
        kwargs_ = {
            "on_failure_do": kwargs.pop("on_failure_do", FallbackAction.RAISE),
            "path": kwargs.pop("path"),
            "sheet": kwargs.pop("sheet", None),
            **kwargs,
        }
        return cls.model_validate(kwargs_)

    @classmethod
    def safe_load(cls, **kwargs) -> Self:
        """Safely load the plugin with full validation.

        This method creates a new plugin instance using Pydantic's model_validate method,
        which performs complete validation of input data according to the model schema.
        This provides additional safety compared to the standard load method.

        The method expects 'path' and optionally 'sheet' parameters in kwargs. It extracts
        these parameters and passes them to the load method for instance creation.

        Args:
            **kwargs: Parameters for loading the plugin, such as configuration options
                or dependencies. Must include 'path' (str) for the Excel file path, and
                optionally 'sheet' (str | None) for the sheet name.

        Returns:
            Self: A new validated instance of the plugin.

        Raises:
            RuntimeError: If required arguments are missing or malformed. The original
                exception (KeyError or ValidationError) is chained as the cause.
        """
        try:
            path = kwargs.pop("path")
            sheet = kwargs.pop("sheet", None)
            return cls.load(path=path, sheet=sheet, **kwargs)
        except KeyError as kerr:
            message = "The arguments were not properly provided."
            err = kerr
        except ValidationError as verr:
            message = "The arguments were malformed."
            err = verr

        logger.error(message)
        raise RuntimeError(message) from err


@plugin(
    meta=PluginMetadata(
        name="CLI Excel File Loader Plugin",
        version="1.0.0",
        feature_tags=[
            "cli_excel_loader_plugin",
            "cli_excel_file_loader",
            "cli_excel_transactions",
            "cli_excel_accounts",
        ],
        # TODO: Add dependencies back in when we have a way to validate them, and define a better use for this field
        # dependencies=[ExcelFilePlugin],
        description=(
            "CLI-enabled plugin for loading and processing transactions and accounts from Excel files. "
            "This plugin provides a command-line interface for the Excel file loader, allowing users to "
            "specify Excel file paths and sheet names via command-line arguments. It automatically "
            "parses Excel spreadsheets, extracts transaction and account data, and integrates with the "
            "transaction registration system for data processing and storage."
        ),
        enabled=True,
    ),
)
class CLIExcelFilePlugin(ExcelFilePlugin, AbstractCLIUtils):
    """CLI-enabled plugin for handling Excel file transactions.

    This plugin extends ExcelFilePlugin with command-line interface capabilities,
    allowing users to specify Excel file paths and sheet names via command-line
    arguments. It automatically parses command-line arguments, extracts the required
    parameters, and creates a configured plugin instance for processing.

    The plugin integrates with the transaction registrar's CLI system through the
    AbstractCLIUtils interface, enabling it to be discovered and executed via the
    main CLI utilities. It provides a user-friendly command-line interface for loading
    and processing transaction data from Excel files without requiring programmatic
    configuration.

    The plugin workflow follows the standard plugin lifecycle:
    1. Load - Parse CLI arguments and create plugin instance
    2. Init - Perform initialization tasks
    3. Start - Begin data loading and processing
    4. Stop - Terminate operation gracefully

    Attributes:
        _loader (ExcelFileLoader): Instance that loads and parses Excel files.
        _builder (ExcelContractBuilder): Builder containing registered handlers for
            processing data.

    Note:
        This plugin requires command-line arguments to be provided either through
        sys.argv or via the 'args' parameter in kwargs. The required arguments are:
        - path (str): Path to the Excel file (required)
        - sheet (str | None): Sheet name to select as target (optional)
    """

    @classmethod
    def parse_cli_args(cls, **kwargs) -> Dict[str, Any]:
        """Build the argument parser for the plugin."""
        parser = ArgumentParser(description=cls.__doc__)
        parser.add_argument(
            "-p",
            "--path",
            "--excel-file-path",
            dest="path",
            help="(/path/to/file) Excel file.",
            type=str,
            required=True,
        )
        parser.add_argument(
            "--sheet",
            dest="sheet",
            help="Sheet name to select as target.",
            required=False,
            default=None,
        )
        parsed_args, _ = parser.parse_known_args(kwargs.pop("args", None) or sys.argv)
        return vars(parsed_args)

    @classmethod
    def load(cls, **kwargs) -> Self:
        """Load the plugin using Pydantic's model construction with CLI argument parsing.

        This method creates a new plugin instance by parsing command-line arguments
        and using Pydantic's model_validate method to directly initialize the model
        fields without additional validation.

        The method sets up an ArgumentParser to parse CLI arguments for the Excel file
        path and optional sheet name. It extracts these arguments from either the 'args'
        parameter in kwargs or from sys.argv, then merges them with any additional
        kwargs before creating the plugin instance.

        Args:
            **kwargs: Parameters for loading the plugin. May include:
                - args (List[str] | None): Command-line arguments to parse. If not
                  provided, sys.argv is used.
                - Additional configuration options or dependencies that will be passed
                  to the parent class's load method.

        Returns:
            Self: A new instance of the plugin initialized with parsed CLI arguments.

        Note:
            The method uses parse_known_args to allow unknown arguments to be passed
            through without raising errors. Unknown arguments are ignored.
        """
        args = cls.parse_cli_args(**kwargs)
        return super().load(**(kwargs | args))

    @classmethod
    def safe_load(cls, **kwargs) -> Self:
        """
        Safely load the plugin with full validation and CLI-friendly error handling.

        This method creates a new plugin instance with complete validation according
        to the model schema, specifically adapted for command-line interface usage.
        It parses command line arguments and provides user-friendly error messages.

        Args:
            **kwargs: Parameters for loading the plugin, such as CLI arguments.
                    Expected to contain 'args' with command line arguments.

        Returns:
            Self: A new validated instance of the plugin.

        Raises:
            SystemExit: If validation fails or arguments are missing, with
                    appropriate error message and exit code.
        """
        try:
            parsed_kwargs = cls.parse_cli_args(**kwargs)
            path = parsed_kwargs.pop("path")
            sheet = parsed_kwargs.pop("sheet")
            combined_kwargs = kwargs.copy()
            combined_kwargs.update(parsed_kwargs)
            return super().load(path=path, sheet=sheet, **combined_kwargs)

        except ArgumentError as arg_err:
            logger.error("CLI argument error: %s", str(arg_err))
            raise SystemExit(1) from arg_err
        except KeyError as kerr:
            message = f"Missing required argument: {str(kerr)}"
            logger.error("CLI error: %s", message)
            raise SystemExit(2) from kerr
        except ValidationError as verr:
            message = f"Invalid argument format: {str(verr)}"
            logger.error("CLI validation error: %s", message)
            raise SystemExit(3) from verr
        except Exception as err:
            message = f"Failed to load plugin: {str(err)}"
            logger.error("CLI error: %s", message)
            raise SystemExit(4) from err

    def run(self) -> Self:
        """Run the plugin."""
        return self

    def stop(self) -> Self:
        """Stop the plugin."""
        return self
