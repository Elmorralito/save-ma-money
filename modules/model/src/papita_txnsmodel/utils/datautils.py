"""
Utilities for working with DataFrames and Pydantic models.

This module provides functions to standardize pandas DataFrames using Pydantic models
and to help with data transfer object (DTO) serialization.
"""

import itertools
from typing import Any, Dict, Generator, Iterator

import pandas as pd
from pydantic import BaseModel


def standardize_dataframe(
    cls: type[BaseModel], df: pd.DataFrame, drops: list[str] | None = None, by_alias: bool = False, **kwargs
) -> pd.DataFrame:
    """
    Standardize a DataFrame using a Pydantic model for validation and transformation.

    This function processes a DataFrame by optionally dropping specified columns,
    adding new columns from kwargs, removing duplicates, and validating each row
    against the provided Pydantic model.

    Args:
        cls: Pydantic model class to validate and transform each row
        df: Input DataFrame to standardize
        drops: Optional list of column names to drop from the DataFrame
        by_alias: Whether to use field aliases from the Pydantic model
        **kwargs: Additional columns to add to the DataFrame before processing

    Returns:
        A standardized DataFrame with rows validated and transformed according to the model
    """
    drops = drops or []
    temp = df.copy()
    temp.drop(columns=drops, errors="ignore", inplace=True)

    try:
        output = temp.drop_duplicates()
    except TypeError:
        output = temp

    standardized = output.reset_index(drop=True).apply(
        lambda row: cls.model_validate(row.to_dict()).model_dump(mode="python", by_alias=by_alias),
        axis=1,
        result_type="expand",
    )
    for key, value in kwargs.items():
        standardized[key] = value

    return standardized


def convert_dto_obj_on_serialize(
    *,
    obj: BaseModel,
    id_field: str,
    id_field_attr_name: str,
    target_field: str,
    expected_output_field_type: type,
    expected_intput_field_type: type,
) -> Dict[str, Any]:
    """
    Convert a field in a Pydantic model during serialization.

    This function extracts a value from a nested object attribute or directly from
    a field and creates a new dictionary with the transformed value. It's useful for
    flattening nested structures during serialization.

    Args:
        obj: The Pydantic model instance to process
        id_field: The field name in the object to extract from
        id_field_attr_name: The attribute name to extract if id_field is an object
        target_field: The name of the new field to create in the output dictionary
        expected_output_field_type: The expected type of the output value
        expected_intput_field_type: The expected type of the input field

    Returns:
        A dictionary with the original data and the transformed field

    Raises:
        TypeError: If the output field value doesn't match the expected type
    """
    data = obj.model_dump()
    field = getattr(obj, id_field)
    if isinstance(field, expected_intput_field_type) and hasattr(field, id_field_attr_name):
        data[target_field] = getattr(field, id_field_attr_name)
    else:
        data[target_field] = field
    if not isinstance(data[target_field], expected_output_field_type):
        raise TypeError(
            f"The output type of the field {id_field} was not expected {expected_output_field_type.__name__}"
        )

    data.pop(id_field)
    return data


def slice_batches(data: pd.DataFrame | Generator | Iterator, batch_size: int):
    """
    Split data into batches of specified size for efficient processing.

    This method takes input data in various formats and yields it as batches
    of specified size. It's particularly useful for database operations where
    processing large amounts of data in smaller chunks is more efficient.

    Args:
        data: The data to be batched. Can be a pandas DataFrame, a Generator,
            or any Iterator. If a DataFrame is provided, it will be converted
            to an iterator of rows.
        batch_size: The maximum number of items to include in each batch.

    Yields:
        List: A batch of items from the input data, with length up to
            batch_size. The last batch may contain fewer items.

    Examples:
        >>> df = pd.DataFrame({'A': range(10)})
        >>> for batch in SomeClass.slice_batches(df, 3):
        ...     print(len(batch))
        3
        3
        3
        1
    """
    if isinstance(data, pd.DataFrame):
        data = map(lambda x: x[1], data.iterrows())

    if isinstance(data, Generator):
        data = iter(data)

    while True:
        slice_ = list(itertools.islice(data, batch_size))
        if not slice_:
            break

        yield slice_
