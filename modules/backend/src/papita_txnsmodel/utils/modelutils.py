"""
Utility functions for model validation and data transformation.

This module provides various utility functions for model operations including class validation,
date parsing and validation, and interest rate normalization. It contains:
- Class validation tools (make_class_validator)
- Date parsing and validation functions (parse_dates, validate_dates)
- Numeric value normalization (validate_interest_rate)
"""

import inspect
import re
from datetime import date, datetime
from typing import Callable, Iterable, Type

import numpy as np
import pandas as pd
import pytz
from dateutil.parser import ParserError
from dateutil.parser import parse as dt_parse
from pydantic import ValidationInfo, ValidatorFunctionWrapHandler
from semver import Version

from .classutils import ClassDiscovery

ALLOWED_DELIMITERS = (",", "|", ";", ":", "\n")
ALLOWED_TRUE_BOOL_VALUES = ("true", "yes", "y", "1", "on", "s", 1, True)
ALLOWED_FALSE_BOOL_VALUES = ("false", "no", "n", "0", "off", 0, False)


def validate_bool(value: bool | int | str, handler: ValidatorFunctionWrapHandler) -> bool:
    """Validate and coerce input values to a boolean.

    This function attempts to convert various input types (bool, int, str) into
    a boolean value using predefined sets of allowed true and false values.
    It is designed to be used as a Pydantic wrap validator.

    Args:
        value (bool | int | str): The value to validate.
        handler (ValidatorFunctionWrapHandler): The Pydantic validator handler.

    Returns:
        bool: The validated boolean value.

    Raises:
        ValueError: If 'value' cannot be mapped to a valid boolean.
    """
    value_ = handler(value)
    if isinstance(value_, bool):
        return value_

    if isinstance(value_, str):
        value_ = value_.lower()

    if value_ in ALLOWED_TRUE_BOOL_VALUES:
        return True

    if value_ in ALLOWED_FALSE_BOOL_VALUES:
        return False

    raise ValueError(f"'{value}' is not a valid boolean value.")


def normalize_tags(value: Iterable[str] | str) -> Iterable[str]:
    """Normalize and filter a collection of tag strings.

    This function processes input tags by splitting strings on allowed delimiters,
    stripping whitespace, converting to lowercase, and filtering for valid
    alphanumeric characters (including hyphens and underscores).

    Args:
        value (Iterable[str] | str): A single string or an iterable of strings
            to be normalized.

    Returns:
        Iterable[str]: A list of unique, lowercase, and stripped tag strings.

    Raises:
        ValueError: If no valid tags are found after processing.
    """
    if isinstance(value, str):
        value_ = [value]
        for delimiter in ALLOWED_DELIMITERS:
            if delimiter in value:
                value_ = value.split(delimiter)
                break
    else:
        value_ = list(value)

    tags = list({str.lower(tag).strip() for tag in value_ if re.match(r"^([A-Za-z0-9-_]|\s)+$", tag.strip() or "")})
    if not tags:
        raise ValueError("No valid tags found.")

    return tags


def make_class_validator(
    class_type: Type,
) -> Callable[[Type | str, ValidationInfo], type | None]:
    """
    Create a validator function to validate class types.

    This function generates a validator that can be used to validate whether
    a given value is a class of the specified type. If the value is a string,
    it attempts to select and load the class using `ClassDiscovery.select`.
    Args:
        class_type (Type): The type of class to validate against.
    Returns:
        Callable[[Type | str, ValidationInfo], Type]: A validator function that takes a value and validation info,
        and returns the validated class.

    Example:
        >>> validator = make_class_validator(MyBaseClass)
        >>> validated_class = validator("MyModule.MyClass", ValidationInfo())
        >>> isinstance(validated_class, MyBaseClass)
        True
    """

    def load_class(val: Type | str, _: ValidationInfo) -> type:
        """
        Load and validate the class.
        Args:
            val (Type | str): The value to validate. Can be a class type or a string representing the class.
            _ (ValidationInfo): Additional validation info (not used in this implementation).
        Returns:
            Type: The validated class type.

        Raises:
            ValueError: If the value cannot be validated as a class of the specified type.
        """
        if inspect.isclass(val):
            return val

        if isinstance(val, str):
            class_ = ClassDiscovery.select(val, class_type=class_type)
            if inspect.isclass(class_):
                return class_

        raise ValueError("Class type not supported.")

    return load_class


def parse_dates(
    ts_value: int | float | str | datetime | date | pd.Timestamp,
) -> pd.Timestamp | None:
    """
    Parse dates from various formats into a standardized pandas Timestamp.

    This function handles multiple date input formats including integers (unix timestamps),
    floats, strings, datetime objects, date objects, and pandas Timestamps. It attempts to
    convert them all to UTC-localized pandas Timestamps.

    Args:
        ts_value: The input date value in any supported format. Can be integer (unix timestamp),
                 float, string, datetime, date, or pandas Timestamp.

    Returns:
        pd.Timestamp | None: The parsed date as a pandas Timestamp object in UTC timezone,
                            or None if parsing fails or input is empty.

    Note:
        - Integer values are treated as unix timestamps in seconds
        - If conversion fails with seconds, it tries milliseconds (dividing by 1000)
        - String values are parsed using dateutil.parser
        - The result is always localized to UTC timezone
    """
    output = None
    if not ts_value:
        return output

    if isinstance(ts_value, pd.Timestamp):
        output = ts_value
    if isinstance(ts_value, datetime):
        output = pd.Timestamp(ts_value)
    elif isinstance(ts_value, date):
        output = pd.Timestamp(ts_value, tz=pytz.UTC)
    elif isinstance(ts_value, str):
        try:
            output = dt_parse(ts_value)
            output = pd.Timestamp(output)
        except (ParserError, TypeError):
            pass
    elif isinstance(ts_value, (int, float)):
        try:
            output = pd.Timestamp.utcfromtimestamp(ts_value)
        except ValueError:
            output = pd.Timestamp.utcfromtimestamp(ts_value / 1000)

    try:
        if output is not None:
            output = output.tz_localize(pytz.UTC)
    except (ParserError, TypeError, ValueError):
        if output is not None:
            output = output.tz_convert(pytz.UTC)

    return output


def validate_dates(
    value: int | float | str | datetime | date | pd.Timestamp, handler: ValidatorFunctionWrapHandler
) -> pd.Timestamp | None:
    """
    Validate date values using a handler function.

    This function wraps the parse_dates function within a validation handler,
    which enables it to be used as a validator in frameworks like Pydantic.

    Args:
        value: The date value to validate, in any format supported by parse_dates.
        handler (ValidatorFunctionWrapHandler): A validator function handler, typically
                                                provided by a validation framework.

    Returns:
        pd.Timestamp | None: The validated and parsed timestamp or None if validation fails.
    """
    return handler(parse_dates(value))


def validate_interest_rate(value: float, handler: ValidatorFunctionWrapHandler) -> float | None:
    """
    Validate and normalize interest rate values.

    This function normalizes interest rates to a decimal format (e.g., 0.05 for 5%).
    If the input rate is greater than or equal to 1.0, it's assumed to be in percentage
    form and is divided by 100. The result is rounded using numpy.

    Args:
        value (float): The interest rate value to validate.
        handler (ValidatorFunctionWrapHandler): A validator function handler, typically
                                                provided by a validation framework.

    Returns:
        float | None: The validated and normalized interest rate as a decimal,
                        or None if validation fails or input is empty.

    Example:
        When used as a Pydantic validator, it will convert 5.0 to 0.05
        and will leave 0.05 as 0.05.
    """
    value_ = handler(value)
    if not value_:
        return None

    if value_ >= 1.0:
        value_ = value_ / 100

    return float(np.around(value_, decimals=8))


def validate_python_version_wrapper(value: str, handler: ValidatorFunctionWrapHandler) -> str:
    """
    Validate that a string follows semantic versioning format.

    This function verifies that a string represents a valid semantic version
    using the semver library. It's designed to be used as a Pydantic validator.

    Args:
        value: The version string to validate.
        handler: Pydantic validator handler for chaining validators.

    Returns:
        The validated version string.

    Raises:
        ValueError: If the string is not a valid semantic version.
    """
    value_ = handler(value)
    return Version.is_valid(value_)


def validate_tags(value: Iterable[str]) -> Iterable[str]:
    """
    Validate and normalize a list of tag strings.

    This function processes a list of tags, ensuring that each tag:
    1. Contains only letters and spaces
    2. Is converted to lowercase
    3. Is unique in the final list

    It's designed to be used as a Pydantic validator.

    Args:
        value: Iterable of tag strings to validate.
        handler: Pydantic validator handler for chaining validators.
    Returns:
        A normalized list of unique, lowercase tags.
    Raises:
        ValueError: If no valid tags are found after filtering.
    """
    tags = [str.lower(elem).strip() for elem in value if re.match(r"^([A-Za-z0-9-_]|\s)+$", elem or "")]
    if not tags:
        raise ValueError("No valid tags found.")

    return list(set(tags))


def validate_tags_wrapper(value: Iterable[str], handler: ValidatorFunctionWrapHandler) -> Iterable[str]:
    """
    Wrapper to use validate_tags as a Pydantic validator.
    This function serves as a bridge to integrate the validate_tags function
    with Pydantic's validation system by utilizing the ValidatorFunctionWrapHandler.
    Args:
        value: Iterable of tag strings to validate.
        handler: Pydantic validator handler for chaining validators.
    Returns:
        A normalized list of unique, lowercase tags.
    """
    value_ = handler(value)
    return validate_tags(value_)
