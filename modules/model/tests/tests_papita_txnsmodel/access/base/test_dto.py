"""Unit tests for the base DTO module in the Papita Transactions system.

This test suite validates the core functionality of TableDTO and CoreTableDTO classes,
including data conversion, validation, and DataFrame standardization operations.
All tests use mocking to ensure isolation and avoid external dependencies.
"""

from typing import Iterable
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from papita_txnsmodel.access.base.dto import CoreTableDTO, TableDTO
from papita_txnsmodel.model.base import BaseSQLModel


@pytest.fixture
def mock_base_sql_model():
    """Provide a mocked BaseSQLModel instance for testing DTO conversion operations."""
    model = MagicMock(spec=BaseSQLModel)
    model.id = uuid.uuid4()
    model.active = True
    model.deleted_at = None
    return model


@pytest.fixture
def sample_dataframe():
    """Provide a sample DataFrame for testing standardization operations."""
    return pd.DataFrame(
        {
            "id": [uuid.uuid4(), uuid.uuid4()],
            "active": [True, False],
            "deleted_at": [None, datetime.now()],
        }
    )


def test_table_dto_from_dao_success():
    """Test that from_dao successfully converts a valid BaseSQLModel instance to TableDTO."""

    # Arrange
    test_datetime = datetime.now()
    base_model = BaseSQLModel(active=False, deleted_at=test_datetime)

    # Act
    result = TableDTO.from_dao(base_model)

    # Assert
    assert isinstance(result, TableDTO)
    assert result.active is False
    assert result.deleted_at == test_datetime
    base_model = BaseSQLModel(active=True, deleted_at=test_datetime)
    result = TableDTO.from_dao(base_model)
    assert result.active is True
    assert result.deleted_at is None
    assert result.id is not None  # Should have auto-generated UUID


def test_table_dto_from_dao_raises_type_error_for_invalid_type():
    """Test that from_dao raises TypeError when provided with an object that is not BaseSQLModel."""
    # Arrange
    invalid_obj = "not a BaseSQLModel"

    # Act & Assert
    with pytest.raises(TypeError, match="Unsupported DAO type"):
        TableDTO.from_dao(invalid_obj)


@pytest.mark.parametrize(
    "active_value,expected",
    [
        (True, True),
        (False, False),
        ("true", True),
        ("false", False),
        ("yes", True),
        ("no", False),
        (1, True),
        (0, False),
    ],
)
def test_table_dto_active_field_validation(active_value, expected):
    """Test that TableDTO active field correctly validates and converts various boolean representations."""
    # Act
    dto = TableDTO(id=uuid.uuid4(), active=active_value, deleted_at=None)

    # Assert
    assert dto.active == expected
    assert isinstance(dto.active, bool)


@patch("papita_txnsmodel.access.base.dto.datautils.standardize_dataframe")
def test_table_dto_standardized_dataframe_calls_utility(mock_standardize, sample_dataframe):
    """Test that standardized_dataframe correctly delegates to datautils.standardize_dataframe with proper parameters."""
    # Arrange
    expected_result = pd.DataFrame({"id": [uuid.uuid4()], "active": [True]})
    mock_standardize.return_value = expected_result
    drops = ["deleted_at"]
    by_alias = True
    extra_col = "test_col"
    extra_val = "test_value"

    # Act
    result = TableDTO.standardized_dataframe(
        sample_dataframe, drops=drops, by_alias=by_alias, test_col=extra_val
    )

    # Assert
    assert result.equals(expected_result)
    mock_standardize.assert_called_once_with(
        TableDTO, sample_dataframe, drops=drops, by_alias=by_alias, test_col=extra_val
    )


def test_core_table_dto_normalize_model_strips_and_normalizes_fields():
    """Test that CoreTableDTO _normalize_model validator correctly strips whitespace and normalizes tags."""
    # Arrange
    name = "  Test Name  "
    description = "  Test Description  "
    tags = ["tag1", "tag2"]

    # Act
    dto = CoreTableDTO(name=name, description=description, tags=tags)

    # Assert
    assert dto.name == "Test Name"
    assert dto.description == "Test Description"
    assert isinstance(dto.tags, Iterable) and not isinstance(dto.tags, str)
    tag_list = list(dto.tags)
    print(tag_list)
    assert "test name" in tag_list
    assert len(tag_list) >= 2
