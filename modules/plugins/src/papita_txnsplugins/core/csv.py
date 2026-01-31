import logging
import sys
from argparse import ArgumentError, ArgumentParser
from typing import Any, Dict, Self, Type

from papita_txnsplugins.__meta__ import __authors__
from papita_txnsplugins.core.builders import ExcelContractBuilder
from pydantic import ValidationError

from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.enums import FallbackAction
from papita_txnsregistrar.contracts.loader import plugin
from papita_txnsregistrar.contracts.meta import PluginMetadata
from papita_txnsregistrar.contracts.plugin import PluginContract
from papita_txnsregistrar.loaders.file.impl import CSVFileLoader
from papita_txnsregistrar.utils.cli.abstract import AbstractCLIUtils

logger = logging.getLogger(__name__)


@plugin(
    meta=PluginMetadata(
        name="CSV File Plugin",
        version="1.0.0",
        feature_tags=["csv_file_plugin", "csv_file_loader", "csv_transactions", "csv_accounts"],
        description=(
            "Plugin for loading and processing CSV files. "
            "This plugin integrates the CSV file loader with the transaction tracking system, "
            "providing capabilities to load and process transaction data from CSV files. "
            "It utilizes the CSVFileLoader for data loading and a specified handler for "
            "transaction processing. The plugin acts as a bridge between CSV data sources "
            "and the transaction registration system."
        ),
        enabled=True,
        authors=__authors__,
    ),
)
class CSVFilePlugin(PluginContract[CSVFileLoader, ExcelContractBuilder]):
    """Plugin for handling CSV file transactions.

    This plugin integrates the CSV file loader with the transaction tracking system,
    providing capabilities to load and process transaction data from CSV files.
    It utilizes the CSVFileLoader for data loading and the ExcelContractBuilder
    for managing the registered handlers that process the loaded data.

    The plugin acts as a bridge between CSV data sources and the transaction
    registration system, coordinating the data flow from raw files to the
    structured model.

    Attributes:
        path: Path to the CSV file to be loaded.
        sheet: The name of the handler/sheet target for the CSV data.
    """

    path: str
    sheet: str

    def init(self, *, connector: Type[SQLDatabaseConnector], **kwargs) -> Self:
        """Initialize the plugin."""
        return super().init(connector=connector, path=self.path, sheet=self.sheet, **kwargs)

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
        name="CLI CSV File Plugin",
        version="1.0.0",
        feature_tags=["cli_csv_file_plugin", "cli_csv_file_loader", "cli_csv_transactions", "cli_csv_accounts"],
        description=(
            "CLI-enabled plugin for loading and processing CSV files. "
            "This plugin provides a command-line interface for the CSV file loader, allowing users to "
            "specify CSV file paths and sheet names via command-line arguments. It automatically "
            "parses CSV files, extracts transaction and account data, and integrates with the "
            "transaction registration system for data processing and storage."
        ),
        enabled=True,
        authors=__authors__,
    ),
)
class CLICSVFilePlugin(CSVFilePlugin, AbstractCLIUtils):
    """CLI-enabled plugin for handling CSV file transactions.

    This plugin extends CSVFilePlugin with command-line interface capabilities,
    allowing users to specify CSV file paths and sheet names via command-line
    arguments. It automatically parses command-line arguments, extracts the required
    parameters, and creates a configured plugin instance for processing.

    The plugin integrates with the transaction registrar's CLI system through the
    AbstractCLIUtils interface, enabling it to be discovered and executed via the
    main CLI utilities. It provides a user-friendly command-line interface for loading
    and processing transaction data from CSV files without requiring programmatic
    configuration.

    The plugin workflow follows the standard plugin lifecycle:
    1. Load - Parse CLI arguments and create plugin instance
    2. Init - Perform initialization tasks
    3. Start - Begin data loading and processing
    4. Stop - Terminate operation gracefully

    Attributes:
        _loader (CSVFileLoader): Instance that loads and parses CSV files.
        _builder (ExcelContractBuilder): Builder containing registered handlers for
            processing data.

    Note:
        This plugin requires command-line arguments to be provided either through
        sys.argv or via the 'args' parameter in kwargs. The required arguments are:
        - path (str): Path to the CSV file (required)
        - sheet (str | None): Sheet name to select as target (optional)
    """

    @classmethod
    def parse_cli_args(cls, **kwargs) -> Dict[str, Any]:
        """Build the argument parser for the plugin."""
        parser = ArgumentParser(description=cls.__doc__)
        parser.add_argument(
            "-p",
            "--path",
            "--csv-file-path",
            dest="path",
            help="(/path/to/file) CSV file.",
            type=str,
            required=True,
        )
        parser.add_argument(
            "--sheet",
            "--handler",
            dest="sheet",
            help="Handler name to select as target. Name of the handler that will be used to process the data.",
            required=True,
        )
        parsed_args, _ = parser.parse_known_args(kwargs.pop("args", None) or sys.argv)
        return vars(parsed_args)

    @classmethod
    def load(cls, **kwargs) -> Self:
        """Load the plugin using Pydantic's model construction with CLI argument parsing.

        This method creates a new plugin instance by parsing command-line arguments
        and using Pydantic's model_validate method to directly initialize the model
        fields without additional validation.

        The method sets up an ArgumentParser to parse CLI arguments for the CSV file
        path and handler name. It extracts these arguments from either the 'args'
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
