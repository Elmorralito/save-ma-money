"""Unit tests for the TypesDTO class in the types/dto.py module.

This module tests the functionality of the TypesDTO class including:
- Creation with default and custom values
- Field validations (discriminator, name, description, tags)
- DAO conversion methods (from_dao, to_dao)
- Inheritance behavior from CoreTableDTO
- Row property method
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from papita_txnsmodel.access.types.dto import TypesDTO
from papita_txnsmodel.model.types import Types


@pytest.fixture
def valid_types_dto_data():
    """Return valid data for creating a TypesDTO instance."""
    return {
        "id": uuid.uuid4(),
        "name": "Test Type",
        "description": "This is a test type",
        "active": True,
        "tags": ["test", "type"],
        "discriminator": "assets"
    }


@pytest.fixture
def mock_types_model():
    """Create a mock of the Types model."""
    mock = MagicMock(spec=Types)
    mock.id = uuid.uuid4()
    mock.name = "Test Type"
    mock.description = "Test Description"
    mock.active = True
    mock.tags = ["test"]
    mock.discriminator = "assets"
    mock.deleted_at = None
    return mock


def test_types_dto_creation_with_defaults():
    """Test creating a TypesDTO with minimal required values."""
    # Arrange & Act
    dto = TypesDTO(
        name="Test Type",
        description="This is a test type",
        tags=["test"],
        discriminator="assets"
    )

    # Assert - required fields
    assert dto.name == "Test Type"
    assert dto.description == "This is a test type"
    assert dto.tags == ["test"]
    assert dto.discriminator == "assets"

    # Assert - default values
    assert dto.id is not None
    assert dto.active is True
    assert dto.deleted_at is None


def test_types_dto_creation_with_all_fields(valid_types_dto_data):
    """Test creating a TypesDTO with all fields specified."""
    # Arrange & Act
    dto = TypesDTO(**valid_types_dto_data)

    # Assert
    for field, value in valid_types_dto_data.items():
        assert getattr(dto, field) == value


@pytest.mark.parametrize("discriminator,should_pass", [
    ("assets", True),
    ("liabilities", True),
    ("transactions", True),
    ("invalid", False),
    ("ASSETS", False),  # Case sensitive check
])
def test_discriminator_validation(discriminator, should_pass):
    """Test discriminator validation with various scenarios."""
    # Arrange
    data = {
        "name": "Test Type",
        "description": "This is a test type",
        "tags": ["test"],
        "discriminator": discriminator
    }

    if should_pass:
        # Act & Assert - Should not raise an exception
        dto = TypesDTO(**data)
        assert dto.discriminator == discriminator
    else:
        # Act & Assert - Should raise a ValidationError
        with pytest.raises(ValidationError) as exc_info:
            TypesDTO(**data)
        assert "Input should be 'assets', 'liabilities' or 'transactions'" in str(exc_info.value)


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
        "description": "This is a test type",
        "tags": ["test"],
        "discriminator": "assets"
    }

    if should_pass:
        # Act & Assert - Should not raise an exception
        dto = TypesDTO(**data)
        assert dto.name == name
    else:
        # Act & Assert - Should raise a ValidationError
        with pytest.raises(ValidationError) as exc_info:
            TypesDTO(**data)
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
        "name": "Test Type",
        "description": description,
        "tags": ["test"],
        "discriminator": "assets"
    }

    if should_pass:
        # Act & Assert - Should not raise an exception
        dto = TypesDTO(**data)
        assert dto.description == description
    else:
        # Act & Assert - Should raise a ValidationError
        with pytest.raises(ValidationError) as exc_info:
            TypesDTO(**data)
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
        "name": "Test Type",
        "description": "This is a test type",
        "tags": tags,
        "discriminator": "assets"
    }

    if should_pass:
        # Act & Assert - Should not raise an exception
        dto = TypesDTO(**data)
        assert dto.tags == tags
    else:
        # Act & Assert - Should raise a ValidationError
        with pytest.raises(ValidationError) as exc_info:
            TypesDTO(**data)
        assert error_msg in str(exc_info.value)


def test_row_property():
    """Test the row property method."""
    # Arrange
    dto = TypesDTO(
        name="Test Type",
        description="This is a test type",
        tags=["test"],
        discriminator="assets",
        custom_field="custom_value"  # Extra field allowed by model_config
    )

    # Act
    row_data = dto.row

    # Assert
    assert isinstance(row_data, dict)
    assert row_data["name"] == "Test Type"
    assert row_data["description"] == "This is a test type"
    assert row_data["tags"] == ["test"]
    assert row_data["discriminator"] == "assets"
    assert row_data["custom_field"] == "custom_value"  # Extra field should be included


@pytest.mark.filterwarnings("ignore")
def test_from_dao_method(mock_types_model):
    """Test the from_dao class method."""
    # Arrange - Patch the model_validate method to return a predefined DTO
    with patch.object(TypesDTO, 'model_validate') as mock_validate:
        dto = TypesDTO(
            id=mock_types_model.id,
            name=mock_types_model.name,
            description=mock_types_model.description,
            active=mock_types_model.active,
            tags=mock_types_model.tags,
            discriminator=mock_types_model.discriminator
        )
        mock_validate.return_value = dto

        # Act - Test the from_dao method
        result = TypesDTO.from_dao(mock_types_model)

        # Assert - Verify the result and that model_validate was called correctly
        assert result == dto
        mock_validate.assert_called_once_with(mock_types_model, strict=True)


@pytest.mark.filterwarnings("ignore")
def test_from_dao_type_error():
    """Test that from_dao raises TypeError when given the wrong type."""
    # Arrange
    not_a_type = object()

    # Act & Assert
    with pytest.raises(TypeError) as exc_info:
        TypesDTO.from_dao(not_a_type)

    assert "Unsupported DAO type:" in str(exc_info.value)


@pytest.mark.filterwarnings("ignore")
def test_to_dao_method():
    """Test the to_dao method."""
    # Arrange - Create a minimal DTO and mock the model_validate method
    dto = TypesDTO(
        name="Test Type",
        description="This is a test type",
        tags=["test"],
        discriminator="assets"
    )

    mock_dao = MagicMock(spec=Types)

    with patch.object(TypesDTO.__dao_type__, 'model_validate', return_value=mock_dao) as mock_validate:
        # Act
        result = dto.to_dao()

        # Assert
        assert result == mock_dao
        # Verify model_validate was called with expected parameters
        mock_validate.assert_called_once()


def test_extra_fields_allowed():
    """Test that extra fields are allowed in the TypesDTO."""
    # Arrange & Act
    dto = TypesDTO(
        name="Test Type",
        description="This is a test type",
        tags=["test"],
        discriminator="assets",
        custom_field1="value1",
        custom_field2=123
    )

    # Assert
    assert dto.custom_field1 == "value1"
    assert dto.custom_field2 == 123


@pytest.mark.parametrize("discriminator", ["assets", "liabilities", "transactions"])
def test_all_valid_discriminator_values(discriminator):
    """Test that all valid discriminator values are accepted."""
    # Arrange & Act
    dto = TypesDTO(
        name="Test Type",
        description="This is a test type",
        tags=["test"],
        discriminator=discriminator
    )

    # Assert
    assert dto.discriminator == discriminator
