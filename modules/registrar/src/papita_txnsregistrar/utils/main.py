import contextlib
import inspect
import logging
import sys
from argparse import Action, ArgumentParser, Namespace
from typing import Annotated, List, Self, Type

from pydantic import Field, model_validator

from papita_txnsmodel import LIB_NAME as MODEL_LIB_NAME
from papita_txnsmodel import __version__ as MODEL_VERSION
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.classutils import ClassDiscovery
from papita_txnsregistrar import LIB_NAME as REGISTRAR_LIB_NAME
from papita_txnsregistrar import __version__ as REGISTRAR_VERSION
from papita_txnsregistrar.contracts.plugin import PluginContract
from papita_txnsregistrar.contracts.registry import Registry
from papita_txnsregistrar.utils.cli import AbstractCLIUtils
from papita_txnsregistrar.utils.connector import BaseCLIConnectorWrapper, CLIDefaultConnectorWrapper
from papita_txnsregistrar.utils.logger import DEFAULT_LOGGING_CONFIG, setup_logger

logger = logging.getLogger(__name__)


class MainCLIUtils(AbstractCLIUtils):

    plugin: Annotated[
        str | PluginContract, Field(..., alias="plugin", description="Specify the name of the plugin to be used.")
    ]
    modules: List[str] = Field(
        default_factory=lambda: ["papita_txnsregistrar_plugins"],
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
        with contextlib.suppress(AttributeError):
            logger.debug("Cleaning modules: %s", self.modules)
            self.modules = [mod.strip() for mods in self.modules for mod in mods.strip().split(",")]

        try:
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

            logger.debug("Using connector wrapper: %s", connector_wrapper)
            self.connector = connector_wrapper.load().connector
            Registry().discover(*self.modules, debug=True)
            logger.debug("Discovering plugin from modules: %s", self.modules)
            self.plugin = Registry().get(
                label=self.plugin,
                case_sensitive=self.case_sensitive,
                strict_exact=self.strict_exact,
                fuzz_threshold=self.fuzzy_threshold,
            )
            if not self.plugin or not inspect.isclass(self.plugin):
                raise ValueError("The specified plugin could not be found.")

            if not issubclass(self.plugin, AbstractCLIUtils):
                raise TypeError("The specified plugin does not support CLI utilities.")
        except Exception as err:
            raise RuntimeError from err

        logger.debug("Plugin '%s' supports CLI utilities.", self.plugin.meta().name)
        return self

    @classmethod
    def _load_plugin_class(cls, plugin_name: str, modules: List[str], **kwargs) -> Type[AbstractCLIUtils]:
        """Load and return the plugin class without creating an instance."""
        try:
            with contextlib.suppress(AttributeError):
                modules = [mod.strip() for mods in modules for mod in mods.strip().split(",")]

            Registry().discover(*modules, debug=True)
            logger.debug("Discovering plugin from modules: %s", modules)
            plugin = Registry().get(
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
        except Exception as err:
            raise RuntimeError from err

    @classmethod
    def _create_custom_help_action(cls, args_list):
        """Create a custom help action class that has access to the args list."""

        class CustomHelpAction(Action):
            def __init__(self, option_strings, dest, **kwargs):
                super().__init__(option_strings, dest, nargs=0, **kwargs)

            def __call__(self, parser, namespace, values, option_string=None):
                # Parse known args to get plugin name and other necessary parameters
                temp_parser = ArgumentParser(add_help=False)
                temp_parser.add_argument(cls.model_fields["plugin"].alias, type=str)
                temp_parser.add_argument(
                    "-m", "--mod", "--module", dest=cls.model_fields["modules"].alias, nargs="*", default=[]
                )
                temp_parser.add_argument("--modules", dest=cls.model_fields["modules"].alias, nargs="*", default=[])
                temp_parser.add_argument(
                    "--connector-wrapper",
                    dest=cls.model_fields["connector_wrapper"].alias,
                    default=".".join(filter(None, ClassDiscovery.decompose_class(CLIDefaultConnectorWrapper))),
                )
                temp_parser.add_argument(
                    "--case-sensitive",
                    dest=cls.model_fields["case_sensitive"].alias,
                    action="store_false",
                    default=cls.model_fields["case_sensitive"].default,
                )
                temp_parser.add_argument(
                    "--strict-exact",
                    dest=cls.model_fields["strict_exact"].alias,
                    action="store_true",
                    default=cls.model_fields["strict_exact"].default,
                )
                temp_parser.add_argument(
                    "--fuzzy-threshold",
                    dest=cls.model_fields["fuzzy_threshold"].alias,
                    type=int,
                    default=cls.model_fields["fuzzy_threshold"].default,
                )

                # Filter out help flags from args
                filtered_args = [arg for arg in args_list if arg not in ["-h", "--help"]]
                parsed_temp, _ = temp_parser.parse_known_args(args=filtered_args)

                # Load the plugin class and show its help
                try:
                    plugin_name = getattr(parsed_temp, cls.model_fields["plugin"].alias)
                    if plugin_name:
                        plugin_class = cls._load_plugin_class(
                            plugin_name=plugin_name,
                            modules=getattr(parsed_temp, cls.model_fields["modules"].alias)
                            or cls.model_fields["modules"].default_factory(),
                            case_sensitive=getattr(parsed_temp, cls.model_fields["case_sensitive"].alias),
                            strict_exact=getattr(parsed_temp, cls.model_fields["strict_exact"].alias),
                            fuzzy_threshold=getattr(parsed_temp, cls.model_fields["fuzzy_threshold"].alias),
                        )

                        # Get plugin's parser by creating it with help flag
                        # We'll intercept the plugin's load method to get its parser
                        logger.debug("\n%s\n", "=" * 80)
                        plugin_name_display = (
                            plugin_class.meta().name
                            if hasattr(plugin_class, "meta") and callable(getattr(plugin_class, "meta", None))
                            else plugin_class.__name__
                        )
                        logger.debug("Plugin '%s' help:\n", plugin_name_display)

                        # Create plugin parser by temporarily modifying sys.argv and calling load
                        # The plugin's load method will create a parser - we'll capture it
                        old_argv = sys.argv[:]
                        try:
                            # Remove plugin name from args - plugins don't need it
                            # The plugin's parser will ignore unknown main CLI args via parse_known_args
                            plugin_args = [arg for arg in filtered_args if arg != plugin_name]
                            sys.argv = ["plugin"] + plugin_args + ["--help"]
                            try:
                                # This will trigger the plugin's help
                                plugin_class.load(args=sys.argv)
                            except SystemExit:
                                # SystemExit is expected when --help is used
                                pass
                        finally:
                            sys.argv = old_argv
                    else:
                        logger.debug("\nNote: Specify a plugin name to see plugin-specific help.")
                except Exception as e:
                    # If plugin loading fails, show a message
                    logger.exception("Could not load plugin for help: %s", e)
                    logger.exception("Showing main help only.")
                    parser.print_help()

                parser.exit()

        return CustomHelpAction

    @classmethod
    def _setup_logger(cls, args: Namespace) -> None:
        # Configure logging based on verbosity level
        if args.verbose == 1:
            level = logging.INFO
        elif args.verbose == 2:
            level = logging.DEBUG
        elif args.verbose >= 3:
            level = logging.NOTSET  # Or a custom level for maximum verbosity
        else:
            level = logging.WARNING

        logger.debug("Logger setup with level '%s'", level)
        logger.debug("Logger setup with config '%s'", args.log_config)
        setup_logger(name=MODEL_LIB_NAME, config=args.log_config, level=level)
        setup_logger(name=REGISTRAR_LIB_NAME, config=args.log_config, level=level)

    @classmethod
    def load(cls, **kwargs) -> Self:
        parser = ArgumentParser(cls.__doc__, add_help=False)
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
            version=f"%(prog)s {REGISTRAR_VERSION} | Papita Transaction Model {MODEL_VERSION} | by Papita Software",
        )
        parser.add_argument(
            "-v", "--verbose", action="count", default=0, help="Increase output verbosity (e.g., -v, -vv, -vvv)"
        )
        parser.add_argument(
            "--log-config",
            dest="log_config",
            help="Specify the path to the logging configuration file.",
            type=str,
            default=DEFAULT_LOGGING_CONFIG,
        )
        args_ = kwargs.get("args") or sys.argv
        if not isinstance(args_, list):
            raise ValueError("args must be   a list of strings or None")

        # Create custom help action with access to args
        CustomHelpAction = cls._create_custom_help_action(args_)
        parser.add_argument(
            "-h",
            "--help",
            action=CustomHelpAction,
            help="Show this help message and plugin-specific help.",
        )

        parsed_args, _ = parser.parse_known_args(args=args_)
        cls._setup_logger(args=parsed_args)
        return cls.model_validate(vars(parsed_args))
