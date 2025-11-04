"""
Excel file plugin module for transaction registration.
This module provides a plugin for loading and processing transaction data from Excel files.
It integrates the Excel file loader with the transaction tracking system, enabling the
loading, processing, and registration of transaction data from Excel spreadsheets.
"""

import logging

# from typing import Dict, Self, Tuple, Type
from argparse import ArgumentError, ArgumentParser
from typing import Self

from papita_txnsregistrar_plugins.core.builders import ExcelContractBuilder
from pydantic import ValidationError

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
        plugin = cls.model_validate(kwargs)
        return plugin.init(**kwargs)

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
        name="cli_excel_loader_plugin",
        version="1.0.0",
        feature_tags=["cli_excel_file_loader", "cli_excel_transactions", "cli_excel_accounts"],
        dependencies=[ExcelFilePlugin],
        description="Loading transactions and accounts from Excel files.",
        enabled=True,
    ),
)
class CLIExcelFilePlugin(ExcelFilePlugin):

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
        parser = ArgumentParser(description=cls.__doc__, parents=kwargs.get("args_parent", []))
        parser.add_argument(
            "--path", "--excel-file-path", dest="path", help="(/path/to/file) Excel file.", type=str, required=True
        )
        parser.add_argument(
            "--sheet",
            dest="sheet",
            help="Sheet name to select as target.",
            required=False,
            default=None,
        )
        args, _ = parser.parse_known_args(kwargs.get("args"))
        return super().load(**(kwargs | vars(args)))

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
            # Parse CLI arguments just like in the load method
            parser = ArgumentParser(description=cls.__doc__, parents=kwargs.get("args_parent", []))
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

            # Parse known args from the CLI arguments
            args, unknown = parser.parse_known_args(kwargs.get("args", []))
            if unknown:
                logger.warning("Unknown arguments ignored: %s", unknown)

            # Extract the parsed arguments
            parsed_kwargs = vars(args)
            path = parsed_kwargs.get("path")
            sheet = parsed_kwargs.get("sheet")

            # Merge parsed args with any other provided kwargs
            combined_kwargs = kwargs.copy()
            combined_kwargs.update(parsed_kwargs)

            # Call the parent class's load method to create and validate the instance
            return super().load(path=path, sheet=sheet, **combined_kwargs)

        except ArgumentError as arg_err:
            logger.error("CLI argument error: %s", str(arg_err))
            print(f"Error: {str(arg_err)}")
            raise SystemExit(1) from arg_err
        except KeyError as kerr:
            message = f"Missing required argument: {str(kerr)}"
            logger.error("CLI error: %s", message)
            print(f"Error: {message}")
            raise SystemExit(2) from kerr
        except ValidationError as verr:
            message = f"Invalid argument format: {str(verr)}"
            logger.error("CLI validation error: %s", message)
            print(f"Error: {message}")
            raise SystemExit(3) from verr
        except Exception as err:
            message = f"Failed to load plugin: {str(err)}"
            logger.error("CLI error: %s", message)
            print(f"Error: {message}")
            raise SystemExit(4) from err
