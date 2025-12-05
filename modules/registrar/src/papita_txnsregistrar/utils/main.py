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
import inspect
import logging
import sys
from argparse import ArgumentParser, Namespace
from typing import Annotated, List, Self, Type

from pydantic import Field, model_validator

from papita_txnsmodel import LIB_NAME as MODEL_LIB_NAME
from papita_txnsmodel import __version__ as MODEL_VERSION
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.classutils import ClassDiscovery
from papita_txnsmodel.utils.configutils import configure_logger
from papita_txnsregistrar import LIB_NAME as REGISTRAR_LIB_NAME
from papita_txnsregistrar import __version__ as REGISTRAR_VERSION
from papita_txnsregistrar.contracts.plugin import PluginContract
from papita_txnsregistrar.contracts.registry import Registry
from papita_txnsregistrar.utils import connector as connector_wrapper_module
from papita_txnsregistrar.utils.cli import AbstractCLIUtils

DEFAULT_LOGGER_CONFIG_PATH = str(importlib_resources.files(f"{REGISTRAR_LIB_NAME}.configs").joinpath("logger.yaml"))

logger = logging.getLogger(REGISTRAR_LIB_NAME)


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
        modules: List of module names to search for plugins. Defaults to
                 ["papita_txnsregistrar_plugins"]. Multiple modules can be specified, separated
                 by commas.
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
        default_factory=lambda: ["papita_txnsregistrar_plugins"],
        description="Specify the module(s) to be used. This can include multiple modules separated by commas.",
    )
    connector_wrapper: Annotated[
        str | Type[connector_wrapper_module.BaseCLIConnectorWrapper],
        Field(None, alias="connector_wrapper", description="An optional database connector wrapper instance."),
    ]
    connector: Annotated[
        Type[SQLDatabaseConnector] | None,
        Field(None, alias="connector", description="An optional database connector wrapper instance."),
    ] = None
    case_sensitive: Annotated[
        bool, Field(..., description="Enable case-sensitive matching for plugin names and tags.")
    ] = True
    strict_exact: Annotated[bool, Field(..., description="Enable strict exact matching for plugin names and tags.")] = (
        False
    )
    fuzzy_threshold: Annotated[
        int,
        Field(
            ...,
            ge=0,
            le=100,
            description="Set the threshold for fuzzy matching (0-100). Higher values require closer matches.",
        ),
    ] = 90
    safe_mode: Annotated[
        bool, Field(..., description="Enable safe mode to prevent execution of potentially harmful operations.")
    ] = False

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
            self.connector_wrapper = f"{connector_wrapper_module.__name__}.{class_}"

        try:
            if isinstance(self.plugin, str):
                logger.debug("Loading plugin from registry: %s with modules: %s", self.plugin, self.modules)
                self.plugin = self._load_plugin_class(
                    plugin_name=self.plugin,
                    modules=self.modules,
                    case_sensitive=self.case_sensitive,
                    strict_exact=self.strict_exact,
                    fuzzy_threshold=self.fuzzy_threshold,
                )

            logger.debug("Using plugin: %s", self.plugin)
            connector_wrapper = next(
                filter(
                    None,
                    [
                        ClassDiscovery.select(
                            self.connector_wrapper,
                            class_type=connector_wrapper_module.BaseCLIConnectorWrapper,
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

            logger.debug("Using connector wrapper: %s", connector_wrapper)
            logger.debug("Discovering plugin from modules: %s", self.modules)
            self.connector = connector_wrapper.load().connector
            logger.debug("Using connector: %s", self.connector)
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
        try:
            with contextlib.suppress(AttributeError):
                modules = [mod.strip() for mods in modules for mod in mods.strip().split(",")]

            logger.debug("Discovering plugin from modules: %s", modules)
            registry = Registry().discover(*modules, debug=True)
            logger.debug("Discovered plugins: %s")
            logger.debug("Getting plugin '%s' from registry", plugin_name)
            plugin = registry.get(
                label=plugin_name,
                case_sensitive=kwargs.get("case_sensitive", True),
                strict_exact=kwargs.get("strict_exact", False),
                fuzz_threshold=kwargs.get("fuzzy_threshold", 90),
            )
            if not plugin or not inspect.isclass(plugin):
                raise ValueError("The specified plugin could not be found.")

            if not issubclass(plugin, AbstractCLIUtils):
                raise TypeError("The specified plugin does not support CLI utilities.")

            return plugin
        except (ValueError, TypeError) as err:
            raise RuntimeError(f"Error loading plugin: {err}") from err
        except Exception as err:
            raise err

    @classmethod
    def _setup_logger(cls, args: Namespace) -> None:
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
            args: The parsed command-line arguments namespace. Must contain:
                  - verbose (int): Integer count of verbosity flags (default: 0)
                  - log_config (str): Path to the logging configuration file (YAML format)

        Note:
            This method configures three separate loggers:
            - The main registrar library logger
            - The plugin system logger
            - The model library logger

            All loggers use the same configuration file and verbosity level for consistency.
        """
        if args.verbose == 1:
            level = logging.INFO
        elif args.verbose == 2:
            level = logging.DEBUG
        elif args.verbose >= 3:
            level = logging.NOTSET  # Maximum verbosity
        else:
            level = logging.WARNING

        configure_logger(logger_name=REGISTRAR_LIB_NAME, config=args.log_config, level=level)
        configure_logger(logger_name=f"{REGISTRAR_LIB_NAME}_plugins", config=args.log_config, level=level)
        configure_logger(logger_name=MODEL_LIB_NAME, config=args.log_config, level=level)
        # Ensure the module logger also uses the configured level
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)

        logger.info("Logger setup with level '%s'", level)
        logger.debug("Logger setup with config '%s'", args.log_config)

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
        parser = ArgumentParser(epilog=cls.__doc__)
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
            default=".".join(
                filter(None, ClassDiscovery.decompose_class(connector_wrapper_module.CLIDefaultConnectorWrapper))
            ),
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
        args_ = kwargs.get("args") or sys.argv
        if not isinstance(args_, list):
            raise ValueError("args must be   a list of strings or None")

        parsed_args, _ = parser.parse_known_args(args=args_)
        cls._setup_logger(args=parsed_args)
        return cls.model_validate(vars(parsed_args))
