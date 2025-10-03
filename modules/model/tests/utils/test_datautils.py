"""Tests for datautils module providing utilities for working with DataFrames and Pydantic models."""
from copy import deepcopy
import pytest
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict, Optional

from papita_txnsmodel.utils.datautils import standardize_dataframe, convert_dto_obj_on_serialize


# Fixtures and helper classes for testing standardize_dataframe
class _TestModel(BaseModel):
    """Test Pydantic model for standardize_dataframe tests."""
    id: int
    name: str
    optional_field: Optional[str] = None


class _TestModelWithAlias(BaseModel):
    """Test Pydantic model with field aliases for by_alias tests."""
    id: int
    name: str = Field(alias="full_name")
    optional_field: Optional[str] = None


@pytest.fixture
def sample_df():
    """Provide a sample DataFrame for testing standardization functions."""
    return pd.DataFrame({
        "id": [1, 2, 3, 3],  # Note the duplicate
        "name": ["Alice", "Bob", "Charlie", "Charlie"],
        "optional_field": ["test1", "test2", None, "test3"],
        "to_drop": ["drop1", "drop2", "drop3", "drop3"]
    })


# Test cases for standardize_dataframe
def test_standardize_dataframe_basic(sample_df):
    """Test the basic functionality of standardize_dataframe with default parameters."""
    result = standardize_dataframe(_TestModel, sample_df[list(set(_TestModel.model_fields) - {"to_drop"})])

    # Check shape (should drop one duplicate)
    assert len(result) >= 3

    # Check all columns from model are present
    assert "id" in result.columns
    assert "name" in result.columns
    assert "optional_field" in result.columns


def test_standardize_dataframe_with_drops(sample_df):
    """Test standardize_dataframe with columns to drop specified."""
    result = standardize_dataframe(_TestModel, sample_df, drops=["to_drop"])

    # Check shape
    assert len(result) == 4

    # Check all columns from model are present
    assert "id" in result.columns
    assert "name" in result.columns
    assert "optional_field" in result.columns

    # Check to_drop column is not present
    assert "to_drop" not in result.columns


def test_standardize_dataframe_with_kwargs(sample_df):
    """Test standardize_dataframe with additional columns added via kwargs."""
    Custom_TestModel = deepcopy(_TestModel)
    Custom_TestModel.model_config = ConfigDict(extra="allow")
    result = standardize_dataframe(Custom_TestModel, sample_df, new_column="value")

    # Check shape
    assert len(result) == 4

    # Check all columns from model are present
    assert "id" in result.columns
    assert "name" in result.columns
    assert "optional_field" in result.columns

    # Check new column
    assert "to_drop" not in result.columns
    assert "new_column" in result.columns
    assert result["new_column"].iloc[0] == "value"


def test_standardize_dataframe_by_alias(sample_df):
    """Test standardize_dataframe with by_alias=True to use field aliases from the model."""
    # Rename the column to match the alias
    df = sample_df.rename(columns={"name": "full_name"})

    result = standardize_dataframe(_TestModelWithAlias, df, by_alias=True, drops=["to_drop"])

    # Check columns - should use aliases
    assert "id" in result.columns
    assert "full_name" in result.columns  # The alias name
    assert "name" not in result.columns   # Original field name not present


def test_standardize_dataframe_type_error_handling():
    """Test standardize_dataframe handles TypeError during deduplication gracefully."""
    # Create a DataFrame with a column containing unhashable types (e.g., lists)
    df = pd.DataFrame({
        "id": [1, 2],
        "name": ["Alice", "Bob"],
        "unhashable": [[1, 2], [3, 4]]  # Lists are unhashable
    })

    # Should handle the TypeError during drop_duplicates
    result = standardize_dataframe(_TestModel, df)

    # Check that rows were processed
    assert len(result) == 2


# Fixtures and helper classes for testing convert_dto_obj_on_serialize
class NestedModel(BaseModel):
    """Test nested Pydantic model for DTO serialization tests."""
    nested_id: str


class ParentModel(BaseModel):
    """Test parent Pydantic model containing a nested model for DTO serialization tests."""
    id: int
    nested: NestedModel | str


@pytest.fixture
def nested_model_instance():
    """Provide a nested model instance for testing DTO serialization."""
    return ParentModel(
        id=123,
        nested=NestedModel(nested_id="test-id")
    )


# Test cases for convert_dto_obj_on_serialize
def test_convert_dto_obj_on_serialize_success(nested_model_instance):
    """Test successful conversion with convert_dto_obj_on_serialize for nested objects."""
    result = convert_dto_obj_on_serialize(
        obj=nested_model_instance,
        id_field="nested",
        id_field_attr_name="nested_id",
        target_field="nested_id",
        expected_output_field_type=str,
        expected_intput_field_type=NestedModel
    )

    # Check that the new field was created with the correct value
    assert "nested_id" in result
    assert result["nested_id"] == "test-id"

    # Check that the original field was removed
    assert "nested" not in result

    # Check that other fields remain
    assert "id" in result
    assert result["id"] == 123


def test_convert_dto_obj_on_serialize_with_direct_value():
    """Test convert_dto_obj_on_serialize with a direct value instead of a nested object."""
    # Create a model where the field is a direct value, not a nested object
    model = ParentModel(
        id=123,
        nested="direct-value"  # String instead of NestedModel
    )

    result = convert_dto_obj_on_serialize(
        obj=model,
        id_field="nested",
        id_field_attr_name="nested_id",  # Won't be used
        target_field="nested_id",
        expected_output_field_type=str,
        expected_intput_field_type=NestedModel
    )

    # Check that the direct value was used
    assert result["nested_id"] == "direct-value"


def test_convert_dto_obj_on_serialize_type_error():
    """Test convert_dto_obj_on_serialize raises TypeError when output type doesn't match expected."""
    model = ParentModel(
        id=123,
        nested=NestedModel(nested_id="123")  # Integer instead of expected string
    )

    with pytest.raises(TypeError, match="The output type of the field nested was not expected int"):
        convert_dto_obj_on_serialize(
            obj=model,
            id_field="nested",
            id_field_attr_name="nested_id",
            target_field="nested_id",
            expected_output_field_type=int,  # Expect int
            expected_intput_field_type=NestedModel
        )
