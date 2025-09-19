"""
Accounts Repository module.

This module provides a repository for accessing and manipulating Accounts data in the database.
It extends the BaseRepository class with specific functionality for Accounts entities.

Unit tests for the AccountsRepository class in the accounts/repository.py module.

This module contains tests that verify the functionality of the AccountsRepository,
including its ability to connect to a mock DuckDB database for testing purposes,
create test accounts, and properly manage database connections.
"""

from datetime import datetime
import functools
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Optional

import uuid

import pandas as pd
import pytest
from sqlalchemy import Engine
from sqlmodel import Session

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.accounts.repository import AccountsRepository
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.classutils import MetaSingleton


class TestAccountsRepository(AccountsRepository, metaclass=MetaSingleton):
    """Repository for Account entities.

    This class provides methods to access and manipulate Account entities in the database.
    It inherits from BaseRepository and uses the Singleton pattern via MetaSingleton.

    Attributes:
        __expected_dto__: The DTO class used by this repository.
    """

    __expected_dto__ = AccountsDTO

    @classmethod
    def setup_test_db(
        cls, db_path: Optional[str] = None, connector: type[SQLDatabaseConnector] | None = None
    ) -> "TestAccountsRepository":
        """Sets up a DuckDB database for testing purposes.

        This method initializes a connection to a DuckDB database that can be used
        for testing. If no db_path is provided, it creates a temporary database.

        Args:
            db_path: Optional path to the DuckDB database file. If None, a temporary
                    file will be created.

        Returns:
            AccountsRepository: The repository instance connected to the test database.

        Examples:
            >>> # Create a repository with a temporary test database
            >>> repo = AccountsRepository.setup_test_db()
            >>>
            >>> # Create a repository with a specific test database file
            >>> repo = AccountsRepository.setup_test_db("/path/to/test.duckdb")
        """
        # Create a temporary file if no path is provided
        if db_path is None:
            temp_dir = tempfile.mkdtemp()
            db_path = Path(temp_dir) / "test_accounts.duckdb"

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

        Examples:
            >>> repo = AccountsRepository.setup_test_db()
            >>> # Run tests...
            >>> repo.teardown_test_db()
        """
        return (connector or SQLDatabaseConnector).close()

    def create_test_account(self, **kwargs) -> AccountsDTO:
        """Creates a test account in the database.

        This helper method simplifies creating test accounts with sensible defaults.

        Args:
            **kwargs: Overrides for the default account attributes.

        Returns:
            AccountsDTO: The created account DTO.

        Examples:
            >>> repo = AccountsRepository.setup_test_db()
            >>> account = repo.create_test_account(name="Test Account")
        """
        # Create account with defaults that can be overridden
        defaults = {
            "name": "Test Account",
            "description": "Account created for testing purposes",
            "tags": ["test"],
            "active": True
        }

        # Override defaults with any provided kwargs
        account_data = {**defaults, **kwargs}
        account = AccountsDTO(**account_data)

        # Save to database
        return self.upsert_record(account)  # pylint: disable=E1125


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
    """Provides an instance of AccountsRepository without database connection.

    Returns:
        AccountsRepository: An instance of the repository.
    """
    # Create a repository instance without calling setup_test_db
    return TestAccountsRepository()


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
        yield TestAccountsRepository, mock_connector


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
def test_account_dto():
    """Creates a test account DTO.

    Returns:
        AccountsDTO: A DTO with test data.
    """
    return AccountsDTO(
        id=uuid.uuid4(),
        name="Test Account",
        description="Test description",
        tags=["test"],
        active=True,
        start_ts=datetime.now()
    )


@pytest.fixture
def mock_upsert_record():
    """Provides a mock for the upsert_record method.

    Returns:
        MagicMock: A mock for the upsert_record method.
    """
    with patch.object(AccountsRepository, "upsert_record") as mock_upsert:
        mock_upsert.return_value = AccountsDTO(
            name="Test Account",
            description="Account created for testing purposes",
            tags=["test"],
            active=True
        )
        yield mock_upsert


@pytest.fixture
def mock_connect_deco(mock_db_session):
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
    assert TestAccountsRepository.__expected_dto__ == AccountsDTO


def test_setup_test_db_with_path(mock_sql_connector, mock_temp_dir):
    """Test setup_test_db method with a specific database path."""
    # Arrange
    db_path = os.path.join(mock_temp_dir, "test.duckdb")

    # Act
    repo = TestAccountsRepository.setup_test_db(db_path=db_path, connector=mock_sql_connector)

    # Assert
    assert issubclass(repo, AccountsRepository)
    mock_sql_connector.establish.assert_called_once()
    # Verify the connection arguments
    call_args = mock_sql_connector.establish.call_args
    assert call_args[1]["connection"] == db_path
    assert "sql_kwargs" in call_args[1]
    assert call_args[1]["sql_kwargs"]["connect_args"]["read_only"] is False


def test_setup_test_db_without_path(mock_sql_connector):
    """Test setup_test_db method without specifying a database path."""
    # Act

    repo = TestAccountsRepository.setup_test_db(connector=mock_sql_connector)

    # Assert
    assert issubclass(repo, AccountsRepository)
    mock_sql_connector.establish.assert_called_once()
    # Verify a path was automatically created
    call_args = mock_sql_connector.establish.call_args
    assert isinstance(call_args[1]["connection"], str)
    assert "test_accounts.duckdb" in call_args[1]["connection"]


def test_teardown_test_db(mock_sql_connector):
    """Test that teardown_test_db calls the close method on SQLDatabaseConnector."""
    # Arrange
    repo = TestAccountsRepository()

    # Act
    repo.teardown_test_db(connector=mock_sql_connector)

    # Assert
    mock_sql_connector.close.assert_called_once()


def test_create_test_account_with_defaults(repo_instance, mock_upsert_record):
    """Test creating a test account with default values."""
    # Act
    account = repo_instance.create_test_account()

    # Assert
    mock_upsert_record.assert_called_once()
    dto = mock_upsert_record.call_args[0][0]
    assert dto.name == "Test Account"
    assert dto.description == "Account created for testing purposes"
    assert dto.tags == ["test"]
    assert dto.active is True
    assert account == mock_upsert_record.return_value


def test_create_test_account_with_custom_values(repo_instance, mock_upsert_record):
    """Test creating a test account with custom values."""
    # Arrange
    custom_values = {
        "name": "Custom Account",
        "description": "Custom description",
        "tags": ["custom", "test"],
        "active": False
    }

    # Act
    account = repo_instance.create_test_account(**custom_values)

    # Assert
    mock_upsert_record.assert_called_once()
    dto = mock_upsert_record.call_args[0][0]
    assert dto.name == custom_values["name"]
    assert dto.description == custom_values["description"]
    assert dto.tags == custom_values["tags"]
    assert dto.active is custom_values["active"]
    assert account == mock_upsert_record.return_value


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


def test_get_records(repo_instance, mock_db_session):
    """Test retrieving records with the get_records method."""
    # Arrange
    test_data = pd.DataFrame({
        "id": [uuid.uuid4(), uuid.uuid4()],
        "name": ["Account 1", "Account 2"],
        "description": ["Description 1", "Description 2"],
        "tags": [["tag1"], ["tag2"]],
        "active": [True, True]
    })

    with patch.object(repo_instance, "run_query", return_value=test_data):
        # Act
        result = repo_instance.get_records(dto_type=AccountsDTO)

        # Assert
        assert not result.empty
        assert len(result) == 2
        assert list(result["name"]) == ["Account 1", "Account 2"]


def test_get_records_empty_result(repo_instance):
    """Test retrieving records with no results."""
    # Arrange
    with patch.object(repo_instance, "run_query", return_value=pd.DataFrame()):
        # Act
        result = repo_instance.get_records(dto_type=AccountsDTO)

        # Assert
        assert result.empty


def test_get_record_by_id(repo_instance, test_account_dto):
    """Test retrieving a record by ID."""
    # Arrange
    test_id = test_account_dto.id
    test_data = pd.DataFrame({
        "id": [test_id],
        "name": ["Test Account"],
        "description": ["Test description"],
        "tags": [["test"]],
        "active": [True]
    })

    with patch.object(repo_instance, "get_records", return_value=test_data):
        with patch.object(AccountsDTO, "standardized_dataframe") as mock_standardize:
            mock_standardize.return_value = test_data

            # Act
            result = repo_instance.get_record_by_id(test_id, AccountsDTO)

            # Assert
            assert result is not None
            assert result["id"] == test_id
            assert result["name"] == "Test Account"
            mock_standardize.assert_called_once()


def test_get_record_by_id_string(repo_instance, test_account_dto):
    """Test retrieving a record by ID when providing a string UUID."""
    # Arrange
    test_id = str(test_account_dto.id)
    test_data = pd.DataFrame({
        "id": [uuid.UUID(test_id)],
        "name": ["Test Account"],
        "description": ["Test description"],
        "tags": [["test"]],
        "active": [True]
    })

    with patch.object(repo_instance, "get_records", return_value=test_data):
        with patch.object(AccountsDTO, "standardized_dataframe") as mock_standardize:
            mock_standardize.return_value = test_data

            # Act
            result = repo_instance.get_record_by_id(test_id, AccountsDTO)

            # Assert
            assert result is not None
            assert str(result["id"]) == test_id
            mock_standardize.assert_called_once()


def test_get_record_by_id_not_found(repo_instance):
    """Test retrieving a record by ID when the record doesn't exist."""
    # Arrange
    test_id = uuid.uuid4()

    with patch.object(repo_instance, "get_records", return_value=pd.DataFrame()):
        # Act
        result = repo_instance.get_record_by_id(test_id, AccountsDTO)

        # Assert
        assert result is None


def test_get_records_from_attributes(repo_instance, test_account_dto):
    """Test retrieving records based on entity attributes."""
    # Arrange
    test_data = pd.DataFrame({
        "id": [test_account_dto.id],
        "name": ["Test Account"],
        "description": ["Test description"],
        "tags": [["test"]],
        "active": [True]
    })

    with patch.object(repo_instance, "get_records", return_value=test_data):
        # Act
        result = repo_instance.get_records_from_attributes(test_account_dto)

        # Assert
        assert not result.empty
        assert len(result) == 1
        assert result.iloc[0]["name"] == "Test Account"


def test_get_record_from_attributes(repo_instance, test_account_dto):
    """Test retrieving a single record based on entity attributes."""
    # Arrange
    test_data = pd.DataFrame({
        "id": [test_account_dto.id],
        "name": ["Test Account"],
        "description": ["Test description"],
        "tags": [["test"]],
        "active": [True]
    })

    with patch.object(repo_instance, "get_records_from_attributes", return_value=test_data):
        with patch.object(AccountsDTO, "standardized_dataframe") as mock_standardize:
            mock_standardize.return_value = test_data

            # Act
            result = repo_instance.get_record_from_attributes(test_account_dto)

            # Assert
            assert result is not None
            assert result["name"] == "Test Account"
            mock_standardize.assert_called_once()


def test_get_record_from_attributes_not_found(repo_instance, test_account_dto):
    """Test retrieving a record by attributes when the record doesn't exist."""
    # Arrange
    with patch.object(repo_instance, "get_records_from_attributes", return_value=pd.DataFrame()):
        # Act
        result = repo_instance.get_record_from_attributes(test_account_dto)

        # Assert
        assert result is None


def test_hard_delete_records(repo_instance, mock_connect_deco, mock_db_session):
    """Test hard deletion of records."""
    # Arrange
    test_ids = [uuid.uuid4(), uuid.uuid4()]
    test_data = pd.DataFrame({
        "id": test_ids,
        "name": ["Account 1", "Account 2"],
        "description": ["Description 1", "Description 2"],
        "tags": [["tag1"], ["tag2"]],
        "active": [True, True]
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
                mock_primary_key.name = "id"
                mock_inspector.return_value.primary_key = [mock_primary_key]

                # Act
                # Create a simple query filter that would match what real code expects
                dao = AccountsDTO.__dao_type__
                query_filter = dao.id.in_(test_ids)  # Simple filter matching IDs in test data
                result = mock_connect_deco(
                    SQLDatabaseConnector, repo_instance.hard_delete_records
                )(query_filter, dto_type=AccountsDTO)

                # Assert
                assert not result.empty
                assert len(result.index) == 2
                assert mock_db_session.exec.call_count == 2
                mock_db_session.commit.assert_called_once()


# pylint: disable=R0914,W0212
def test_soft_delete_records(repo_instance, mock_connect_deco, mock_db_session):
    """Test soft deletion of records.

    Verifies that soft_delete_records properly marks records as inactive
    instead of removing them from the database.
    """
    # Arrange
    test_ids = [uuid.uuid4(), uuid.uuid4()]
    test_data = pd.DataFrame({
        "id": test_ids,
        "name": ["Account 1", "Account 2"],
        "description": ["Description 1", "Description 2"],
        "tags": [["tag1"], ["tag2"]],
        "active": [True, True]
    })

    # Mock the SQLDatabaseConnector properly
    with patch.object(SQLDatabaseConnector, 'engine', create=True, new=MagicMock(spec=Engine)):
        # Mock get_records to return our test data
        with patch.object(repo_instance, "get_records", return_value=test_data):
            # Mock db_inspector to handle primary key inspection
            with patch("papita_txnsmodel.access.base.repository.db_inspector") as mock_inspector:
                # Configure the mock inspector to return primary keys
                mock_primary_key = MagicMock()
                mock_primary_key.name = "id"
                mock_inspector.return_value.primary_key = [mock_primary_key]

                # Mock datetime.now() to have a deterministic timestamp
                test_timestamp = datetime(2023, 1, 1, 12, 0, 0)
                with patch("papita_txnsmodel.access.base.repository.datetime") as mock_datetime:
                    mock_datetime.now.return_value = test_timestamp

                    # Act
                    # Create a simple query filter that would match what real code expects
                    dao = AccountsDTO.__dao_type__
                    query_filter = dao.id.in_(test_ids)
                    result = mock_connect_deco(SQLDatabaseConnector, repo_instance.soft_delete_records)(
                        query_filter, dto_type=AccountsDTO
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


# pylint: disable=W0212
def test_soft_delete_records_empty_results(repo_instance, mock_connect_deco, mock_db_session):
    """Test soft deletion when no records match the query.

    Verifies appropriate behavior when attempting to soft delete records
    that don't exist.
    """
    # Arrange
    empty_data = pd.DataFrame([])

    # Mock get_records to return empty DataFrame
    with patch.object(SQLDatabaseConnector, 'engine', create=True, new=MagicMock(spec=Engine)):
        with patch.object(repo_instance, "get_records", return_value=empty_data):
            with patch.object(SQLDatabaseConnector, "connect"):
                # Act
                dao = AccountsDTO.__dao_type__
                query_filter = dao.id == uuid.uuid4()  # Query that won't match anything
                result = mock_connect_deco(SQLDatabaseConnector, repo_instance.soft_delete_records)(
                    query_filter, dto_type=AccountsDTO, _testing_=True
                )

                # Assert
                assert result.empty
                mock_db_session.exec.assert_not_called()
                mock_db_session.commit.assert_not_called()


def test_soft_delete_records_exception_handling(repo_instance, mock_connect_deco, mock_db_session):
    """Test exception handling during soft deletion.

    Verifies that exceptions during soft deletion are properly caught,
    logged, and session is rolled back.
    """
    # Arrange
    test_ids = [uuid.uuid4()]
    test_data = pd.DataFrame({
        "id": test_ids,
        "name": ["Account 1"],
        "description": ["Description 1"],
        "tags": [["tag1"]],
        "active": [True]
    })

    # Mock the SQLDatabaseConnector
    with patch.object(SQLDatabaseConnector, 'engine', create=True, new=MagicMock(spec=Engine)):
        # Mock get_records to return test data
        with patch.object(repo_instance, "get_records", return_value=test_data):
            # Mock db_inspector
            with patch("papita_txnsmodel.access.base.repository.db_inspector") as mock_inspector:
                mock_primary_key = MagicMock()
                mock_primary_key.name = "id"
                mock_inspector.return_value.primary_key = [mock_primary_key]

                # Setup session to raise exception on exec
                mock_db_session.exec.side_effect = Exception("Database error")

                # Mock logger to check it's being called
                with patch("papita_txnsmodel.access.base.repository.logger") as mock_logger:
                    # Replace the @connect decorator
                    with patch.object(SQLDatabaseConnector, "connect"):
                        # Act
                        dao = AccountsDTO.__dao_type__
                        query_filter = dao.id.in_(test_ids)
                        result = mock_connect_deco(SQLDatabaseConnector, repo_instance.soft_delete_records)(
                            query_filter, dto_type=AccountsDTO, _testing_=True
                        )

                        # Assert
                        # Verify we still get the test data back
                        assert not result.empty
                        assert len(result) == 1

                        # Verify exception handling behavior
                        mock_logger.exception.assert_called_once()
                        mock_db_session.rollback.assert_called_once()
                        mock_db_session.commit.assert_not_called()


def test_hard_delete_records_exception_handling(repo_instance, mock_connect_deco, mock_db_session):
    """Test exception handling during hard deletion.

    Verifies that exceptions during hard deletion are properly caught,
    logged, and session is rolled back.
    """
    # Arrange
    test_ids = [uuid.uuid4()]
    test_data = pd.DataFrame({
        "id": test_ids,
        "name": ["Account 1"],
        "description": ["Description 1"],
        "tags": [["tag1"]],
        "active": [True]
    })

    # Mock the SQLDatabaseConnector
    with patch.object(SQLDatabaseConnector, 'engine', create=True, new=MagicMock(spec=Engine)):
        # Mock get_records to return test data
        with patch.object(repo_instance, "get_records", return_value=test_data):
            # Mock db_inspector
            with patch("papita_txnsmodel.access.base.repository.db_inspector") as mock_inspector:
                mock_primary_key = MagicMock()
                mock_primary_key.name = "id"
                mock_inspector.return_value.primary_key = [mock_primary_key]

                # Setup session to raise exception on exec
                mock_db_session.exec.side_effect = Exception("Database error")

                # Mock logger to check it's being called
                with patch("papita_txnsmodel.access.base.repository.logger") as mock_logger:
                    # Replace the @connect decorator
                    with patch.object(SQLDatabaseConnector, "connect"):
                        # Act
                        dao = AccountsDTO.__dao_type__
                        query_filter = dao.id.in_(test_ids)
                        result = mock_connect_deco(SQLDatabaseConnector, repo_instance.hard_delete_records)(
                            query_filter, dto_type=AccountsDTO, _testing_=True
                        )

                        # Assert
                        # Verify we still get the test data back
                        assert not result.empty
                        assert len(result) == 1

                        # Verify exception handling behavior
                        mock_logger.exception.assert_called_once()
                        mock_db_session.rollback.assert_called_once()
                        mock_db_session.commit.assert_not_called()


def test_hard_delete_records_empty_results(repo_instance, mock_connect_deco, mock_db_session):
    """Test hard deletion when no records match the query.

    Verifies appropriate behavior when attempting to hard delete records
    that don't exist.
    """
    # Arrange
    empty_data = pd.DataFrame([])

    # Mock get_records to return empty DataFrame
    with patch.object(SQLDatabaseConnector, 'engine', create=True, new=MagicMock(spec=Engine)):
        with patch.object(repo_instance, "get_records", return_value=empty_data):
            with patch.object(SQLDatabaseConnector, "connect"):
                # Act
                dao = AccountsDTO.__dao_type__
                query_filter = dao.id == uuid.uuid4()  # Query that won't match anything
                result = mock_connect_deco(SQLDatabaseConnector, repo_instance.hard_delete_records)(
                    query_filter, dto_type=AccountsDTO, _testing_=True
                )

                # Assert
                assert result.empty
                mock_db_session.exec.assert_not_called()
                mock_db_session.commit.assert_not_called()
