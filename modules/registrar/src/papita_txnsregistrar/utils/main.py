import contextlib
import logging
import sys
from argparse import ArgumentParser
from typing import Annotated, List, Self, Type

from pydantic import Field, model_validator

from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.classutils import ClassDiscovery
from papita_txnsregistrar.contracts.plugin import PluginContract
from papita_txnsregistrar.contracts.registry import Registry
from papita_txnsregistrar.utils.cli import AbstractCLIUtils
from papita_txnsregistrar.utils.connector import BaseCLIConnectorWrapper

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
            if not self.plugin:
                raise ValueError("The specified plugin could not be found.")

            if not issubclass(self.plugin, AbstractCLIUtils):
                raise TypeError("The specified plugin does not support CLI utilities.")
        except Exception as err:
            raise RuntimeError from err

        logger.debug("Plugin '%s' supports CLI utilities.", self.plugin.meta().name)
        return self

    @classmethod
    def load(cls, **kwargs) -> Self:
        parser = ArgumentParser(cls.__doc__)
        parser.add_argument(
            "-p",
            "--plugin",
            dest=cls.model_fields["plugin"].alias,
            help=cls.model_fields["plugin"].field_info.description,
            type=str,
            required=True,
        )
        parser.add_argument(
            "-m",
            "--mod",
            "--module",
            dest=cls.model_fields["modules"].alias,
            help=cls.model_fields["modules"].field_info.description,
            type=str,
            required=False,
            nargs="*",
            default=[],
        )
        parser.add_argument(
            "--modules",
            dest=cls.model_fields["modules"].alias,
            help=cls.model_fields["modules"].field_info.description,
            type=str,
            required=False,
            nargs="*",
            default=[],
        )
        parser.add_argument(
            "--connector-wrapper",
            dest=cls.model_fields["connector_wrapper"].alias,
            help=cls.model_fields["connector_wrapper"].field_info.description,
            type=str,
            required=True,
        )
        parser.add_argument(
            "--case-sensitive",
            dest=cls.model_fields["case_sensitive"].alias,
            help=cls.model_fields["case_sensitive"].field_info.description,
            action="store_false",
            default=cls.model_fields["case_sensitive"].default,
        )
        parser.add_argument(
            "--strict-exact",
            dest=cls.model_fields["strict_exact"].alias,
            help=cls.model_fields["strict_exact"].field_info.description,
            action="store_true",
            default=cls.model_fields["strict_exact"].default,
        )
        parser.add_argument(
            "--fuzzy-threshold",
            dest=cls.model_fields["fuzzy_threshold"].alias,
            help=cls.model_fields["fuzzy_threshold"].field_info.description,
            type=int,
            default=cls.model_fields["fuzzy_threshold"].default,
        )
        parser.add_argument(
            "--safe-mode",
            dest=cls.model_fields["safe_mode"].alias,
            help=cls.model_fields["safe_mode"].field_info.description,
            action="store_true",
            default=cls.model_fields["safe_mode"].default,
        )

        args_ = kwargs.get("args") or sys.argv
        if not isinstance(args_, list):
            raise ValueError("args must be   a list of strings or None")

        parsed_args, _ = parser.parse_known_args(args=args_)
        return cls.model_validate(vars(parsed_args))
