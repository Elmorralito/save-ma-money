"""
Types Repository tests module.

This module provides tests for the TypesRepository class that handles Types data in the database.
It tests functionality such as database connections, CRUD operations on types, and error handling.
"""

from datetime import datetime
import functools
import os
import tempfile
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch
import uuid

import pandas as pd
import pytest
from sqlalchemy import Engine
from sqlmodel import Session

from papita_txnsmodel.access.types.dto import (
    AssetAccountTypesDTO,
    LiabilityAccountTypesDTO,
    TransactionCategoriesDTO,
    TypesDTO
)
from papita_txnsmodel.access.types.repository import TypesRepository
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.classutils import MetaSingleton


class TestTypesRepository(TypesRepository, metaclass=MetaSingleton):
    """Repository for Types entities testing.

    This class provides methods to access and manipulate Types entities in a test database.
    It inherits from TypesRepository and uses the Singleton pattern via MetaSingleton.

    Attributes:
        __expected_dto_type__: The DTO class used by this repository.
    """

    __expected_dto_type__ = TypesDTO

    @classmethod
    def setup_test_db(
        cls, db_path: Optional[str] = None, connector: type[SQLDatabaseConnector] | None = None
    ) -> "TestTypesRepository":
        """Sets up a DuckDB database for testing purposes.

        This method initializes a connection to a DuckDB database that can be used
        for testing. If no db_path is provided, it creates a temporary database.

        Args:
            db_path: Optional path to the DuckDB database file. If None, a temporary
                    file will be created.
            connector: Optional SQLDatabaseConnector to use. If None, a new one will be created.

        Returns:
            TestTypesRepository: The repository instance connected to the test database.

        Examples:
            >>> # Create a repository with a temporary test database
            >>> repo = TestTypesRepository.setup_test_db()
            >>>
            >>> # Create a repository with a specific test database file
            >>> repo = TestTypesRepository.setup_test_db("/path/to/test.duckdb")
        """
        # Create a temporary file if no path is provided
        if db_path is None:
            temp_dir = tempfile.mkdtemp()
            db_path = Path(temp_dir) / "test_types.duckdb"

        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Connect to DuckDB
        (connector or SQLDatabaseConnector()).establish(
            connection=str(db_path),
            sql_kwargs={"connect_args": {"read_only": False}}
        )
        return cls

    @classmethod
    def teardown_test_db(cls, connector: type[SQLDatabaseConnector] | None = None) -> None:
        """Closes the test database connection.

        This method should be called after tests are completed to properly
        close the database connection.

        Args:
            connector: Optional SQLDatabaseConnector to use. If None, uses the default.

        Examples:
            >>> repo = TestTypesRepository.setup_test_db()
            >>> # Run tests...
            >>> repo.teardown_test_db()
        """
        return (connector or SQLDatabaseConnector).close()

    def create_test_asset_account_type(self, **kwargs) -> AssetAccountTypesDTO:
        """Creates a test asset account type in the database.

        This helper method simplifies creating test asset account types with sensible defaults.

        Args:
            **kwargs: Overrides for the default asset account type attributes.

        Returns:
            AssetAccountTypesDTO: The created asset account type DTO.

        Examples:
            >>> repo = TestTypesRepository.setup_test_db()
            >>> asset_type = repo.create_test_asset_account_type(name="Test Type")
        """
        # Create asset account type with defaults that can be overridden
        defaults = {
            "name": "Test Asset Account Type",
            "description": "Asset account type created for testing purposes",
            "tags": ["test"],
            "active": True,
            "discriminator": "asset_account_types"
        }

        # Override defaults with any provided kwargs
        type_data = {**defaults, **kwargs}
        asset_type = AssetAccountTypesDTO(**type_data)

        # Save to database
        return self.upsert_record(asset_type)  # pylint: disable=E1125

    def create_test_liability_account_type(self, **kwargs) -> LiabilityAccountTypesDTO:
        """Creates a test liability account type in the database.

        This helper method simplifies creating test liability account types with sensible defaults.

        Args:
            **kwargs: Overrides for the default liability account type attributes.

        Returns:
            LiabilityAccountTypesDTO: The created liability account type DTO.

        Examples:
            >>> repo = TestTypesRepository.setup_test_db()
            >>> liability_type = repo.create_test_liability_account_type(name="Test Type")
        """
        # Create liability account type with defaults that can be overridden
        defaults = {
            "name": "Test Liability Account Type",
            "description": "Liability account type created for testing purposes",
            "tags": ["test"],
            "active": True,
            "discriminator": "liability_account_types"
        }

        # Override defaults with any provided kwargs
        type_data = {**defaults, **kwargs}
        liability_type = LiabilityAccountTypesDTO(**type_data)

        # Save to database
        return self.upsert_record(liability_type)  # pylint: disable=E1125

    def create_test_transaction_category(self, **kwargs) -> TransactionCategoriesDTO:
        """Creates a test transaction category in the database.

        This helper method simplifies creating test transaction categories with sensible defaults.

        Args:
            **kwargs: Overrides for the default transaction category attributes.

        Returns:
            TransactionCategoriesDTO: The created transaction category DTO.

        Examples:
            >>> repo = TestTypesRepository.setup_test_db()
            >>> category = repo.create_test_transaction_category(name="Test Category")
        """
        # Create transaction category with defaults that can be overridden
        defaults = {
            "name": "Test Transaction Category",
            "description": "Transaction category created for testing purposes",
            "tags": ["test"],
            "active": True,
            "discriminator": "transaction_categories"
        }

        # Override defaults with any provided kwargs
        category_data = {**defaults, **kwargs}
        category = TransactionCategoriesDTO(**category_data)

        # Save to database
        return self.upsert_record(category)  # pylint: disable=E1125


@pytest.fixture
def mock_sql_connector():
    """Provides a mock for the SQLDatabaseConnector class.

    Returns:
        MagicMock: A mock object for the SQLDatabaseConnector.
    """
    with patch("papita_txnsmodel.database.connector.SQLDatabaseConnector") as mock_connector:
        # Configure mock to return itself for establish method
        mock_connector.establish.return_value = mock_connector
        mock_connector.close.return_value = None
        mock_connector.sql_kwargs = {}
        yield mock_connector


@pytest.fixture
def mock_temp_dir():
    """Creates a temporary directory for test database files.

    Yields:
        str: Path to the temporary directory.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def repo_instance():
    """Provides an instance of TestTypesRepository without database connection.

    Returns:
        TestTypesRepository: An instance of the repository.
    """
    # Create a repository instance without calling setup_test_db
    return TestTypesRepository()


@pytest.fixture
def setup_db_repo():
    """Fixture that sets up a test database and returns a repository.

    This fixture mocks the database connection process.

    Returns:
        tuple: A tuple containing (repository instance, mock_connector)
    """
    with patch("papita_txnsmodel.database.connector.SQLDatabaseConnector") as mock_connector:
        mock_connector.establish.return_value = mock_connector
        mock_connector.close.return_value = None
        mock_connector.sql_kwargs = {}
        yield TestTypesRepository, mock_connector


@pytest.fixture
def mock_db_session():
    """Provides a mock database session.

    Returns:
        MagicMock: A mock session object.
    """
    mock_session = MagicMock(spec=Session)
    return mock_session


@pytest.fixture
def mock_dataframe():
    """Provides a mock pandas DataFrame for test results.

    Returns:
        MagicMock: A mock DataFrame object.
    """
    mock_df = MagicMock(spec=pd.DataFrame)
    mock_df.empty = False
    return mock_df


@pytest.fixture
def test_asset_type_dto():
    """Creates a test asset account type DTO.

    Returns:
        AssetAccountTypesDTO: A DTO with test data.
    """
    return AssetAccountTypesDTO(
        id=uuid.uuid4(),
        name="Test Asset Type",
        description="Test description",
        tags=["test"],
        active=True,
        start_ts=datetime.now(),
        discriminator="asset_account_types"
    )


@pytest.fixture
def test_liability_type_dto():
    """Creates a test liability account type DTO.

    Returns:
        LiabilityAccountTypesDTO: A DTO with test data.
    """
    return LiabilityAccountTypesDTO(
        id=uuid.uuid4(),
        name="Test Liability Type",
        description="Test description",
        tags=["test"],
        active=True,
        start_ts=datetime.now(),
        discriminator="liability_account_types"
    )


@pytest.fixture
def test_transaction_category_dto():
    """Creates a test transaction category DTO.

    Returns:
        TransactionCategoriesDTO: A DTO with test data.
    """
    return TransactionCategoriesDTO(
        id=uuid.uuid4(),
        name="Test Transaction Category",
        description="Test description",
        tags=["test"],
        active=True,
        start_ts=datetime.now(),
        discriminator="transaction_categories"
    )


@pytest.fixture
def mock_upsert_record():
    """Provides a mock for the upsert_record method.

    Returns:
        MagicMock: A mock for the upsert_record method.
    """
    with patch.object(TypesRepository, "upsert_record") as mock_upsert:
        mock_upsert.return_value = TypesDTO(
            name="Test Type",
            description="Type created for testing purposes",
            tags=["test"],
            active=True
        )
        yield mock_upsert


@pytest.fixture
def mock_connect_deco(mock_db_session):
    """Creates a mock connect decorator for testing database operations.

    Args:
        mock_db_session: A mock session object.

    Returns:
        function: A decorated function that uses the mock session.
    """
    def mock_connect(cls, func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            kwargs.pop("_testing_", None)
            return func(self, *args, _db_session=mock_db_session, _testing_=True, **kwargs)

        return wrapper

    return mock_connect


def test_repository_expected_dto():
    """Test that the repository has the correct expected DTO type."""
    # Act & Assert
    assert TestTypesRepository.__expected_dto_type__ == TypesDTO


def test_setup_test_db_with_path(mock_sql_connector, mock_temp_dir):
    """Test setup_test_db method with a specific database path."""
    # Arrange
    db_path = os.path.join(mock_temp_dir, "test.duckdb")

    # Act
    repo = TestTypesRepository.setup_test_db(db_path=db_path, connector=mock_sql_connector)

    # Assert
    assert issubclass(repo, TypesRepository)
    mock_sql_connector.establish.assert_called_once()
    # Verify the connection arguments
    call_args = mock_sql_connector.establish.call_args
    assert call_args[1]["connection"] == db_path
    assert "sql_kwargs" in call_args[1]
    assert call_args[1]["sql_kwargs"]["connect_args"]["read_only"] is False


def test_setup_test_db_without_path(mock_sql_connector):
    """Test setup_test_db method without specifying a database path."""
    # Act
    repo = TestTypesRepository.setup_test_db(connector=mock_sql_connector)

    # Assert
    assert issubclass(repo, TypesRepository)
    mock_sql_connector.establish.assert_called_once()
    # Verify a path was automatically created
    call_args = mock_sql_connector.establish.call_args
    assert isinstance(call_args[1]["connection"], str)
    assert "test_types.duckdb" in call_args[1]["connection"]


def test_teardown_test_db(mock_sql_connector):
    """Test that teardown_test_db calls the close method on SQLDatabaseConnector."""
    # Arrange
    repo = TestTypesRepository()

    # Act
    repo.teardown_test_db(connector=mock_sql_connector)

    # Assert
    mock_sql_connector.close.assert_called_once()


def test_create_test_asset_account_type_with_defaults(repo_instance, mock_upsert_record):
    """Test creating a test asset account type with default values."""
    # Act
    asset_type = repo_instance.create_test_asset_account_type()

    # Assert
    mock_upsert_record.assert_called_once()
    dto = mock_upsert_record.call_args[0][0]
    assert dto.name == "Test Asset Account Type"
    assert dto.description == "Asset account type created for testing purposes"
    assert dto.tags == ["test"]
    assert dto.active is True
    assert dto.discriminator == "asset_account_types"
    assert asset_type == mock_upsert_record.return_value


def test_create_test_asset_account_type_with_custom_values(repo_instance, mock_upsert_record):
    """Test creating a test asset account type with custom values."""
    # Arrange
    custom_values = {
        "name": "Custom Asset Type",
        "description": "Custom description",
        "tags": ["custom", "test"],
        "active": False
    }

    # Act
    asset_type = repo_instance.create_test_asset_account_type(**custom_values)

    # Assert
    mock_upsert_record.assert_called_once()
    dto = mock_upsert_record.call_args[0][0]
    assert dto.name == custom_values["name"]
    assert dto.description == custom_values["description"]
    assert dto.tags == custom_values["tags"]
    assert dto.active is custom_values["active"]
    assert dto.discriminator == "asset_account_types"
    assert asset_type == mock_upsert_record.return_value


def test_create_test_liability_account_type_with_defaults(repo_instance, mock_upsert_record):
    """Test creating a test liability account type with default values."""
    # Act
    liability_type = repo_instance.create_test_liability_account_type()

    # Assert
    mock_upsert_record.assert_called_once()
    dto = mock_upsert_record.call_args[0][0]
    assert dto.name == "Test Liability Account Type"
    assert dto.description == "Liability account type created for testing purposes"
    assert dto.tags == ["test"]
    assert dto.active is True
    assert dto.discriminator == "liability_account_types"
    assert liability_type == mock_upsert_record.return_value


def test_create_test_liability_account_type_with_custom_values(repo_instance, mock_upsert_record):
    """Test creating a test liability account type with custom values."""
    # Arrange
    custom_values = {
        "name": "Custom Liability Type",
        "description": "Custom description",
        "tags": ["custom", "test"],
        "active": False
    }

    # Act
    liability_type = repo_instance.create_test_liability_account_type(**custom_values)

    # Assert
    mock_upsert_record.assert_called_once()
    dto = mock_upsert_record.call_args[0][0]
    assert dto.name == custom_values["name"]
    assert dto.description == custom_values["description"]
    assert dto.tags == custom_values["tags"]
    assert dto.active is custom_values["active"]
    assert dto.discriminator == "liability_account_types"
    assert liability_type == mock_upsert_record.return_value


def test_create_test_transaction_category_with_defaults(repo_instance, mock_upsert_record):
    """Test creating a test transaction category with default values."""
    # Act
    category = repo_instance.create_test_transaction_category()

    # Assert
    mock_upsert_record.assert_called_once()
    dto = mock_upsert_record.call_args[0][0]
    assert dto.name == "Test Transaction Category"
    assert dto.description == "Transaction category created for testing purposes"
    assert dto.tags == ["test"]
    assert dto.active is True
    assert dto.discriminator == "transaction_categories"
    assert category == mock_upsert_record.return_value


def test_create_test_transaction_category_with_custom_values(repo_instance, mock_upsert_record):
    """Test creating a test transaction category with custom values."""
    # Arrange
    custom_values = {
        "name": "Custom Category",
        "description": "Custom description",
        "tags": ["custom", "test"],
        "active": False
    }

    # Act
    category = repo_instance.create_test_transaction_category(**custom_values)

    # Assert
    mock_upsert_record.assert_called_once()
    dto = mock_upsert_record.call_args[0][0]
    assert dto.name == custom_values["name"]
    assert dto.description == custom_values["description"]
    assert dto.tags == custom_values["tags"]
    assert dto.active is custom_values["active"]
    assert dto.discriminator == "transaction_categories"
    assert category == mock_upsert_record.return_value


def test_integration_setup_and_teardown(setup_db_repo):
    """Test the integration of setup and teardown methods."""
    # Arrange
    repo, mock_connector = setup_db_repo

    # Act
    repo.setup_test_db(connector=mock_connector)
    repo.teardown_test_db(connector=mock_connector)

    # Assert
    mock_connector.establish.assert_called_once()
    mock_connector.close.assert_called_once()


def test_get_records(repo_instance):
    """Test retrieving records with the get_records method."""
    # Arrange
    test_data = pd.DataFrame({
        "name": ["Type 1", "Type 2"],
        "description": ["Description 1", "Description 2"],
        "tags": [["tag1"], ["tag2"]],
        "active": [True, True],
        "discriminator": ["asset_account_types", "liability_account_types"]
    })

    with patch.object(repo_instance, "run_query", return_value=test_data):
        # Act
        result = repo_instance.get_records(dto_type=AssetAccountTypesDTO)

        # Assert
        assert not result.empty
        assert len(result) == 2
        assert list(result["name"]) == ["Type 1", "Type 2"]


def test_get_records_empty_result(repo_instance):
    """Test retrieving records with no results."""
    # Arrange
    with patch.object(repo_instance, "run_query", return_value=pd.DataFrame()):
        # Act
        result = repo_instance.get_records(dto_type=AssetAccountTypesDTO)

        # Assert
        assert result.empty


def test_get_record_by_id(repo_instance, test_asset_type_dto):
    """Test retrieving a record by ID."""
    # Arrange
    test_id = test_asset_type_dto.id
    test_data = pd.DataFrame({
        "id": [test_id],
        "name": ["Test Asset Type"],
        "description": ["Test description"],
        "tags": [["test"]],
        "active": [True],
        "discriminator": ["asset_account_types"]
    })

    with patch.object(repo_instance, "get_records", return_value=test_data):
        with patch.object(AssetAccountTypesDTO, "standardized_dataframe") as mock_standardize:
            mock_standardize.return_value = test_data

            # Act
            result = repo_instance.get_record_by_id(test_id, AssetAccountTypesDTO)

            # Assert
            assert result is not None
            assert result["id"] == test_id
            assert result["name"] == "Test Asset Type"
            assert result["discriminator"] == "asset_account_types"
            mock_standardize.assert_called_once()


def test_get_records_from_attributes(repo_instance, test_liability_type_dto):
    """Test retrieving records based on entity attributes."""
    # Arrange
    test_data = pd.DataFrame({
        "id": [test_liability_type_dto.id],
        "name": ["Test Liability Type"],
        "description": ["Test description"],
        "tags": [["test"]],
        "active": [True],
        "discriminator": ["liability_account_types"]
    })

    with patch.object(repo_instance, "get_records", return_value=test_data):
        # Act
        result = repo_instance.get_records_from_attributes(test_liability_type_dto)

        # Assert
        assert not result.empty
        assert len(result) == 1
        assert result.iloc[0]["name"] == "Test Liability Type"
        assert result.iloc[0]["discriminator"] == "liability_account_types"


def test_get_record_from_attributes(repo_instance, test_transaction_category_dto):
    """Test retrieving a single record based on entity attributes."""
    # Arrange
    test_data = pd.DataFrame({
        "id": [test_transaction_category_dto.id],
        "name": ["Test Transaction Category"],
        "description": ["Test description"],
        "tags": [["test"]],
        "active": [True],
        "discriminator": ["transaction_categories"]
    })

    with patch.object(repo_instance, "get_records_from_attributes", return_value=test_data):
        with patch.object(TransactionCategoriesDTO, "standardized_dataframe") as mock_standardize:
            mock_standardize.return_value = test_data

            # Act
            result = repo_instance.get_record_from_attributes(test_transaction_category_dto)

            # Assert
            assert result is not None
            assert result["name"] == "Test Transaction Category"
            assert result["discriminator"] == "transaction_categories"
            mock_standardize.assert_called_once()


def test_hard_delete_records(repo_instance, mock_connect_deco, mock_db_session):
    """Test hard deletion of records."""
    # Arrange
    test_data = pd.DataFrame({
        "name": ["Type 1", "Type 2"],
        "description": ["Description 1", "Description 2"],
        "tags": [["tag1"], ["tag2"]],
        "active": [True, True],
        "discriminator": ["asset_account_types", "asset_account_types"]
    })

    # Mock the SQLDatabaseConnector properly
    # We need to set the engine attribute before patching methods
    with patch.object(SQLDatabaseConnector, 'engine', create=True, new=MagicMock(spec=Engine)):
        # Mock get_records to return our test data
        with patch.object(repo_instance, "get_records", return_value=test_data):
            # Mock db_inspector to handle primary key inspection
            with patch("papita_txnsmodel.access.base.repository.db_inspector") as mock_inspector:
                # Configure the mock inspector to return primary keys
                mock_primary_key = MagicMock()
                mock_primary_key.name = "name"
                mock_inspector.return_value.primary_key = [mock_primary_key]

                # Act
                # Create a simple query filter that would match what real code expects
                dao = AssetAccountTypesDTO.__dao_type__
                query_filter = dao.name.in_(["Type 1", "Type 2"])  # Simple filter matching names in test data
                result = mock_connect_deco(
                    SQLDatabaseConnector, repo_instance.hard_delete_records
                )(query_filter, dto_type=AssetAccountTypesDTO)

                # Assert
                assert not result.empty
                assert len(result) == 2
                assert mock_db_session.exec.call_count == 2
                mock_db_session.commit.assert_called_once()


# pylint: disable=R0914,W0212
def test_soft_delete_records(repo_instance, mock_connect_deco, mock_db_session):
    """Test soft deletion of records.

    Verifies that soft_delete_records properly marks records as inactive
    instead of removing them from the database.
    """
    # Arrange
    test_data = pd.DataFrame({
        "name": ["Type 1", "Type 2"],
        "description": ["Description 1", "Description 2"],
        "tags": [["tag1"], ["tag2"]],
        "active": [True, True],
        "discriminator": ["transaction_categories", "transaction_categories"]
    })

    # Mock the SQLDatabaseConnector properly
    with patch.object(SQLDatabaseConnector, 'engine', create=True, new=MagicMock(spec=Engine)):
        # Mock get_records to return our test data
        with patch.object(repo_instance, "get_records", return_value=test_data):
            # Mock db_inspector to handle primary key inspection
            with patch("papita_txnsmodel.access.base.repository.db_inspector") as mock_inspector:
                # Configure the mock inspector to return primary keys
                mock_primary_key = MagicMock()
                mock_primary_key.name = "name"
                mock_inspector.return_value.primary_key = [mock_primary_key]

                # Mock datetime.now() to have a deterministic timestamp
                test_timestamp = datetime(2023, 1, 1, 12, 0, 0)
                with patch("papita_txnsmodel.access.base.repository.datetime") as mock_datetime:
                    mock_datetime.now.return_value = test_timestamp

                    # Act
                    # Create a simple query filter that would match what real code expects
                    dao = TransactionCategoriesDTO.__dao_type__
                    query_filter = dao.name.in_(["Type 1", "Type 2"])
                    result = mock_connect_deco(SQLDatabaseConnector, repo_instance.soft_delete_records)(
                        query_filter, dto_type=TransactionCategoriesDTO
                    )

                    # Assert
                    assert not result.empty
                    assert len(result) == 2
                    assert mock_db_session.exec.call_count == 2

                    # Verify the values passed to update
                    update_calls = mock_db_session.exec.call_args_list
                    for call in update_calls:
                        statement = call[0][0]
                        assert "UPDATE" in str(statement)
                        assert "active" in str(statement)
                        assert "deleted_at" in str(statement)

                        # Check that values are properly set in the update statement
                        statement_values = [val.value for val in statement._values.values()]
                        assert False in statement_values  # active = False
                        assert test_timestamp in statement_values  # deleted_at = datetime.now()

                    mock_db_session.commit.assert_called_once()
