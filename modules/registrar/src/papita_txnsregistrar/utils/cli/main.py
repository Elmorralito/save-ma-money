"""Main CLI utilities for the transaction registrar system.

This module provides the primary command-line interface utilities for the transaction registrar,
enabling plugin discovery, database connector management, and argument parsing. The MainCLIUtils
class serves as the entry point for CLI operations, handling plugin loading, module discovery,
and configuration of database connections.

The module supports dynamic plugin discovery from specified modules, fuzzy matching for plugin
names, and flexible database connector configuration. It integrates with the plugin registry
system to locate and instantiate plugins that support CLI operations.

Classes:
    HelpAction: Custom argparse action that displays comprehensive help including plugin and
                connector wrapper documentation.
    MainCLIUtils: Main CLI utility class that handles plugin discovery, connector setup, and
                  argument parsing for the registrar system.
"""

import contextlib
import importlib.resources as importlib_resources
import logging
import sys
import traceback
from argparse import Action, ArgumentParser
from typing import Annotated, Any, Dict, List, Self, Type

from pydantic import Field, model_validator

from papita_txnsmodel import LIB_NAME as MODEL_LIB_NAME
from papita_txnsmodel import __version__ as MODEL_VERSION
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.services.base import OnUpsertConflictDo
from papita_txnsmodel.utils.classutils import ClassDiscovery
from papita_txnsmodel.utils.configutils import configure_logger
from papita_txnsmodel.utils.enums import FallbackAction
from papita_txnsregistrar import LIB_NAME as REGISTRAR_LIB_NAME
from papita_txnsregistrar import __version__ as REGISTRAR_VERSION
from papita_txnsregistrar.contracts.loader import load_plugin
from papita_txnsregistrar.contracts.plugin import PluginContract

from .abstract import AbstractCLIUtils
from .connector import BaseCLIConnectorWrapper, CLIDefaultConnectorWrapper

DEFAULT_LOGGER_CONFIG_PATH: str = str(
    importlib_resources.files(f"{REGISTRAR_LIB_NAME}.configs").joinpath("logger.yaml")
)

logger = logging.getLogger(REGISTRAR_LIB_NAME)


class HelpAction(Action):
    """Custom argparse action that displays comprehensive help including plugin-specific help.

    This action extends the standard argparse help action to include plugin-specific help
    information when a plugin is provided as an argument. It first displays the standard
    CLI help, then attempts to load the specified plugin and display its help information.

    Attributes:
        option_strings: List of command-line option strings that trigger this action.
        dest: The name of the attribute to hold the created object(s).
        default: The value produced if the argument is absent.
        type: The type to which the command-line argument should be converted.
        choices: A container of the allowable values for the argument.
        required: Whether the action option must be provided.
        help: A brief description of what the option does.
        metavar: A name for the argument in usage messages.
    """

    def __init__(self, option_strings, dest="help", default=None, help=None):  # pylint: disable=redefined-builtin
        super().__init__(option_strings=option_strings, dest=dest, default=default, nargs=0, help=help)

    def __call__(
        self, parser, namespace, values, option_string=None
    ):  # pylint: disable=too-many-branches,too-many-locals,too-many-statements
        parser.print_help()

        plugin_name = None
        modules = []
        try:
            args_to_parse = getattr(parser, "_argv", None)
            if args_to_parse is None:
                args_to_parse = sys.argv[1:] if len(sys.argv) > 1 else []

            args_to_parse = [arg for arg in args_to_parse if arg not in ("-h", "--help")]

            if args_to_parse:
                positional_args = []
                skip_next = False
                for i, arg in enumerate(args_to_parse):
                    if skip_next:
                        skip_next = False
                        continue
                    if arg.startswith("-"):
                        # Check if this option takes a value
                        if arg in ["-m", "--module", "--mod"] and i + 1 < len(args_to_parse):
                            module_arg = args_to_parse[i + 1]
                            modules = [m.strip() for m in module_arg.split(",")]
                            skip_next = True
                        continue
                    positional_args.append(arg)

                if len(positional_args) > 1:
                    plugin_name = positional_args[0]
                elif len(positional_args) > 0:
                    potential_plugin = positional_args[0]
                    if potential_plugin and not potential_plugin.startswith("-"):
                        plugin_name = potential_plugin
        except Exception:
            print(f"Error extracting plugin name from args:\n{traceback.format_exc()}")
            plugin_name = None

        print(f"Plugin name: {plugin_name}")
        if plugin_name:
            try:
                connector_wrapper = ".".join(filter(None, ClassDiscovery.decompose_class(CLIDefaultConnectorWrapper)))

                instance = MainCLIUtils.model_validate(
                    {
                        "plugin": plugin_name,
                        "modules": modules,
                        "connector_wrapper": connector_wrapper,
                        "case_sensitive": True,
                        "strict_exact": False,
                        "fuzzy_threshold": 95,
                        "safe_mode": False,
                    }
                )
                instance._build_model()
                instance._show_plugin_help()

            except Exception:
                print(f"Could not load plugin for help:\n{traceback.format_exc()}")
                print(f"\nNote: Could not load plugin '{plugin_name}' for help display.")
                print("This may be due to:")
                print("  - Plugin not found in the specified modules")
                print("  - Plugin requires additional configuration\n")

        parser.exit()


class MainCLIUtils(AbstractCLIUtils):
    """Main CLI utility class for the transaction registrar system.

    This class provides the primary command-line interface for discovering and loading plugins,
    configuring database connectors, and managing CLI operations. It handles argument parsing,
    plugin discovery from specified modules, and dynamic connector wrapper selection.

    The class uses Pydantic for validation and configuration management, supporting flexible
    plugin matching through case-sensitive, exact, and fuzzy matching strategies. It integrates
    with the plugin registry to discover and instantiate plugins that support CLI operations.

    Attributes:
        plugin: The plugin name or PluginContract instance to be used. Can be specified as a
                string (for discovery) or a PluginContract instance.
        modules: List of module names to search for plugins. Defaults to an empty list.
                 Multiple modules can be specified, separated by commas.
        connector_wrapper: Optional database connector wrapper class or string identifier.
                          Used to wrap SQLDatabaseConnector for CLI integration.
        connector: The resolved SQLDatabaseConnector instance, set during model validation.
                   This is populated automatically from the connector_wrapper.
        case_sensitive: Enable case-sensitive matching for plugin names and tags. Defaults to True.
        strict_exact: Enable strict exact matching for plugin names and tags. When enabled,
                      only exact matches are considered. Defaults to False.
        fuzzy_threshold: Threshold for fuzzy matching (0-100). Higher values require closer
                         matches. Defaults to 90.
        safe_mode: Enable safe mode to prevent execution of potentially harmful operations.
                   Defaults to False.

    Note:
        The plugin attribute is resolved during model validation. If a string is provided,
        it will be looked up in the registry using the specified matching criteria.
    """

    plugin: Annotated[
        str | Type[PluginContract], Field(..., alias="plugin", description="Specify the name of the plugin to be used.")
    ]
    modules: List[str] = Field(
        default_factory=list,
        alias="modules",
        description="Specify the module(s) to be used. This can include multiple modules separated by commas.",
    )
    connector_wrapper: Annotated[
        str | Type[BaseCLIConnectorWrapper],
        Field(None, alias="connector_wrapper", description="An optional database connector wrapper instance."),
    ]
    connector: Annotated[
        Type[SQLDatabaseConnector] | None,
        Field(None, alias="connector", description="An optional database connector wrapper instance."),
    ] = None
    case_sensitive: Annotated[
        bool,
        Field(..., alias="case_sensitive", description="Enable case-sensitive matching for plugin names and tags."),
    ] = True
    strict_exact: Annotated[
        bool, Field(..., alias="strict_exact", description="Enable strict exact matching for plugin names and tags.")
    ] = False
    fuzzy_threshold: Annotated[
        int,
        Field(
            ...,
            ge=0,
            le=100,
            alias="fuzzy_threshold",
            description="Set the threshold for fuzzy matching (0-100). Higher values require closer matches.",
        ),
    ] = 95
    safe_mode: Annotated[
        bool,
        Field(
            ...,
            alias="safe_mode",
            description="Enable safe mode to prevent execution of potentially harmful operations.",
        ),
    ] = False

    on_conflict_do: Annotated[
        OnUpsertConflictDo,
        Field(
            ..., alias="on_conflict_do", description="Specify the on conflict do action to take when a conflict occurs."
        ),
    ] = OnUpsertConflictDo.UPDATE

    on_failure_do: Annotated[
        FallbackAction,
        Field(..., alias="on_failure_do", description="Specify the fallback action to take when an error occurs."),
    ] = FallbackAction.RAISE

    @model_validator(mode="after")
    def _build_model(self) -> Self:
        """Build and validate the model after field assignment.

        This method is called automatically by Pydantic after field validation. It performs
        post-initialization tasks including: normalizing module names, discovering and loading
        the connector wrapper, discovering plugins from specified modules, resolving the plugin
        class, and validating that the plugin supports CLI utilities.

        The method processes comma-separated module names, searches for connector wrappers
        across modules, and uses the registry to locate the specified plugin using the configured
        matching criteria (case-sensitive, exact, or fuzzy matching).

        Returns:
            Self: The validated and configured instance with connector and plugin attributes
                  populated.

        Raises:
            RuntimeError: If any error occurs during model building, including connector wrapper
                          discovery failures, plugin not found, or plugin incompatibility.
                          The original exception is chained as the cause.
            ValueError: If no valid connector wrapper could be found, or if the specified
                        plugin could not be found in the registry.
            TypeError: If the specified plugin does not support CLI utilities (i.e., is not
                       a subclass of AbstractCLIUtils).

        Note:
            This method modifies the instance in place, setting the connector and plugin
            attributes based on the provided configuration.
        """
        with contextlib.suppress(AttributeError):
            logger.debug("Cleaning modules: %s", self.modules)
            self.modules = [mod.strip() for mods in self.modules for mod in mods.strip().split(",")]

        mod_, class_ = ClassDiscovery.decompose_class(self.connector_wrapper)
        if not class_:
            raise ValueError("No valid connector wrapper could be found.")

        if not mod_:
            self.connector_wrapper = f'{__name__.replace("main", "connector")}.{class_}'

        try:
            if isinstance(self.plugin, str):
                logger.info("Loading plugin from registry: %s within modules: %s", self.plugin, self.modules)
                self.plugin = self._load_plugin_class(
                    plugin_name=self.plugin,
                    modules=self.modules,
                    case_sensitive=self.case_sensitive,
                    strict_exact=self.strict_exact,
                    fuzzy_threshold=self.fuzzy_threshold,
                )

            logger.info("Using plugin: %s", self.plugin)
            logger.info("Loading connector wrapper as: %s", self.connector_wrapper)
            connector_wrapper = next(
                filter(
                    None,
                    [
                        ClassDiscovery.select(
                            self.connector_wrapper,
                            class_type=BaseCLIConnectorWrapper,
                            default_module=mod_,
                            debug=True,
                        )
                        for mod_ in self.modules
                    ],
                ),
                None,
            )
            if not connector_wrapper:
                raise ValueError("No valid connector wrapper could be found.")

            logger.info("Using connector wrapper: %s", connector_wrapper)
            self.connector = connector_wrapper.load().connector
            logger.info("Using connector: %s", self.connector)
        except Exception as err:
            logger.exception("Error building model: %s", err)
            raise RuntimeError(f"Error building model: {err}") from err

        logger.debug("Plugin '%s' supports CLI utilities.", self.plugin.meta().name)
        return self

    @classmethod
    def _load_plugin_class(cls, plugin_name: str, modules: List[str], **kwargs) -> Type[AbstractCLIUtils]:
        """Load and return the plugin class without creating an instance.

        This method discovers and loads a plugin class from the specified modules using the
        plugin registry. It normalizes module names, performs plugin discovery, and validates
        that the found plugin supports CLI utilities. The plugin class is returned without
        instantiation, allowing for further inspection or delayed instantiation.

        Args:
            plugin_name: The name or identifier of the plugin to load. This will be used
                         for registry lookup using the specified matching criteria.
            modules: List of module names to search for plugins. Module names can be
                     comma-separated strings, which will be automatically split and normalized.
            **kwargs: Additional keyword arguments for plugin matching. Valid keys include:
                      - case_sensitive (bool): Enable case-sensitive matching. Defaults to True.
                      - strict_exact (bool): Enable strict exact matching. Defaults to False.
                      - fuzzy_threshold (int): Threshold for fuzzy matching (0-100).
                        Defaults to 90.

        Returns:
            Type[AbstractCLIUtils]: The plugin class that supports CLI utilities.

        Raises:
            RuntimeError: If any error occurs during plugin loading, including discovery
                          failures or validation errors. The original exception is chained
                          as the cause.
            ValueError: If the specified plugin could not be found in the registry or is
                        not a class.
            TypeError: If the specified plugin does not support CLI utilities (i.e., is not
                       a subclass of AbstractCLIUtils).

        Note:
            This method performs plugin discovery but does not instantiate the plugin. Use
            this method when you need the plugin class for inspection or to create instances
            later.
        """
        plugin_class = load_plugin(plugin_name, modules, **kwargs)
        if not issubclass(plugin_class, AbstractCLIUtils):
            raise TypeError(
                f"The specified plugin '{plugin_name}({plugin_class.__class__.__name__})' does not support CLI "
                "utilities."
            )

        return plugin_class

    @classmethod
    def _setup_logger(cls, args: Dict[str, Any]) -> None:
        """Configure logging based on command-line arguments.

        This method sets up logging for the registrar system and its components based on
        the verbosity level and log configuration file specified in the command-line arguments.
        It configures loggers for the main registrar library, plugin system, and model library.

        The verbosity level is determined by the count of -v flags:
        - No -v flags: WARNING level
        - -v: INFO level
        - -vv: DEBUG level
        - -vvv or more: NOTSET level (maximum verbosity)

        Args:
            args: The parsed command-line arguments dictionary. Must contain:
                  - verbose (int): Integer count of verbosity flags (default: 0)
                  - log_config (str): Path to the logging configuration file (YAML format)

        Note:
            This method configures three separate loggers:
            - The main registrar library logger
            - The plugin system logger
            - The model library logger

            All loggers use the same configuration file and verbosity level for consistency.
        """
        verbose = args.get("verbose", 0)
        if verbose == 1:
            level = logging.INFO
        elif verbose == 2:
            level = logging.DEBUG
        elif verbose >= 3:
            level = logging.NOTSET  # Maximum verbosity
        else:
            level = logging.WARNING

        configure_logger(
            logger_name=REGISTRAR_LIB_NAME, config=args.get("log_config", DEFAULT_LOGGER_CONFIG_PATH), level=level
        )
        configure_logger(
            logger_name=f"{REGISTRAR_LIB_NAME}.plugins",
            config=args.get("log_config", DEFAULT_LOGGER_CONFIG_PATH),
            level=level,
        )
        configure_logger(
            logger_name=MODEL_LIB_NAME, config=args.get("log_config", DEFAULT_LOGGER_CONFIG_PATH), level=level
        )
        for logger_name in (REGISTRAR_LIB_NAME, f"{REGISTRAR_LIB_NAME}.plugins", MODEL_LIB_NAME):
            logger_instance = logging.getLogger(logger_name)
            logger_instance.setLevel(level)
            for handler in logger_instance.handlers:
                handler.setLevel(level)

    @classmethod
    def parse_cli_args(cls, **kwargs) -> Dict[str, Any]:
        """Build the argument parser for the MainCLIUtils class."""
        parser = ArgumentParser(add_help=False)
        parser.add_argument(
            "script",
            help="The script to run. Not used at all",
            type=str,
            metavar="<script>",
        )
        parser.add_argument(
            cls.model_fields["plugin"].alias,
            help=cls.model_fields["plugin"].description,
            type=str,
        )
        parser.add_argument(
            "-m",
            "--mod",
            "--module",
            dest=cls.model_fields["modules"].alias,
            help=cls.model_fields["modules"].description,
            type=str,
            required=False,
            nargs="*",
            default=[],
        )
        parser.add_argument(
            "--connector-wrapper",
            dest=cls.model_fields["connector_wrapper"].alias,
            help=cls.model_fields["connector_wrapper"].description,
            type=str,
            required=False,
            default=".".join(filter(None, ClassDiscovery.decompose_class(CLIDefaultConnectorWrapper))),
        )
        parser.add_argument(
            "--case-sensitive",
            dest=cls.model_fields["case_sensitive"].alias,
            help=cls.model_fields["case_sensitive"].description,
            action="store_false",
            default=cls.model_fields["case_sensitive"].default,
        )
        parser.add_argument(
            "--strict-exact",
            dest=cls.model_fields["strict_exact"].alias,
            help=cls.model_fields["strict_exact"].description,
            action="store_true",
            default=cls.model_fields["strict_exact"].default,
        )
        parser.add_argument(
            "--fuzzy-threshold",
            dest=cls.model_fields["fuzzy_threshold"].alias,
            help=cls.model_fields["fuzzy_threshold"].description,
            type=int,
            default=cls.model_fields["fuzzy_threshold"].default,
        )
        parser.add_argument(
            "--safe-mode",
            dest=cls.model_fields["safe_mode"].alias,
            help=cls.model_fields["safe_mode"].description,
            action="store_true",
            default=cls.model_fields["safe_mode"].default,
        )
        parser.add_argument(
            "--version",
            action="version",
            version=(
                f"Papita Transactions Registrar ({REGISTRAR_LIB_NAME}=={REGISTRAR_VERSION}) | "
                f"Papita Transactions Model ({MODEL_LIB_NAME}=={MODEL_VERSION}) | "
                f"by Papita Software under MIT License"
            ),
        )
        # Replace default help action with custom one that shows plugin help
        parser.add_argument(
            "-h",
            "--help",
            action=HelpAction,
            help="Show this help message and exit. If a plugin is specified, also displays plugin-specific help.",
        )
        parser.add_argument(
            "-v", "--verbose", action="count", default=0, help="Increase output verbosity (e.g., -v, -vv, -vvv)"
        )
        parser.add_argument(
            "--log-config",
            dest="log_config",
            help="Specify the path to the logging configuration file.",
            type=str,
            default=DEFAULT_LOGGER_CONFIG_PATH,
        )
        parser.add_argument(
            "--on-conflict-do",
            dest="on_conflict_do",
            help="Specify the on conflict do action to take when a conflict occurs.",
            type=str,
            choices=[x.value for x in OnUpsertConflictDo],
            default=cls.model_fields["on_conflict_do"].default.value,
        )
        parser.add_argument(
            "--on-failure-do",
            dest="on_failure_do",
            help="Specify the fallback action to take when an error occurs.",
            type=str,
            choices=[x.value for x in FallbackAction],
            default=cls.model_fields["on_failure_do"].default.value,
        )
        args_ = kwargs.get("args") or sys.argv
        if not isinstance(args_, list):
            raise ValueError("args must be   a list of strings or None")

        parsed_args, _ = parser.parse_known_args(args=args_)
        return vars(parsed_args)

    @classmethod
    def load(cls, **kwargs) -> Self:
        """Load and configure the MainCLIUtils instance from command-line arguments.

        This is the primary entry point for creating a MainCLIUtils instance. It sets up
        an argument parser with all CLI options, parses command-line arguments, configures
        logging, and returns a validated instance ready for use.

        The method supports a comprehensive set of command-line arguments including:
        plugin selection, module specification, connector configuration, matching options,
        verbosity control, and logging configuration. It also provides a custom help action
        that displays both main CLI help and plugin-specific help.

        Args:
            **kwargs: Optional keyword arguments. Valid keys include:
                     - args (List[str]): List of command-line argument strings. If not
                       provided, sys.argv is used. Must be a list of strings.

        Returns:
            Self: A fully configured MainCLIUtils instance with all fields validated and
                  populated, including the resolved plugin class and database connector.

        Raises:
            ValueError: If the args parameter is provided but is not a list of strings.

        Note:
            This method performs the following operations:
            1. Creates an argument parser with all CLI options
            2. Sets up a custom help action that includes plugin-specific help
            3. Parses command-line arguments
            4. Configures logging based on verbosity and log config
            5. Validates and builds the model instance

            The plugin and connector are resolved during model validation, which occurs
            when model_validate is called with the parsed arguments.
        """
        parsed_args = cls.parse_cli_args(**kwargs)
        cls._setup_logger(args=parsed_args)
        return cls.model_validate(parsed_args)

    def _show_plugin_help(self) -> Self:
        """Display comprehensive help information for the loaded plugin.

        This method displays formatted help information about the currently loaded plugin,
        including its metadata (name, version, description, feature tags), class documentation,
        and any additional information available from the plugin's metadata.

        The help is formatted in a user-friendly way, showing:
        - Plugin name and version
        - Description
        - Feature tags
        - Enabled status

        Returns:
            Self: Returns self for method chaining.

        Note:
            This method should be called after the plugin has been loaded (i.e., after
            `load()` or `run()` has been called). If the plugin is not loaded, it will
            attempt to use the plugin class directly.
        """
        try:
            plugin_class = self.plugin
            print(f"Plugin class: {plugin_class}")
            if hasattr(self, "_plugin_instance") and self._plugin_instance is not None:
                plugin_class = type(self._plugin_instance)

            if hasattr(plugin_class, "meta"):
                metadata = plugin_class.meta()
            else:
                print("WARNING: Plugin does not have a meta() method. Limited help available.")
                metadata = None

            if metadata:
                print(f"\nPlugin Name: {metadata.name}")
                print(f"Version: {metadata.version}")
                print(f"Enabled: {metadata.enabled}")

                if metadata.description:
                    print("\nDescription:")
                    print(metadata.description)

                if metadata.feature_tags:
                    print("\nFeature Tags:")
                    for tag in metadata.feature_tags:
                        print(f"  - {tag}")

            print(f"\nPlugin Class: {'.'.join(filter(None, ClassDiscovery.decompose_class(plugin_class)))}")
            if metadata.enabled:
                plugin_class.load()
            else:
                print("\nPlugin is not enabled. Please enable it in the configuration.")

        except Exception as err:
            logger.exception("Error displaying plugin help: %s", err)
            print(f"\nError displaying plugin help: {err}\n")

        return self

    def run(self) -> Self:
        """Execute the plugin instance lifecycle operations.

        This method builds, initializes, and starts the plugin instance based on the configured
        plugin. It handles both safe and normal loading modes, creating the plugin instance,
        performing initialization, and starting the plugin's main operations.

        The method follows the plugin lifecycle sequence:
        1. Load - Create the plugin instance using safe_load() or load() depending on safe_mode
        2. Init - Perform initialization tasks via init()
        3. Start - Begin active operation via start()

        Returns:
            Self: Returns self for method chaining.

        Note:
            The plugin instance is stored in the _plugin_instance attribute for later use by
            the stop() method. If safe_mode is enabled, safe_load() is used instead of load()
            to prevent execution of potentially harmful operations.
        """
        plugin_name = self.plugin.meta().name
        if self.safe_mode:
            logger.info("Safely building plugin instance from plugin: %s", plugin_name)
            self._plugin_instance = self.plugin.safe_load(
                on_failure_do=self.on_failure_do, on_conflict_do=self.on_conflict_do
            )
        else:
            logger.info("Building plugin instance from plugin: %s", plugin_name)
            self._plugin_instance = self.plugin.load(
                on_failure_do=self.on_failure_do, on_conflict_do=self.on_conflict_do
            )

        logger.info("Plugin instance of plugin '%s' built and initialized.", plugin_name)
        logger.info("Starting plugin instance from plugin '%s'...", plugin_name)
        self._plugin_instance.init(connector=self.connector, on_conflict_do=self.on_conflict_do).start()
        return self

    def stop(self) -> Self:
        """Shutdown the CLI utility and release all resources.

        This method performs graceful shutdown of the CLI utility by stopping the plugin instance
        (if it exists and has a stop method) and closing the database connector. All operations
        are wrapped in exception suppression to ensure cleanup continues even if individual
        shutdown steps fail.

        The method performs the following cleanup operations:
        1. Stop the plugin instance if it exists and supports the stop() method
        2. Close the database connector if it exists

        Returns:
            Self: Returns self for method chaining.

        Note:
            This method uses contextlib.suppress(Exception) to ensure that errors during
            shutdown do not prevent complete cleanup. All exceptions are silently suppressed
            to allow the shutdown process to complete as much as possible.
        """
        with contextlib.suppress(Exception):
            # Call stop() on the plugin instance if it exists
            if hasattr(self, "_plugin_instance") and self._plugin_instance is not None:
                if hasattr(self._plugin_instance, "stop"):
                    plugin_name = self.plugin.meta().name
                    logger.info("Stopping plugin instance from plugin '%s'...", plugin_name)
                    self._plugin_instance.stop()
                    logger.info("Plugin instance from plugin '%s' stopped.", plugin_name)

            if self.connector:
                logger.info("Closing database connector...")
                self.connector.close()

        logger.info("CLI utilities stopped successfully.")
        return self
