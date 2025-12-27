"""Unit tests for the datautils module in the Papita Transactions system.

This test suite validates DataFrame standardization, DTO serialization conversion,
and batch processing functionality. All tests use mocking where necessary to ensure
isolation and avoid external dependencies.
"""

import uuid
from typing import Generator, Iterator
from unittest.mock import patch

import pandas as pd
import pytest
from pydantic import BaseModel, ConfigDict, Field

from papita_txnsmodel.utils import datautils


@pytest.fixture
def sample_pydantic_model():
    """Provide a sample Pydantic model for testing DataFrame standardization."""

    class TestModel(BaseModel):
        id: uuid.UUID
        name: str = Field(min_length=1)
        active: bool = True

    return TestModel


@pytest.fixture
def sample_dataframe():
    """Provide a sample DataFrame for testing standardization operations."""
    return pd.DataFrame(
        {
            "id": [uuid.uuid4(), uuid.uuid4()],
            "name": ["Test1", "Test2"],
            "active": [True, False],
            "extra_col": ["extra1", "extra2"],
        }
    )


@pytest.fixture
def sample_pydantic_object():
    """Provide a sample Pydantic object for testing serialization conversion."""

    class NestedObject:
        def __init__(self, value):
            self.value = value

    class TestDTO(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)

        id: uuid.UUID
        nested: NestedObject
        simple_field: str

    test_id = uuid.uuid4()
    return TestDTO(id=test_id, nested=NestedObject("test_value"), simple_field="simple")


def test_standardize_dataframe_validates_and_transforms_rows(sample_pydantic_model, sample_dataframe):
    """Test that standardize_dataframe validates and transforms DataFrame rows using Pydantic model."""
    # Arrange
    df = sample_dataframe.copy()

    # Act
    result = datautils.standardize_dataframe(sample_pydantic_model, df)

    # Assert
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert "id" in result.columns
    assert "name" in result.columns
    assert "active" in result.columns


def test_standardize_dataframe_drops_specified_columns(sample_pydantic_model, sample_dataframe):
    """Test that standardize_dataframe correctly drops specified columns from DataFrame."""
    # Arrange
    df = sample_dataframe.copy()
    drops = ["extra_col"]

    # Act
    result = datautils.standardize_dataframe(sample_pydantic_model, df, drops=drops)

    # Assert
    assert "extra_col" not in result.columns
    assert "id" in result.columns
    assert "name" in result.columns


def test_standardize_dataframe_adds_kwargs_columns(sample_pydantic_model, sample_dataframe):
    """Test that standardize_dataframe correctly adds additional columns from kwargs."""
    # Arrange
    df = sample_dataframe.copy()
    extra_value = "extra_value"

    # Act
    result = datautils.standardize_dataframe(sample_pydantic_model, df, static_values={"extra_column": extra_value})

    # Assert
    assert "extra_column" in result.columns
    assert all(result["extra_column"] == extra_value)


def test_standardize_dataframe_removes_duplicates(sample_pydantic_model):
    """Test that standardize_dataframe removes duplicate rows from DataFrame."""
    # Arrange
    test_id = uuid.uuid4()
    df = pd.DataFrame(
        {
            "id": [test_id, test_id, uuid.uuid4()],
            "name": ["Test", "Test", "Test2"],
            "active": [True, True, False],
        }
    )

    # Act
    result = datautils.standardize_dataframe(sample_pydantic_model, df)

    # Assert
    assert len(result) == 2  # Duplicate removed


def test_standardize_dataframe_handles_type_error_on_drop_duplicates(sample_pydantic_model, sample_dataframe):
    """Test that standardize_dataframe handles TypeError when drop_duplicates fails and continues processing.

    This test mocks the drop_duplicates method of the DataFrame class to raise a TypeError.
    This is to test that the standardize_dataframe function continues processing even when
    the drop_duplicates method fails.
    """
    # Arrange
    df = sample_dataframe.copy()

    with patch.object(pd.DataFrame, "drop_duplicates", side_effect=TypeError("Unhashable type")):
        # Act
        result = datautils.standardize_dataframe(sample_pydantic_model, df)

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(df)


def test_convert_dto_obj_on_serialize_extracts_nested_attribute(sample_pydantic_object):
    """Test that convert_dto_obj_on_serialize correctly extracts nested object attribute."""
    # Arrange
    obj = sample_pydantic_object

    # Act
    result = datautils.convert_dto_obj_on_serialize(
        obj=obj,
        id_field="nested",
        id_field_attr_name="value",
        target_field="nested_value",
        expected_output_field_type=str,
        expected_intput_field_type=type(obj.nested),
    )

    # Assert
    assert "nested_value" in result
    assert result["nested_value"] == "test_value"
    assert "nested" not in result
    assert result["id"] == obj.id


def test_convert_dto_obj_on_serialize_uses_direct_field_when_not_nested(sample_pydantic_object):
    """Test that convert_dto_obj_on_serialize uses direct field value when field is not nested object."""
    # Arrange
    obj = sample_pydantic_object

    # Act
    result = datautils.convert_dto_obj_on_serialize(
        obj=obj,
        id_field="simple_field",
        id_field_attr_name="value",
        target_field="simple_value",
        expected_output_field_type=str,
        expected_intput_field_type=object,
    )

    # Assert
    assert "simple_value" in result
    assert result["simple_value"] == "simple"
    assert "simple_field" not in result


def test_convert_dto_obj_on_serialize_raises_type_error_for_mismatch(sample_pydantic_object):
    """Test that convert_dto_obj_on_serialize raises TypeError when output type doesn't match expected."""
    # Arrange
    obj = sample_pydantic_object

    # Act & Assert
    with pytest.raises(TypeError, match="The output type of the field"):
        datautils.convert_dto_obj_on_serialize(
            obj=obj,
            id_field="simple_field",
            id_field_attr_name="value",
            target_field="simple_value",
            expected_output_field_type=int,
            expected_intput_field_type=object,
        )


@pytest.mark.parametrize(
    "data_type,data_input",
    [
        ("dataframe", pd.DataFrame({"A": range(10)})),
        ("generator", (x for x in range(10))),
        ("iterator", iter(range(10))),
    ],
)
def test_slice_batches_processes_different_data_types(data_type, data_input):
    """Test that slice_batches correctly processes DataFrame, Generator, and Iterator inputs."""
    # Arrange
    batch_size = 3

    # Act
    batches = list(datautils.slice_batches(data_input, batch_size))

    # Assert
    assert len(batches) > 0
    assert all(len(batch) <= batch_size for batch in batches)
    if data_type == "dataframe":
        assert all(isinstance(batch[0], pd.Series) for batch in batches)


def test_slice_batches_handles_empty_data():
    """Test that slice_batches handles empty input data gracefully."""
    # Arrange
    empty_df = pd.DataFrame()
    batch_size = 5

    # Act
    batches = list(datautils.slice_batches(empty_df, batch_size))

    # Assert
    assert len(batches) == 0
