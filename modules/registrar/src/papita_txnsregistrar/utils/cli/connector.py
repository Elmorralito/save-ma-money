"""CLI connector wrapper module for database connection management.

This module provides wrapper classes that facilitate integration of SQLDatabaseConnector
with command-line interfaces. It enables users to configure database connections through
various methods including direct URLs, configuration files, and default local connections.

The module defines a base wrapper class and several concrete implementations:
    - BaseCLIConnectorWrapper: Abstract base class defining the interface for CLI connector
      wrappers. Provides the foundation for all connector wrapper implementations.
    - CLIURLConnectorWrapper: Wrapper that connects to databases using a connection URL
      string provided via command-line arguments.
    - CLIFileConnectorWrapper: Wrapper that loads database connection parameters from
      configuration files. Supports multiple file formats including JSON, YAML, TOML,
      INI-style config files, and environment files (.env).
    - CLIDefaultConnectorWrapper: Wrapper that uses a default local DuckDB connection
      stored in the user's home directory.

All wrappers extend AbstractCLIUtils to integrate with the CLI utility system and
provide consistent argument parsing and lifecycle management. They encapsulate
SQLDatabaseConnector instances and handle the complexity of connection establishment
from various sources.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, ClassVar, Dict, Self, Tuple, Type

import dotenv
import toml
import yaml

from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.configutils import DEFAULT_ENCODING

from .abstract import AbstractCLIUtils

logger = logging.getLogger(__name__)


class BaseCLIConnectorWrapper(AbstractCLIUtils):
    """Base wrapper class for SQLDatabaseConnector CLI integration.

    This abstract base class provides the foundation for all CLI connector wrappers.
    It encapsulates a SQLDatabaseConnector instance, allowing it to be easily
    constructed and managed via command-line interfaces. It serves as a bridge
    between CLI utilities and the database connection logic.

    Subclasses must implement the load() method to provide specific connection
    establishment logic based on their connection source (URL, file, default, etc.).

    Attributes:
        connector: The database connector instance. This is set during model
                   validation when load() is called.

    Note:
        This class extends AbstractCLIUtils to integrate with the CLI utility
        system, providing consistent argument parsing and lifecycle management.
    """

    connector: Type[SQLDatabaseConnector]

    @classmethod
    def load(cls, **kwargs) -> Self:
        """Load the connector wrapper using Pydantic's model construction.

        This method constructs an instance of the connector wrapper by validating
        and parsing the provided keyword arguments. It must be implemented by
        subclasses to provide specific connection establishment logic.

        Args:
            **kwargs: Keyword arguments required for constructing the connector.
                      Typically includes connection parameters and may include
                      'args' for command-line argument parsing.

        Returns:
            Self: An instance of the connector wrapper with the connector
                  attribute populated.

        Raises:
            NotImplementedError: Always raised, as this method must be
                                  implemented by subclasses.
        """
        raise NotImplementedError("This method should be implemented in subclasses.")

    def run(self) -> Self:
        """Execute the connector wrapper lifecycle operations.

        This method provides a no-op implementation for the run phase of the
        connector wrapper lifecycle. Subclasses may override this method to
        perform additional initialization or setup operations.

        Returns:
            Self: Returns self for method chaining.
        """
        return self

    def stop(self) -> Self:
        """Shutdown the connector wrapper and release resources.

        This method provides a no-op implementation for the stop phase of the
        connector wrapper lifecycle. Subclasses may override this method to
        perform cleanup operations such as closing database connections.

        Returns:
            Self: Returns self for method chaining.
        """
        return self


class CLIURLConnectorWrapper(BaseCLIConnectorWrapper):
    """CLI wrapper for SQLDatabaseConnector that connects using a database URL.

    This wrapper allows users to specify a database connection via a URL string
    when using command-line interfaces. It parses the --connect-url argument
    from the command line and constructs the underlying SQLDatabaseConnector
    based on the provided URL.

    The URL format follows standard database connection string conventions
    (e.g., "postgresql://user:password@host:port/database" or
    "duckdb:///path/to/file.duckdb").

    Attributes:
        connector: The database connector instance established from the URL.
    """

    @classmethod
    def parse_cli_args(cls, **kwargs) -> Dict[str, Any]:
        """Build the argument parser for the connector wrapper."""
        parser = argparse.ArgumentParser(description=cls.__doc__)
        parser.add_argument(
            "--connect-url",
            dest="connect_url",
            help="The database connection URL.",
            type=str,
            required=True,
        )
        parsed_args, _ = parser.parse_known_args(kwargs.pop("args", None) or sys.argv)
        return vars(parsed_args)

    @classmethod
    def load(cls, **kwargs) -> Self:
        """Load the connector wrapper using the provided database URL.

        This method parses command-line arguments to extract the database
        connection URL, then constructs an instance of CLIURLConnectorWrapper
        by creating a SQLDatabaseConnector with the specified URL.

        Args:
            **kwargs: Keyword arguments. May include:
                - args (List[str] | None): Command-line arguments to parse.
                  If not provided, sys.argv is used.
                - Additional keyword arguments passed to model validation.

        Returns:
            Self: An instance of CLIURLConnectorWrapper with the connector
                  attribute populated from the parsed URL.

        Raises:
            SystemExit: If the --connect-url argument is missing or invalid.
            ValidationError: If the model validation fails after parsing
                              arguments.
        """
        parsed_args = cls.parse_cli_args(**kwargs)
        return cls.model_validate(
            {"connector": SQLDatabaseConnector.establish(connection=parsed_args["connect_url"]), **kwargs}
        )


class CLIFileConnectorWrapper(BaseCLIConnectorWrapper):
    """CLI wrapper for SQLDatabaseConnector that connects using a configuration file.

    This wrapper allows users to specify a database connection via a configuration
    file path when using command-line interfaces. It supports multiple file formats
    including JSON, YAML, TOML, INI-style config files, and environment files (.env).

    The wrapper automatically detects the file format based on the file extension
    and attempts to load connection parameters. If the initial load fails, it
    will attempt to load the file with different format extensions as a fallback.

    For environment files, the wrapper maps common environment variable names to
    database connection parameters using the MAPPING_VARIABLES dictionary.

    Attributes:
        connector: The database connector instance established from the file
                   configuration.

    Class Variables:
        CONFIG_FILE_EXTENSIONS: Tuple of supported INI-style config file
                                 extensions (.cfg, .ini, .conf).
        JSON_FILE_EXTENSIONS: Tuple of supported JSON file extensions
                               (.json, .jsonc).
        YAML_FILE_EXTENSIONS: Tuple of supported YAML file extensions
                               (.yaml, .yml).
        TOML_FILE_EXTENSIONS: Tuple of supported TOML file extensions (.toml).
        ENV_FILE_EXTENSIONS: Tuple of supported environment file extensions
                              (.env, .properties).
        MAPPING_VARIABLES: Dictionary mapping environment variable names to
                           database connection parameter names.
    """

    CONFIG_FILE_EXTENSIONS: ClassVar[Tuple[str, ...]] = (".cfg", ".ini", ".conf")
    JSON_FILE_EXTENSIONS: ClassVar[Tuple[str, ...]] = (".json", ".jsonc")
    YAML_FILE_EXTENSIONS: ClassVar[Tuple[str, ...]] = (".yaml", ".yml")
    TOML_FILE_EXTENSIONS: ClassVar[Tuple[str, ...]] = (".toml",)
    ENV_FILE_EXTENSIONS: ClassVar[Tuple[str, ...]] = (".env", ".properties")
    MAPPING_VARIABLES: ClassVar[Dict[str, str]] = {
        "DB_DRIVER": "drivername",
        "DB_URL": "url",
        "DB_USER": "username",
        "DB_PASSWORD": "password",
        "DB_HOST": "host",
        "DB_PORT": "port",
        "DB_NAME": "database",
        "USERNAME": "username",
        "PASSWORD": "password",
        "HOST": "host",
        "PORT": "port",
        "DATABASE": "database",
        "DRIVERNAME": "drivername",
        "URL": "url",
    }

    @classmethod
    def _load_config_file(cls, connect_file: str) -> dict | None:
        """Load connection parameters from an INI-style configuration file.

        This method reads a configuration file in INI format (key=value pairs)
        and parses it into a dictionary. Lines starting with '#' are treated
        as comments and ignored.

        Args:
            connect_file: Path to the configuration file to load.

        Returns:
            Dictionary containing connection parameters parsed from the file,
            or None if the file is empty or cannot be parsed.

        Raises:
            ValueError: If a line cannot be parsed as key=value format.
            IOError: If the file cannot be read.
        """
        output = {}
        with open(connect_file, mode="r", encoding=DEFAULT_ENCODING) as freader:
            for line in freader:
                if line.strip().startswith("#"):
                    continue
                key, value = line.strip().split("=")
                output[key.strip()] = value.strip()

        return output

    @classmethod
    def _load_json_file(cls, connect_file: str) -> dict | None:
        """Load connection parameters from a JSON configuration file.

        This method reads a JSON file and parses it into a dictionary containing
        connection parameters.

        Args:
            connect_file: Path to the JSON file to load.

        Returns:
            Dictionary containing connection parameters parsed from the JSON file,
            or None if the file is empty.

        Raises:
            TypeError: If the JSON content is not a dictionary.
            json.JSONDecodeError: If the file contains invalid JSON.
            IOError: If the file cannot be read.
        """
        with open(connect_file, mode="r", encoding=DEFAULT_ENCODING) as freader:
            content = json.load(freader)

        if not isinstance(content, dict):
            raise TypeError("The content of the JSON file is not a dictionary.")

        return content

    @classmethod
    def _load_toml_file(cls, connect_file: str) -> dict | None:
        """Load connection parameters from a TOML configuration file.

        This method reads a TOML file and parses it into a dictionary containing
        connection parameters.

        Args:
            connect_file: Path to the TOML file to load.

        Returns:
            Dictionary containing connection parameters parsed from the TOML file,
            or None if the file is empty.

        Raises:
            TypeError: If the TOML content is not a dictionary.
            toml.TomlDecodeError: If the file contains invalid TOML.
            IOError: If the file cannot be read.
        """
        with open(connect_file, mode="r", encoding=DEFAULT_ENCODING) as freader:
            content = toml.load(freader, _dict=dict)

        if not isinstance(content, dict):
            raise TypeError("The content of the TOML file is not a dictionary.")

        return content

    @classmethod
    def _load_yaml_file(cls, connect_file: str) -> dict | None:
        """Load connection parameters from a YAML configuration file.

        This method reads a YAML file and parses it into a dictionary containing
        connection parameters using the SafeLoader for security.

        Args:
            connect_file: Path to the YAML file to load.

        Returns:
            Dictionary containing connection parameters parsed from the YAML file,
            or None if the file is empty.

        Raises:
            TypeError: If the YAML content is not a dictionary.
            yaml.YAMLError: If the file contains invalid YAML.
            IOError: If the file cannot be read.
        """
        with open(connect_file, mode="r", encoding=DEFAULT_ENCODING) as freader:
            content = yaml.load(freader, Loader=yaml.SafeLoader)

        if not isinstance(content, dict):
            raise TypeError("The content of the YAML file is not a dictionary.")

        return content

    @classmethod
    def _load_env_file(cls, connect_file: str) -> dict | None:
        """Load connection parameters from an environment file.

        This method reads an environment file (.env or .properties format) and
        parses it into a dictionary containing connection parameters. It maps
        common environment variable names to database connection parameter names
        using the MAPPING_VARIABLES dictionary.

        Args:
            connect_file: Path to the environment file to load.

        Returns:
            Dictionary containing connection parameters parsed from the
            environment file, or None if the file is empty or cannot be parsed.

        Raises:
            ValueError: If the environment file does not contain a valid database
                         connection URL or required connection parameters.
        """
        content = dotenv.dotenv_values(dotenv_path=connect_file)
        if not content:
            return None

        return content or None


    @classmethod
    def _load_file(cls, connect_file: str) -> dict | None:
        """Load connection parameters from a configuration file with format detection.

        This method automatically detects the file format based on the file extension
        and loads the connection parameters accordingly. If the initial load fails,
        it attempts to load the file with different format extensions as a fallback
        mechanism.

        Supported formats are detected in the following order:
        1. JSON (.json, .jsonc)
        2. YAML (.yaml, .yml)
        3. TOML (.toml)
        4. INI-style config (.cfg, .ini, .conf)
        5. Environment files (.env, .properties)

        Args:
            connect_file: Path to the configuration file to load.

        Returns:
            Dictionary containing connection parameters parsed from the file.

        Raises:
            ValueError: If the file extension is not recognized or the file format
                         is not supported after attempting all fallback formats.
            TypeError: If the file content is not a dictionary after parsing.
            IOError: If the file cannot be read.

        Note:
            If the initial load fails, the method will attempt to load the file
            with different format extensions by appending common extensions to
            the base filename. This allows for more flexible file naming.
        """
        def _load_extension(extension: str) -> dict | None:
            logger.debug("Loading file '%s' with extension: %s", connect_file, extension)
            connection = None
            try:
                if extension in cls.JSON_FILE_EXTENSIONS:
                    connection = cls._load_json_file(connect_file)
                
                if extension in cls.YAML_FILE_EXTENSIONS:
                    connection = cls._load_yaml_file(connect_file)
                
                if extension in cls.TOML_FILE_EXTENSIONS:
                    connection = cls._load_toml_file(connect_file)
                
                if extension in cls.CONFIG_FILE_EXTENSIONS:
                    connection = cls._load_config_file(connect_file)
                
                if extension in cls.ENV_FILE_EXTENSIONS:
                    connection = cls._load_env_file(connect_file)
                
                if not isinstance(connection, dict) or connection is None:
                    raise ValueError(f"The file extension is not recognized or the file format is not supported on '{connect_file}'.")

            except Exception:
                logger.exception("Something happened while loading the file: %s", connect_file)
                logger.warning("Trying to load the file over different formats...")

            return connection

        for format_ in set(
            cls.JSON_FILE_EXTENSIONS
            + cls.TOML_FILE_EXTENSIONS
            + cls.YAML_FILE_EXTENSIONS
            + cls.CONFIG_FILE_EXTENSIONS
            + cls.ENV_FILE_EXTENSIONS
        ):
            connection = _load_extension(format_)
            if connection:
                return connection

        raise ValueError(f"The file format is not supported on '{connect_file}'.")

    @classmethod
    def map_connection_params(cls, connection_params: dict) -> dict:
        """Map connection parameters to database connection parameters."""
        mapping = { key.upper(): value for key, value in cls.MAPPING_VARIABLES.items() }
        output = {}
        for key, value in connection_params.items():
            if key.upper() in mapping:
                output[mapping[key.upper()]] = value
            else:
                output[key] = value

        if "url" in output:
            return {"url": output["url"]}

        return output

    @classmethod
    def parse_cli_args(cls, **kwargs) -> Dict[str, Any]:
        """Build the argument parser for the connector wrapper."""
        parser = argparse.ArgumentParser(description=cls.__doc__)
        parser.add_argument(
            "--connect-file",
            dest="connect_file",
            help="The database connection file path.",
            type=str,
            required=True,
        )
        parsed_args, _ = parser.parse_known_args(kwargs.pop("args", None) or sys.argv)
        return vars(parsed_args)

    @classmethod
    def load(cls, **kwargs) -> Self:
        """Load the connector wrapper using a configuration file.

        This method parses command-line arguments to extract the database
        connection file path, loads the connection parameters from the file,
        and constructs an instance of CLIFileConnectorWrapper by creating a
        SQLDatabaseConnector with the loaded parameters.

        Args:
            **kwargs: Keyword arguments. May include:
                - args (List[str] | None): Command-line arguments to parse.
                  If not provided, sys.argv is used.
                - Additional keyword arguments passed to model validation.

        Returns:
            Self: An instance of CLIFileConnectorWrapper with the connector
                  attribute populated from the configuration file.

        Raises:
            SystemExit: If the --connect-file argument is missing or invalid.
            ValueError: If the configuration file format is not supported or
                         contains invalid connection parameters.
            TypeError: If the file content is not a dictionary after parsing.
            ValidationError: If the model validation fails after loading the
                              configuration file.
        """
        parsed_args = cls.parse_cli_args(**kwargs)
        raw_connection_params = cls._load_file(parsed_args["connect_file"])
        connection_params = cls.map_connection_params(raw_connection_params)
        logger.debug("Connection parameters loaded: %s", connection_params)
        return cls.model_validate({"connector": SQLDatabaseConnector.establish(connection=connection_params), **kwargs})


class CLIDefaultConnectorWrapper(BaseCLIConnectorWrapper):
    """CLI wrapper for SQLDatabaseConnector that uses a default local connection.

    This wrapper provides a convenient default database connection using a local
    DuckDB database file stored in the user's home directory. It automatically
    creates the necessary directory structure and database file if they do not
    exist, making it ideal for local development and testing scenarios.

    The default connection uses DuckDB and stores the database file at
    ~/.papita-local/store.duckdb. This location is automatically created if
    it does not exist when the wrapper is loaded.

    Attributes:
        connector: The database connector instance established using the default
                   local DuckDB connection.

    Class Variables:
        LOCAL_DEFAULT_CONNECTION: The default database connection URL pointing
                                   to a local DuckDB file in the user's home
                                   directory.
    """

    LOCAL_DEFAULT_CONNECTION: ClassVar[str] = (
        f"duckdb:///{os.path.join(os.path.expanduser('~'), '.papita-local', 'store.duckdb')}"
    )

    @classmethod
    def parse_cli_args(cls, **kwargs) -> Dict[str, Any]:
        """Build the argument parser for the connector wrapper."""
        parser = argparse.ArgumentParser(description=cls.__doc__)
        parsed_args, _ = parser.parse_known_args(kwargs.pop("args", None) or sys.argv)
        return vars(parsed_args)

    @classmethod
    def load(cls, **kwargs) -> Self:
        """Load the connector wrapper using the default local connection.

        This method establishes a connection to the default local DuckDB database
        file. It automatically creates the necessary directory structure and
        database file if they do not exist, ensuring the connection can be
        established without manual setup.

        The method performs the following operations:
        1. Extracts the file path from the connection URL
        2. Creates the parent directory if it does not exist
        3. Creates the database file if it does not exist
        4. Establishes the SQLDatabaseConnector connection

        Args:
            **kwargs: Keyword arguments passed to model validation. Typically
                      empty for the default connector wrapper.

        Returns:
            Self: An instance of CLIDefaultConnectorWrapper with the connector
                  attribute populated using the default local connection.

        Note:
            The database file and directory are created automatically if they
            do not exist. This makes the default connector wrapper convenient
            for local development without requiring manual database setup.
        """
        local_default_path = Path(cls.LOCAL_DEFAULT_CONNECTION.removeprefix("duckdb:///"))
        logger.debug("Using local default connection: %s", local_default_path)
        local_default_path.parent.mkdir(exist_ok=True, parents=True)
        if not local_default_path.exists():
            local_default_path.touch()
            logger.debug("Created local default connection file: %s", local_default_path)
        else:
            logger.debug("Local default connection file already exists: %s", local_default_path)

        return cls.model_validate(
            {"connector": SQLDatabaseConnector.establish(connection=cls.LOCAL_DEFAULT_CONNECTION), **kwargs}
        )
