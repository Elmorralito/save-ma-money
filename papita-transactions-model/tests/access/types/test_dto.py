"""Unit tests for the DTO classes in the types/dto.py module.

This module tests the functionality of the TypesDTO class and its subclasses including:
- Creation with default and custom values for each DTO type
- Row property behavior including discriminator handling
- Discriminated type model functionality
- DAO conversion methods (from_dao, to_dao)
- Type validation and error handling
- DTO_TYPES collection completeness
"""

import inspect
import sys
from typing import Literal
import uuid
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from papita_txnsmodel.access.types.dto import (
    AssetAccountTypesDTO,
    DTO_TYPES,
    DiscriminatedTypesModel,
    LiabilityAccountTypesDTO,
    TransactionCategoriesDTO,
    TypesDTO,
)
from papita_txnsmodel.model.types import (
    AssetAccountTypes,
    LiabilityAccountTypes,
    TransactionCategories,
)


@pytest.fixture
def valid_asset_account_types_data():
    """Return valid data for creating an AssetAccountTypesDTO instance."""
    return {
        "id": uuid.uuid4(),
        "name": "Cash",
        "description": "Cash account type",
        "tags": ["test"],
        "discriminator": "asset_account_types",
        # Add other fields that might be needed
    }


@pytest.fixture
def valid_liability_account_types_data():
    """Return valid data for creating a LiabilityAccountTypesDTO instance."""
    return {
        "id": uuid.uuid4(),
        "name": "Credit Card",
        "description": "Credit card liability type",
        "tags": ["test"],
        "discriminator": "liability_account_types",
        # Add other fields that might be needed
    }


@pytest.fixture
def valid_transaction_categories_data():
    """Return valid data for creating a TransactionCategoriesDTO instance."""
    return {
        "id": uuid.uuid4(),
        "name": "Groceries",
        "description": "Grocery shopping expenses",
        "tags": ["test"],
        "discriminator": "transaction_categories",
        # Add other fields that might be needed
    }


@pytest.fixture
def mock_asset_account_types():
    """Create a mock of the AssetAccountTypes model."""
    mock = MagicMock(spec=AssetAccountTypes)
    mock.id = uuid.uuid4()
    mock.name = "Cash"
    mock.description = "Cash account type"
    # Set other attributes that might be needed
    return mock


@pytest.fixture
def mock_liability_account_types():
    """Create a mock of the LiabilityAccountTypes model."""
    mock = MagicMock(spec=LiabilityAccountTypes)
    mock.id = uuid.uuid4()
    mock.name = "Credit Card"
    mock.description = "Credit card liability type"
    # Set other attributes that might be needed
    return mock


@pytest.fixture
def mock_transaction_categories():
    """Create a mock of the TransactionCategories model."""
    mock = MagicMock(spec=TransactionCategories)
    mock.id = uuid.uuid4()
    mock.name = "Groceries"
    mock.description = "Grocery shopping expenses"
    # Set other attributes that might be needed
    return mock

@pytest.fixture
def mock_test_types_parameters():
    return {
        "description": "test", "tags": ["test"], "name": "Test"
    }


def test_types_dto_row_property(mock_test_types_parameters):
    """Test the row property of TypesDTO includes the discriminator field."""
    # Arrange
    class TestTypesDTO(TypesDTO):
        discriminator: Literal["test_types"]
        name: str = "Test"

    dto = TestTypesDTO(discriminator="test_types", **mock_test_types_parameters)

    # Act
    row_dict = dto.row

    # Assert
    assert "discriminator" in row_dict
    assert row_dict["discriminator"] == "test_types"
    assert row_dict["name"] == "Test"


def test_asset_account_types_dto_creation(mock_test_types_parameters):
    """Test creating an AssetAccountTypesDTO with basic values."""
    # Arrange & Act
    dto = AssetAccountTypesDTO(discriminator="asset_account_types", **mock_test_types_parameters)

    # Assert
    assert dto.name == "Test"
    assert dto.description == "test"
    assert dto.discriminator == "asset_account_types"


def test_liability_account_types_dto_creation(mock_test_types_parameters):
    """Test creating a LiabilityAccountTypesDTO with basic values."""
    # Arrange & Act
    dto = LiabilityAccountTypesDTO(discriminator="liability_account_types", **mock_test_types_parameters)

    # Assert
    assert dto.name == "Test"
    assert dto.description == "test"
    assert dto.discriminator == "liability_account_types"


def test_transaction_categories_dto_creation(mock_test_types_parameters):
    """Test creating a TransactionCategoriesDTO with basic values."""
    # Arrange & Act
    dto = TransactionCategoriesDTO(iscriminator="transaction_categories", **mock_test_types_parameters)

    # Assert
    assert dto.name == "Test"
    assert dto.description == "test"
    assert dto.discriminator == "transaction_categories"


def test_asset_account_types_dto_creation_with_all_fields(valid_asset_account_types_data):
    """Test creating an AssetAccountTypesDTO with all fields specified."""
    # Arrange & Act
    dto = DiscriminatedTypesModel(type_dto=valid_asset_account_types_data)

    # Assert
    assert isinstance(dto, AssetAccountTypes)
    for field, value in valid_asset_account_types_data.items():
        assert getattr(dto, field) == value
    assert dto.discriminator == "asset_account_types"


def test_liability_account_types_dto_creation_with_all_fields(valid_liability_account_types_data):
    """Test creating a LiabilityAccountTypesDTO with all fields specified."""
    # Arrange & Act
    dto = DiscriminatedTypesModel(type_dto=valid_liability_account_types_data)

    # Assert
    assert isinstance(dto, LiabilityAccountTypesDTO)
    for field, value in valid_liability_account_types_data.items():
        assert getattr(dto, field) == value
    assert dto.discriminator == "liability_account_types"


def test_transaction_categories_dto_creation_with_all_fields(valid_transaction_categories_data):
    """Test creating a TransactionCategoriesDTO with all fields specified."""
    # Arrange & Act
    dto = DiscriminatedTypesModel(type_dto=valid_transaction_categories_data)

    # Assert
    assert isinstance(dto, TransactionCategoriesDTO)
    for field, value in valid_transaction_categories_data.items():
        assert getattr(dto, field) == value
    assert dto.discriminator == "transaction_categories"


def test_discriminated_types_model_serialization():
    """Test serialization of DiscriminatedTypesModel."""
    # Arrange
    asset_dto = AssetAccountTypesDTO(name="Cash", description="Cash account type")
    model = DiscriminatedTypesModel(type_dto=asset_dto)

    # Act
    model_dict = model.model_dump()

    # Assert
    assert "type_dto" in model_dict
    assert model_dict["type_dto"]["discriminator"] == "asset_account_types"
    assert model_dict["type_dto"]["name"] == "Cash"
    assert model_dict["type_dto"]["description"] == "Cash account type"


@pytest.mark.filterwarnings("ignore")
def test_from_dao_method_for_asset_account_types(mock_asset_account_types):
    """Test the from_dao class method for AssetAccountTypesDTO."""
    # Arrange
    with patch.object(AssetAccountTypesDTO, 'model_validate') as mock_validate:
        dto = AssetAccountTypesDTO(
            id=mock_asset_account_types.id,
            name=mock_asset_account_types.name,
            description=mock_asset_account_types.description,
        )
        mock_validate.return_value = dto

        # Act
        result = AssetAccountTypesDTO.from_dao(mock_asset_account_types)

        # Assert
        assert result == dto
        mock_validate.assert_called_once_with(mock_asset_account_types, strict=True)


@pytest.mark.filterwarnings("ignore")
def test_from_dao_method_for_liability_account_types(mock_liability_account_types):
    """Test the from_dao class method for LiabilityAccountTypesDTO."""
    # Arrange
    with patch.object(LiabilityAccountTypesDTO, 'model_validate') as mock_validate:
        dto = LiabilityAccountTypesDTO(
            id=mock_liability_account_types.id,
            name=mock_liability_account_types.name,
            description=mock_liability_account_types.description,
        )
        mock_validate.return_value = dto

        # Act
        result = LiabilityAccountTypesDTO.from_dao(mock_liability_account_types)

        # Assert
        assert result == dto
        mock_validate.assert_called_once_with(mock_liability_account_types, strict=True)


@pytest.mark.filterwarnings("ignore")
def test_from_dao_method_for_transaction_categories(mock_transaction_categories):
    """Test the from_dao class method for TransactionCategoriesDTO."""
    # Arrange
    with patch.object(TransactionCategoriesDTO, 'model_validate') as mock_validate:
        dto = TransactionCategoriesDTO(
            id=mock_transaction_categories.id,
            name=mock_transaction_categories.name,
            description=mock_transaction_categories.description,
        )
        mock_validate.return_value = dto

        # Act
        result = TransactionCategoriesDTO.from_dao(mock_transaction_categories)

        # Assert
        assert result == dto
        mock_validate.assert_called_once_with(mock_transaction_categories, strict=True)


@pytest.mark.filterwarnings("ignore")
def test_from_dao_type_error_for_asset_account_types():
    """Test that from_dao raises TypeError when given the wrong type for AssetAccountTypesDTO."""
    # Arrange
    not_an_asset_type = object()

    # Act & Assert
    with pytest.raises(TypeError) as exc_info:
        AssetAccountTypesDTO.from_dao(not_an_asset_type)

    assert "Unsupported DAO type:" in str(exc_info.value)


@pytest.mark.filterwarnings("ignore")
def test_to_dao_method_for_asset_account_types():
    """Test the to_dao method for AssetAccountTypesDTO."""
    # Arrange
    dto = AssetAccountTypesDTO(name="Cash", description="Cash account type")
    mock_dao = MagicMock(spec=AssetAccountTypes)

    with patch.object(AssetAccountTypesDTO.__dao_type__, 'model_validate', return_value=mock_dao) as mock_validate:
        # Act
        result = dto.to_dao()

        # Assert
        assert result == mock_dao
        mock_validate.assert_called_once()


@pytest.mark.filterwarnings("ignore")
def test_to_dao_method_for_liability_account_types():
    """Test the to_dao method for LiabilityAccountTypesDTO."""
    # Arrange
    dto = LiabilityAccountTypesDTO(name="Credit Card", description="Credit card liability type")
    mock_dao = MagicMock(spec=LiabilityAccountTypes)

    with patch.object(LiabilityAccountTypesDTO.__dao_type__, 'model_validate', return_value=mock_dao) as mock_validate:
        # Act
        result = dto.to_dao()

        # Assert
        assert result == mock_dao
        mock_validate.assert_called_once()


@pytest.mark.filterwarnings("ignore")
def test_to_dao_method_for_transaction_categories():
    """Test the to_dao method for TransactionCategoriesDTO."""
    # Arrange
    dto = TransactionCategoriesDTO(name="Groceries", description="Grocery shopping expenses")
    mock_dao = MagicMock(spec=TransactionCategories)

    with patch.object(TransactionCategoriesDTO.__dao_type__, 'model_validate', return_value=mock_dao) as mock_validate:
        # Act
        result = dto.to_dao()

        # Assert
        assert result == mock_dao
        mock_validate.assert_called_once()


def test_dto_types_contains_all_subclasses():
    """Test that DTO_TYPES contains all TypesDTO subclasses defined in the module."""
    # Arrange
    expected_subclasses = {
        cls for cls in inspect.getmembers(sys.modules["papita_txnsmodel.access.types.dto"], inspect.isclass)
        if issubclass(cls[1], TypesDTO) and cls[1] != TypesDTO
    }
    expected_subclass_names = {cls_name for cls_name, _ in expected_subclasses}

    # Act
    actual_subclass_names = {cls.__name__ for cls in DTO_TYPES}

    # Assert
    assert actual_subclass_names == expected_subclass_names
    assert "AssetAccountTypesDTO" in actual_subclass_names
    assert "LiabilityAccountTypesDTO" in actual_subclass_names
    assert "TransactionCategoriesDTO" in actual_subclass_names


def test_extra_fields_allowed_in_types_dto():
    """Test that TypesDTO allows extra fields due to ConfigDict(extra='allow')."""
    # Arrange & Act
    dto = AssetAccountTypesDTO(name="Cash", description="Cash account", extra_field="Extra value")

    # Assert
    assert hasattr(dto, "extra_field")
    assert dto.extra_field == "Extra value"
    assert "extra_field" in dto.model_dump()


def test_discriminator_included_in_model_dump():
    """Test that the discriminator is included in the model_dump output."""
    # Arrange
    dto = AssetAccountTypesDTO(name="Cash", description="Cash account type")

    # Act
    dump_dict = dto.model_dump()

    # Assert
    assert "discriminator" in dump_dict
    assert dump_dict["discriminator"] == "asset_account_types"

def test_asset_account_types_dto_creation_with_all_fields(valid_asset_account_types_data):
    """Test creating an AssetAccountTypesDTO with all fields specified."""
    # Arrange & Act
    dto = AssetAccountTypesDTO(**valid_asset_account_types_data)

    # Assert
    for field, value in valid_asset_account_types_data.items():
        assert getattr(dto, field) == value
    assert dto.discriminator == "asset_account_types"


def test_liability_account_types_dto_creation_with_all_fields(valid_liability_account_types_data):
    """Test creating a LiabilityAccountTypesDTO with all fields specified."""
    # Arrange & Act
    dto = LiabilityAccountTypesDTO(**valid_liability_account_types_data)

    # Assert
    for field, value in valid_liability_account_types_data.items():
        assert getattr(dto, field) == value
    assert dto.discriminator == "liability_account_types"


def test_transaction_categories_dto_creation_with_all_fields(valid_transaction_categories_data):
    """Test creating a TransactionCategoriesDTO with all fields specified."""
    # Arrange & Act
    dto = TransactionCategoriesDTO(**valid_transaction_categories_data)

    # Assert
    for field, value in valid_transaction_categories_data.items():
        assert getattr(dto, field) == value
    assert dto.discriminator == "transaction_categories"


def test_discriminated_types_model_with_asset_type():
    """Test DiscriminatedTypesModel accepts AssetAccountTypesDTO."""
    # Arrange
    asset_dto = AssetAccountTypesDTO(name="Cash", description="Cash account type")

    # Act
    model = DiscriminatedTypesModel(type_dto=asset_dto)

    # Assert
    assert isinstance(model.type_dto, AssetAccountTypesDTO)
    assert model.type_dto.discriminator == "asset_account_types"
    assert model.type_dto.name == "Cash"


def test_discriminated_types_model_with_liability_type():
    """Test DiscriminatedTypesModel accepts LiabilityAccountTypesDTO."""
    # Arrange
    liability_dto = LiabilityAccountTypesDTO(
        name="Credit Card", description="Credit card liability type"
    )

    # Act
    model = DiscriminatedTypesModel(type_dto=liability_dto)

    # Assert
    assert isinstance(model.type_dto, LiabilityAccountTypesDTO)
    assert model.type_dto.discriminator == "liability_account_types"
    assert model.type_dto.name == "Credit Card"


def test_discriminated_types_model_with_transaction_type():
    """Test DiscriminatedTypesModel accepts TransactionCategoriesDTO."""
    # Arrange
    transaction_dto = TransactionCategoriesDTO(
        name="Groceries", description="Grocery shopping expenses"
    )

    # Act
    model = DiscriminatedTypesModel(type_dto=transaction_dto)

    # Assert
    assert isinstance(model.type_dto, TransactionCategoriesDTO)
    assert model.type_dto.discriminator == "transaction_categories"
    assert model.type_dto.name == "Groceries"


def test_discriminated_types_model_serialization():
    """Test serialization of DiscriminatedTypesModel."""
    # Arrange
    asset_dto = AssetAccountTypesDTO(name="Cash", description="Cash account type")
    model = DiscriminatedTypesModel(type_dto=asset_dto)

    # Act
    model_dict = model.model_dump()

    # Assert
    assert "type_dto" in model_dict
    assert model_dict["type_dto"]["discriminator"] == "asset_account_types"
    assert model_dict["type_dto"]["name"] == "Cash"
    assert model_dict["type_dto"]["description"] == "Cash account type"


@pytest.mark.filterwarnings("ignore")
def test_from_dao_method_for_asset_account_types(mock_asset_account_types):
    """Test the from_dao class method for AssetAccountTypesDTO."""
    # Arrange
    with patch.object(AssetAccountTypesDTO, 'model_validate') as mock_validate:
        dto = AssetAccountTypesDTO(
            id=mock_asset_account_types.id,
            name=mock_asset_account_types.name,
            description=mock_asset_account_types.description,
        )
        mock_validate.return_value = dto

        # Act
        result = AssetAccountTypesDTO.from_dao(mock_asset_account_types)

        # Assert
        assert result == dto
        mock_validate.assert_called_once_with(mock_asset_account_types, strict=True)


@pytest.mark.filterwarnings("ignore")
def test_from_dao_method_for_liability_account_types(mock_liability_account_types):
    """Test the from_dao class method for LiabilityAccountTypesDTO."""
    # Arrange
    with patch.object(LiabilityAccountTypesDTO, 'model_validate') as mock_validate:
        dto = LiabilityAccountTypesDTO(
            id=mock_liability_account_types.id,
            name=mock_liability_account_types.name,
            description=mock_liability_account_types.description,
        )
        mock_validate.return_value = dto

        # Act
        result = LiabilityAccountTypesDTO.from_dao(mock_liability_account_types)

        # Assert
        assert result == dto
        mock_validate.assert_called_once_with(mock_liability_account_types, strict=True)


@pytest.mark.filterwarnings("ignore")
def test_from_dao_method_for_transaction_categories(mock_transaction_categories):
    """Test the from_dao class method for TransactionCategoriesDTO."""
    # Arrange
    with patch.object(TransactionCategoriesDTO, 'model_validate') as mock_validate:
        dto = TransactionCategoriesDTO(
            id=mock_transaction_categories.id,
            name=mock_transaction_categories.name,
            description=mock_transaction_categories.description,
        )
        mock_validate.return_value = dto

        # Act
        result = TransactionCategoriesDTO.from_dao(mock_transaction_categories)

        # Assert
        assert result == dto
        mock_validate.assert_called_once_with(mock_transaction_categories, strict=True)


@pytest.mark.filterwarnings("ignore")
def test_from_dao_type_error_for_asset_account_types():
    """Test that from_dao raises TypeError when given the wrong type for AssetAccountTypesDTO."""
    # Arrange
    not_an_asset_type = object()

    # Act & Assert
    with pytest.raises(TypeError) as exc_info:
        AssetAccountTypesDTO.from_dao(not_an_asset_type)

    assert "Unsupported DAO type:" in str(exc_info.value)


@pytest.mark.filterwarnings("ignore")
def test_from_dao_type_error_for_liability_account_types():
    """Test that from_dao raises TypeError when given the wrong type for LiabilityAccountTypesDTO."""
    # Arrange
    not_a_liability_type = object()

    # Act & Assert
    with pytest.raises(TypeError) as exc_info:
        LiabilityAccountTypesDTO.from_dao(not_a_liability_type)

    assert "Unsupported DAO type:" in str(exc_info.value)


@pytest.mark.filterwarnings("ignore")
def test_from_dao_type_error_for_transaction_categories():
    """Test that from_dao raises TypeError when given the wrong type for TransactionCategoriesDTO."""
    # Arrange
    not_a_transaction_category = object()

    # Act & Assert
    with pytest.raises(TypeError) as exc_info:
        TransactionCategoriesDTO.from_dao(not_a_transaction_category)

    assert "Unsupported DAO type:" in str(exc_info.value)


@pytest.mark.filterwarnings("ignore")
def test_to_dao_method_for_asset_account_types():
    """Test the to_dao method for AssetAccountTypesDTO."""
    # Arrange
    dto = AssetAccountTypesDTO(name="Cash", description="Cash account type")
    mock_dao = MagicMock(spec=AssetAccountTypes)

    with patch.object(AssetAccountTypesDTO.__dao_type__, 'model_validate', return_value=mock_dao) as mock_validate:
        # Act
        result = dto.to_dao()

        # Assert
        assert result == mock_dao
        mock_validate.assert_called_once()


@pytest.mark.filterwarnings("ignore")
def test_to_dao_method_for_liability_account_types():
    """Test the to_dao method for LiabilityAccountTypesDTO."""
    # Arrange
    dto = LiabilityAccountTypesDTO(name="Credit Card", description="Credit card liability type")
    mock_dao = MagicMock(spec=LiabilityAccountTypes)

    with patch.object(LiabilityAccountTypesDTO.__dao_type__, 'model_validate', return_value=mock_dao) as mock_validate:
        # Act
        result = dto.to_dao()

        # Assert
        assert result == mock_dao
        mock_validate.assert_called_once()


@pytest.mark.filterwarnings("ignore")
def test_to_dao_method_for_transaction_categories():
    """Test the to_dao method for TransactionCategoriesDTO."""
    # Arrange
    dto = TransactionCategoriesDTO(name="Groceries", description="Grocery shopping expenses")
    mock_dao = MagicMock(spec=TransactionCategories)

    with patch.object(TransactionCategoriesDTO.__dao_type__, 'model_validate', return_value=mock_dao) as mock_validate:
        # Act
        result = dto.to_dao()

        # Assert
        assert result == mock_dao
        mock_validate.assert_called_once()


def test_dto_types_contains_all_subclasses():
    """Test that DTO_TYPES contains all TypesDTO subclasses defined in the module."""
    # Arrange
    expected_subclasses = {
        cls for cls in inspect.getmembers(sys.modules["papita_txnsmodel.access.types.dto"], inspect.isclass)
        if issubclass(cls[1], TypesDTO) and cls[1] != TypesDTO
    }
    expected_subclass_names = {cls_name for cls_name, _ in expected_subclasses}

    # Act
    actual_subclass_names = {cls.__name__ for cls in DTO_TYPES}

    # Assert
    assert actual_subclass_names == expected_subclass_names
    assert "AssetAccountTypesDTO" in actual_subclass_names
    assert "LiabilityAccountTypesDTO" in actual_subclass_names
    assert "TransactionCategoriesDTO" in actual_subclass_names


def test_extra_fields_allowed_in_types_dto():
    """Test that TypesDTO allows extra fields due to ConfigDict(extra='allow')."""
    # Arrange & Act
    dto = AssetAccountTypesDTO(name="Cash", description="Cash account", extra_field="Extra value")

    # Assert
    assert hasattr(dto, "extra_field")
    assert dto.extra_field == "Extra value"
    assert "extra_field" in dto.model_dump()


def test_discriminator_included_in_model_dump():
    """Test that the discriminator is included in the model_dump output."""
    # Arrange
    dto = AssetAccountTypesDTO(name="Cash", description="Cash account type")

    # Act
    dump_dict = dto.model_dump()

    # Assert
    assert "discriminator" in dump_dict
    assert dump_dict["discriminator"] == "asset_account_types"


def test_discriminated_types_model_with_dict_input():
    """Test DiscriminatedTypesModel accepts dictionary input."""
    # Arrange
    asset_dict = {
        "discriminator": "asset_account_types",
        "name": "Cash",
        "description": "Cash account type"
    }

    # Act
    model = DiscriminatedTypesModel(type_dto=asset_dict)

    # Assert
    assert isinstance(model.type_dto, AssetAccountTypesDTO)
    assert model.type_dto.name == "Cash"
    assert model.type_dto.discriminator == "asset_account_types"


def test_discriminated_types_model_with_invalid_discriminator():
    """Test DiscriminatedTypesModel raises error with invalid discriminator."""
    # Arrange
    invalid_dict = {
        "discriminator": "invalid_type",
        "name": "Invalid",
        "description": "Invalid type"
    }

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        DiscriminatedTypesModel(type_dto=invalid_dict)

    assert "Input tag 'invalid_type' found using discriminator 'discriminator'" in str(exc_info.value)


def test_discriminated_types_model_with_missing_discriminator():
    """Test DiscriminatedTypesModel behavior with missing discriminator."""
    # Arrange
    missing_discriminator = {
        "name": "Missing",
        "description": "Missing discriminator"
    }

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        DiscriminatedTypesModel(type_dto=missing_discriminator)

    assert "Discriminator 'discriminator' not found" in str(exc_info.value)
