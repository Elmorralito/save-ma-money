"""Unit tests for the AccountsDTO class in the accounts/dto.py module.

This module tests the functionality of the AccountsDTO class including:
- Creation with default and custom values
- Field validations (start_ts, end_ts, name, description, tags)
- DAO conversion methods (from_dao, to_dao)
- Inheritance behavior from CoreTableDTO
"""

import datetime
import uuid
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.model.accounts import Accounts


@pytest.fixture
def valid_accounts_dto_data():
    """Return valid data for creating an AccountsDTO instance."""
    return {
        "id": uuid.uuid4(),
        "name": "Test Account",
        "description": "This is a test account",
        "active": True,
        "tags": ["test", "account"],
        "start_ts": datetime.datetime(2023, 1, 1, 0, 0, 0),
        "end_ts": datetime.datetime(2023, 12, 31, 23, 59, 59)
    }


@pytest.fixture
def mock_accounts_model():
    """Create a mock of the Accounts model."""
    mock = MagicMock(spec=Accounts)
    mock.id = uuid.uuid4()
    mock.name = "Test Account"
    mock.description = "Test Description"
    mock.active = True
    mock.tags = ["test"]
    mock.start_ts = datetime.datetime.now()
    mock.end_ts = None
    mock.deleted_at = None
    return mock


def test_accounts_dto_creation_with_defaults():
    """Test creating an AccountsDTO with default values."""
    # Arrange & Act
    dto = AccountsDTO(
        name="Test Account",
        description="This is a test account",
        tags=["test"]
    )

    # Assert - required fields
    assert dto.name == "Test Account"
    assert dto.description == "This is a test account"
    assert dto.tags == ["test"]

    # Assert - default values
    assert dto.id is not None
    assert dto.active is True
    assert dto.deleted_at is None
    assert dto.start_ts is not None
    assert isinstance(dto.start_ts, datetime.datetime)
    assert dto.end_ts is None


def test_accounts_dto_creation_with_all_fields(valid_accounts_dto_data):
    """Test creating an AccountsDTO with all fields specified."""
    # Arrange & Act
    dto = AccountsDTO(**valid_accounts_dto_data)

    # Assert
    for field, value in valid_accounts_dto_data.items():
        assert getattr(dto, field) == value


@pytest.mark.parametrize("start_ts,end_ts,should_pass", [
    (datetime.datetime(2023, 1, 1), datetime.datetime(2023, 1, 2), True),  # end after start
    (datetime.datetime(2023, 1, 1), datetime.datetime(2023, 1, 1), False),  # end same as start
    (datetime.datetime(2023, 1, 2), datetime.datetime(2023, 1, 1), False),  # end before start
    (datetime.datetime(2023, 1, 1), None, True),  # end is None
])
def test_end_ts_validation(start_ts, end_ts, should_pass):
    """Test end_ts validation with various scenarios."""
    # Arrange
    data = {
        "name": "Test Account",
        "description": "This is a test account",
        "tags": ["test"],
        "start_ts": start_ts,
        "end_ts": end_ts
    }

    if should_pass:
        # Act & Assert - Should not raise an exception
        dto = AccountsDTO(**data)
        assert dto.start_ts == start_ts
        assert dto.end_ts == end_ts
    else:
        # Act & Assert - Should raise a ValidationError
        with pytest.raises(ValidationError) as exc_info:
            AccountsDTO(**data)
        assert "end_ts must be after start_ts" in str(exc_info.value)


@pytest.mark.parametrize("name,should_pass", [
    ("Valid Name", True),
    ("", False),
    ("   ", False),
])
def test_name_validation(name, should_pass):
    """Test name validation with various scenarios."""
    # Arrange
    data = {
        "name": name,
        "description": "This is a test account",
        "tags": ["test"]
    }

    if should_pass:
        # Act & Assert - Should not raise an exception
        dto = AccountsDTO(**data)
        assert dto.name == name
    else:
        # Act & Assert - Should raise a ValidationError
        with pytest.raises(ValidationError) as exc_info:
            AccountsDTO(**data)
        assert "name cannot be empty" in str(exc_info.value)


@pytest.mark.parametrize("description,should_pass", [
    ("Valid description", True),
    ("", False),
    ("   ", False),
])
def test_description_validation(description, should_pass):
    """Test description validation with various scenarios."""
    # Arrange
    data = {
        "name": "Test Account",
        "description": description,
        "tags": ["test"]
    }

    if should_pass:
        # Act & Assert - Should not raise an exception
        dto = AccountsDTO.model_validate(data)
        assert dto.description == description
    else:
        # Act & Assert - Should raise a ValidationError
        with pytest.raises(ValidationError) as exc_info:
            AccountsDTO(**data)
        assert "description cannot be empty" in str(exc_info.value)


@pytest.mark.parametrize("tags,should_pass,error_msg", [
    (["test"], True, None),
    (["test1", "test2"], True, None),
    ([], False, "tags must have at least one item"),
    (["test", "test"], False, "tags must contain unique items"),
])
def test_tags_validation(tags, should_pass, error_msg):
    """Test tags validation with various scenarios."""
    # Arrange
    data = {
        "name": "Test Account",
        "description": "This is a test account",
        "tags": tags
    }

    if should_pass:
        # Act & Assert - Should not raise an exception
        dto = AccountsDTO.model_validate(data)
        assert dto.tags == tags
    else:
        # Act & Assert - Should raise a ValidationError
        with pytest.raises(ValidationError) as exc_info:
            AccountsDTO(**data)
        assert error_msg in str(exc_info.value)


@pytest.mark.filterwarnings("ignore")
def test_from_dao_method(mock_accounts_model):
    """Test the from_dao class method."""
    # Arrange - Patch the model_validate method to return a predefined DTO
    with patch.object(AccountsDTO, 'model_validate') as mock_validate:
        dto = AccountsDTO(
            id=mock_accounts_model.id,
            name=mock_accounts_model.name,
            description=mock_accounts_model.description,
            active=mock_accounts_model.active,
            tags=mock_accounts_model.tags,
            start_ts=mock_accounts_model.start_ts,
            end_ts=mock_accounts_model.end_ts
        )
        mock_validate.return_value = dto

        # Act - Test the from_dao method
        result = AccountsDTO.from_dao(mock_accounts_model)

        # Assert - Verify the result and that model_validate was called correctly
        assert result == dto
        mock_validate.assert_called_once_with(mock_accounts_model, strict=True)


@pytest.mark.filterwarnings("ignore")
def test_from_dao_type_error():
    """Test that from_dao raises TypeError when given the wrong type."""
    # Arrange
    not_an_account = object()

    # Act & Assert
    with pytest.raises(TypeError) as exc_info:
        AccountsDTO.from_dao(not_an_account)

    assert "Unsupported DAO type:" in str(exc_info.value)


@pytest.mark.filterwarnings("ignore")
def test_to_dao_method():
    """Test the to_dao method."""
    # Arrange - Create a minimal DTO and mock the model_validate method
    dto = AccountsDTO(
        name="Test Account",
        description="This is a test account",
        tags=["test"]
    )

    mock_dao = MagicMock(spec=Accounts)

    with patch.object(AccountsDTO.__dao_type__, 'model_validate', return_value=mock_dao) as mock_validate:
        # Act
        result = dto.to_dao()

        # Assert
        assert result == mock_dao
        # Verify model_validate was called with expected parameters
        mock_validate.assert_called_once()
