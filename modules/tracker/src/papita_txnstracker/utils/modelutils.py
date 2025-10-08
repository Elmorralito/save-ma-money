import inspect
from datetime import date, datetime
from typing import Callable, Type

import numpy as np
import pandas as pd
import pytz
from dateutil.parser import ParserError
from dateutil.parser import parse as dt_parse
from pydantic import ValidationInfo, ValidatorFunctionWrapHandler

from .discovery import ClassDiscoverer


def make_class_validator(
    class_type: Type,
) -> Callable[[Type | str, ValidationInfo], type | None]:
    """
    Create a validator function to validate class types.

    This function generates a validator that can be used to validate whether
    a given value is a class of the specified type. If the value is a string,
    it attempts to select and load the class using `ClassSelector.select`.

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
            TypeError: If the value cannot be validated as a class of the specified type.
        """
        if inspect.isclass(val):
            return val

        if isinstance(val, str):
            class_ = ClassDiscoverer.select(val, class_type=class_type)
            if inspect.isclass(class_):
                return class_

        raise ValueError("Class type not supported.")

    return load_class


def parse_dates(
    ts_value: int | float | str | datetime | date | pd.Timestamp,
) -> pd.Timestamp | None:
    """
    Parse dates from various formats.

    Args:
        ts_value (Optional[Union[int, float, str, datetime, date, pd.Timestamp]]): The input date value.

    Returns:
        Union[pd.Timestamp, None]: The parsed date as pd.Timestamp or None.
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
    return handler(parse_dates(value))


def validate_interest_rate(value: float, handler: ValidatorFunctionWrapHandler) -> float:
    value_ = handler(value)
    if value_ >= 1.0:
        value_ = value_ / 100

    return float(np.around(value_))
