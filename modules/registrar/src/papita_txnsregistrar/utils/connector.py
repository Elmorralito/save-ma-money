import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import ClassVar, Self, Tuple, Type

import toml
import yaml

from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsregistrar.utils.cli import AbstractCLIUtils

logger = logging.getLogger(__name__)


class BaseCLIConnectorWrapper(AbstractCLIUtils):
    """
    A wrapper model for SQLDatabaseConnector to facilitate CLI integration.

    This model encapsulates a SQLDatabaseConnector instance, allowing it to be
    easily constructed and managed via command-line interfaces. It serves as
    a bridge between CLI utilities and the database connection logic.

    Attributes:
        connector (SQLDatabaseConnector): The database connector instance.
    """

    connector: Type[SQLDatabaseConnector]

    @classmethod
    def load(cls, **kwargs) -> Self:
        """
        Load the connector wrapper using Pydantic's model construction.

        This method constructs an instance of CLIConnectorWrapper by validating
        and parsing the provided keyword arguments.

        Args:
            **kwargs: Keyword arguments required for constructing the connector.

        Returns:
            Self: An instance of CLIConnectorWrapper.
        """
        raise NotImplementedError("This method should be implemented in subclasses.")


class CLIURLConnectoryWrapper(BaseCLIConnectorWrapper):
    """
    A CLI wrapper for SQLDatabaseConnector that connects using a database URL.

    This wrapper allows users to specify a database connection via a URL
    string when using command-line interfaces. It constructs the underlying
    SQLDatabaseConnector based on the provided URL.

    Attributes:
        url (str): The database connection URL.
    """

    @classmethod
    def load(cls, **kwargs) -> Self:
        """
        Load the connector wrapper using the provided database URL.

        This method constructs an instance of CLIURLConnectorWrapper by
        creating a SQLDatabaseConnector with the specified URL.

        Args:
            **kwargs: Keyword arguments containing 'url' for the database connection.

        Returns:
            Self: An instance of CLIURLConnectorWrapper.
        """
        parser = argparse.ArgumentParser(cls.__doc__)
        parser.add_argument(
            "--connect-url",
            dest="connect_url",
            help="The database connection URL.",
            type=str,
            required=True,
        )
        parsed_args, _ = parser.parse_known_args(args=kwargs.pop("args") or sys.argv)

        return cls.model_validate(
            {"connector": SQLDatabaseConnector.establish(connection=getattr(parsed_args, "connect_url")), **kwargs}
        )


class CLIFileConnectoryWrapper(BaseCLIConnectorWrapper):
    """
    A CLI wrapper for SQLDatabaseConnector that connects using a file path.

    This wrapper allows users to specify a database connection via a file path
    when using command-line interfaces. It constructs the underlying
    SQLDatabaseConnector based on the provided file path.
    """

    CONFIG_FILE_EXTENSIONS: ClassVar[Tuple[str, ...]] = (".cfg", ".ini", ".conf")
    JSON_FILE_EXTENSIONS: ClassVar[Tuple[str, ...]] = (".json", ".jsonc")
    YAML_FILE_EXTENSIONS: ClassVar[Tuple[str, ...]] = (".yaml", ".yml")
    TOML_FILE_EXTENSIONS: ClassVar[Tuple[str, ...]] = (".toml",)

    @classmethod
    def _load_config_file(cls, connect_file: str) -> dict | None:
        output = {}
        with open(connect_file, mode="r", encoding="utf-8") as freader:
            for line in freader:
                if line.strip().startswith("#"):
                    continue
                key, value = line.strip().split("=")
                output[key.strip()] = value.strip()

        return output

    @classmethod
    def _load_json_file(cls, connect_file: str) -> dict | None:
        with open(connect_file, mode="r", encoding="utf-8") as freader:
            content = json.load(freader)

        if not isinstance(content, dict):
            raise TypeError("The content of the JSON file is not a dictionary.")

        return content

    @classmethod
    def _load_toml_file(cls, connect_file: str) -> dict | None:
        with open(connect_file, mode="r", encoding="utf-8") as freader:
            content = toml.load(freader, _dict=dict)

        if not isinstance(content, dict):
            raise TypeError("The content of the TOML file is not a dictionary.")

        return content

    @classmethod
    def _load_yaml_file(cls, connect_file: str) -> dict | None:
        with open(connect_file, mode="r", encoding="utf-8") as freader:
            content = yaml.load(freader, Loader=yaml.SafeLoader)

        if not isinstance(content, dict):
            raise TypeError("The content of the YAML file is not a dictionary.")

        return content

    @classmethod
    def _load_file(cls, connect_file: str) -> dict:
        try:
            if connect_file.endswith(cls.JSON_FILE_EXTENSIONS):
                connection = cls._load_json_file(connect_file)
            elif connect_file.endswith(cls.YAML_FILE_EXTENSIONS):
                connection = cls._load_yaml_file(connect_file)
            elif connect_file.endswith(cls.TOML_FILE_EXTENSIONS):
                connection = cls._load_toml_file(connect_file)
            elif connect_file.endswith(cls.CONFIG_FILE_EXTENSIONS):
                connection = cls._load_config_file(connect_file)
            else:
                raise ValueError(f"The file extension is not recognized on '{connect_file}'.")

            if not isinstance(connection, dict):
                raise TypeError("The content of the file is not a dictionary.")

            return connection
        except Exception:
            logger.exception("Something happened while loading the file: %s", connect_file)
            logger.warning("Trying to load the file over different formats...")

        for format_ in set(
            cls.JSON_FILE_EXTENSIONS + cls.TOML_FILE_EXTENSIONS + cls.YAML_FILE_EXTENSIONS + cls.CONFIG_FILE_EXTENSIONS
        ):
            file_path = connect_file.removesuffix(".") + f".{format_.lstrip('.')}"
            try:
                return cls._load_file(file_path)
            except Exception:
                logger.warning("Something happened while loading the file: %s", file_path)

        raise ValueError(f"The file format is not supported on '{connect_file}'.")

    @classmethod
    def load(cls, **kwargs) -> Self:
        parser = argparse.ArgumentParser(cls.__doc__)
        parser.add_argument(
            "--connect-file",
            dest="connect_file",
            help="The database connection file path.",
            type=str,
            required=True,
        )
        parsed_args, _ = parser.parse_known_args(args=kwargs.pop("args") or sys.argv)
        content = cls._load_file(getattr(parsed_args, "connect_file"))
        return cls.model_validate({"connector": SQLDatabaseConnector.establish(connection=content), **kwargs})


class CLIDefaultConnectorWrapper(BaseCLIConnectorWrapper):
    """
    A CLI wrapper for SQLDatabaseConnector that connects using the default connection.

    This wrapper allows users to specify a database connection via a file path
    when using command-line interfaces. It constructs the underlying
    SQLDatabaseConnector based on the provided file path.
    """

    LOCAL_DEFAULT_CONNECTION: ClassVar[str] = (
        f"duckdb:///{os.path.join(os.path.expanduser('~'), '.config', 'papita', 'db', 'store.duckdb')}"
    )

    @classmethod
    def load(cls, **kwargs) -> Self:
        local_default_path = Path(cls.LOCAL_DEFAULT_CONNECTION.removeprefix("duckdb:///"))
        logger.debug("Using local default connection: %s", local_default_path)
        local_default_path.parent.mkdir(parents=True, exist_ok=True)
        if not local_default_path.exists():
            local_default_path.touch()
            logger.debug("Created local default connection file: %s", local_default_path)
        else:
            logger.debug("Local default connection file already exists: %s", local_default_path)

        return cls.model_validate(
            {"connector": SQLDatabaseConnector.establish(connection=cls.LOCAL_DEFAULT_CONNECTION), **kwargs}
        )
