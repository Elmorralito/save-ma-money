"""
Validation utilities for Pydantic models in the transaction tracker system.

This module provides validator functions used by Pydantic models to ensure data
consistency and correctness. It includes functions for validating semantic version
strings and tag formatting to maintain data quality throughout the system.
"""

import re
from typing import List

from pydantic import ValidatorFunctionWrapHandler
from semver import Version


def validate_python_version(value: str, handler: ValidatorFunctionWrapHandler) -> str:
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
    return Version.is_valid(handler(value))


def validate_tags(value: List[str], handler: ValidatorFunctionWrapHandler) -> List[str]:
    """
    Validate and normalize a list of tag strings.

    This function processes a list of tags, ensuring that each tag:
    1. Contains only letters and spaces
    2. Is converted to lowercase
    3. Is unique in the final list

    It's designed to be used as a Pydantic validator.

    Args:
        value: List of tag strings to validate.
        handler: Pydantic validator handler for chaining validators.

    Returns:
        A normalized list of unique, lowercase tags.

    Raises:
        ValueError: If no valid tags are found after filtering.
    """
    value_ = handler(value)
    tags = [str.lower(elem) for elem in value_ if re.match(r"^([A-Za-z]|\s)+$", elem or "")]
    if not tags:
        raise ValueError("No valid tags found.")

    return list(set(tags))
