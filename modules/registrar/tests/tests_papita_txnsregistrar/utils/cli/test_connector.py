"""Test suite for CLI connector wrapper classes.

This module contains unit tests for the CLI connector wrapper classes that facilitate
database connection management through command-line interfaces. The tests verify that
each wrapper class correctly parses arguments, loads connection configurations from
various file formats, and establishes database connections using mocked database
operations to ensure complete test isolation without actual database connections.
"""

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from papita_txnsmodel.database.connector import SQLDatabaseConnector

from papita_txnsregistrar.utils.cli.connector import (
    BaseCLIConnectorWrapper,
    CLIDefaultConnectorWrapper,
    CLIFileConnectorWrapper,
    CLIURLConnectorWrapper,
)


def test_base_cli_connector_wrapper_load_raises_not_implemented_error():
    """Test that BaseCLIConnectorWrapper.load raises NotImplementedError when called directly."""
    with pytest.raises(NotImplementedError, match="This method should be implemented in subclasses"):
        BaseCLIConnectorWrapper.load()


@patch("papita_txnsregistrar.utils.cli.connector.SQLDatabaseConnector")
@patch("papita_txnsregistrar.utils.cli.connector.argparse.ArgumentParser")
def test_cli_url_connector_wrapper_load_success(mock_parser_class, mock_connector_class):
    """Test that CLIURLConnectorWrapper.load successfully creates instance with URL connection."""
    # Arrange
    mock_parser = MagicMock()
    mock_parser_class.return_value = mock_parser
    mock_parsed_args = MagicMock()
    mock_parsed_args.connect_url = "postgresql://user:pass@localhost/db"
    mock_parser.parse_known_args.return_value = (mock_parsed_args, [])
    # establish() returns the class itself (Type[SQLDatabaseConnector]), not an instance
    mock_connector_class.establish.return_value = SQLDatabaseConnector

    # Act
    result = CLIURLConnectorWrapper.load(args=["--connect-url", "postgresql://user:pass@localhost/db"])

    # Assert
    assert isinstance(result, CLIURLConnectorWrapper)
    assert result.connector == SQLDatabaseConnector
    mock_parser.add_argument.assert_called_once()
    mock_connector_class.establish.assert_called_once_with(connection="postgresql://user:pass@localhost/db")


@patch("papita_txnsregistrar.utils.cli.connector.SQLDatabaseConnector")
@patch("papita_txnsregistrar.utils.cli.connector.argparse.ArgumentParser")
@patch("builtins.open", new_callable=mock_open, read_data='{"url": "postgresql://localhost/testdb"}')
@patch("papita_txnsregistrar.utils.cli.connector.json.load")
def test_cli_file_connector_wrapper_load_json_success(
    mock_json_load, mock_file_open, mock_parser_class, mock_connector_class
):
    """Test that CLIFileConnectorWrapper.load successfully loads JSON file and creates connector."""
    # Arrange
    mock_parser = MagicMock()
    mock_parser_class.return_value = mock_parser
    mock_parsed_args = MagicMock()
    mock_parsed_args.connect_file = "/path/to/config.json"
    mock_parser.parse_known_args.return_value = (mock_parsed_args, [])
    mock_json_load.return_value = {"url": "postgresql://localhost/testdb"}
    # establish() returns the class itself (Type[SQLDatabaseConnector]), not an instance
    mock_connector_class.establish.return_value = SQLDatabaseConnector

    # Act
    result = CLIFileConnectorWrapper.load(args=["--connect-file", "/path/to/config.json"])

    # Assert
    assert isinstance(result, CLIFileConnectorWrapper)
    assert result.connector == SQLDatabaseConnector
    mock_connector_class.establish.assert_called_once_with(connection={"url": "postgresql://localhost/testdb"})


@patch("builtins.open", new_callable=mock_open, read_data='{"url": "postgresql://localhost/testdb"}')
def test_load_json_file_success(mock_file):
    """Test that _load_json_file successfully loads and returns dictionary from JSON file."""
    # Arrange
    file_path = "/path/to/config.json"
    expected_content = {"url": "postgresql://localhost/testdb"}

    # Act
    result = CLIFileConnectorWrapper._load_json_file(file_path)

    # Assert
    assert result == expected_content
    mock_file.assert_called_once_with(file_path, mode="r", encoding="utf-8")


@patch("builtins.open", new_callable=mock_open, read_data='["not", "a", "dict"]')
def test_load_json_file_raises_type_error_for_non_dict(mock_file):
    """Test that _load_json_file raises TypeError when JSON content is not a dictionary."""
    # Arrange
    file_path = "/path/to/config.json"

    # Act & Assert
    with pytest.raises(TypeError, match="The content of the JSON file is not a dictionary"):
        CLIFileConnectorWrapper._load_json_file(file_path)


@patch("builtins.open", new_callable=mock_open, read_data="url: postgresql://localhost/testdb\nhost: localhost")
def test_load_yaml_file_success(mock_file):
    """Test that _load_yaml_file successfully loads and returns dictionary from YAML file."""
    # Arrange
    file_path = "/path/to/config.yaml"
    expected_content = {"url": "postgresql://localhost/testdb", "host": "localhost"}

    # Act
    with patch("papita_txnsregistrar.utils.cli.connector.yaml.load", return_value=expected_content) as mock_yaml_load:
        result = CLIFileConnectorWrapper._load_yaml_file(file_path)

    # Assert
    assert result == expected_content
    mock_file.assert_called_once_with(file_path, mode="r", encoding="utf-8")
    mock_yaml_load.assert_called_once()


@patch("builtins.open", new_callable=mock_open, read_data="key1=value1\nkey2=value2\n# This is a comment\nkey3=value3")
def test_load_config_file_success_with_comments(mock_file):
    """Test that _load_config_file successfully loads config file and skips comment lines."""
    # Arrange
    file_path = "/path/to/config.cfg"
    expected_content = {"key1": "value1", "key2": "value2", "key3": "value3"}

    # Act
    result = CLIFileConnectorWrapper._load_config_file(file_path)

    # Assert
    assert result == expected_content
    mock_file.assert_called_once_with(file_path, mode="r", encoding="utf-8")


@patch("papita_txnsregistrar.utils.cli.connector.dotenv.dotenv_values")
def test_load_env_file_success_with_mapping(mock_dotenv_values):
    """Test that _load_env_file successfully loads env file and maps variables correctly."""
    # Arrange
    file_path = "/path/to/config.env"
    # Include DB_URL to satisfy the validation check (either "url" in output OR all mapping values)
    mock_dotenv_values.return_value = {
        "DB_URL": "postgresql://localhost/testdb",
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "testdb",
        "DB_USER": "testuser",
        "DB_PASSWORD": "testpass",
    }
    expected_content = {
        "url": "postgresql://localhost/testdb",
        "host": "localhost",
        "port": "5432",
        "database": "testdb",
        "username": "testuser",
        "password": "testpass",
    }

    # Act
    result = CLIFileConnectorWrapper._load_env_file(file_path)

    # Assert
    assert result == expected_content
    mock_dotenv_values.assert_called_once_with(dotenv_path=file_path)


@patch("papita_txnsregistrar.utils.cli.connector.dotenv.dotenv_values")
def test_load_env_file_raises_value_error_when_missing_url(mock_dotenv_values):
    """Test that _load_env_file raises ValueError when env file lacks valid database connection URL."""
    # Arrange
    file_path = "/path/to/config.env"
    mock_dotenv_values.return_value = {"SOME_OTHER_VAR": "value"}

    # Act & Assert
    with pytest.raises(ValueError, match="The environment file does not contain a valid database connection URL"):
        CLIFileConnectorWrapper._load_env_file(file_path)


@pytest.mark.parametrize("file_exists", [True, False])
@patch("papita_txnsregistrar.utils.cli.connector.SQLDatabaseConnector")
@patch("papita_txnsregistrar.utils.cli.connector.Path")
def test_cli_default_connector_wrapper_load_handles_file_existence(
    mock_path_class, mock_connector_class, file_exists
):
    """Test that CLIDefaultConnectorWrapper.load handles both existing and non-existing database files."""
    # Arrange
    mock_path = MagicMock(spec=Path)
    mock_path.parent = MagicMock()
    mock_path.exists.return_value = file_exists
    mock_path_class.return_value = mock_path
    # establish() returns the class itself (Type[SQLDatabaseConnector]), not an instance
    mock_connector_class.establish.return_value = SQLDatabaseConnector

    # Act
    result = CLIDefaultConnectorWrapper.load()

    # Assert
    assert isinstance(result, CLIDefaultConnectorWrapper)
    assert result.connector == SQLDatabaseConnector
    mock_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    if file_exists:
        mock_path.touch.assert_not_called()
    else:
        mock_path.touch.assert_called_once()
    mock_connector_class.establish.assert_called_once()
    call_args = mock_connector_class.establish.call_args
    assert "connection" in call_args.kwargs
    assert call_args.kwargs["connection"].startswith("duckdb:///")
