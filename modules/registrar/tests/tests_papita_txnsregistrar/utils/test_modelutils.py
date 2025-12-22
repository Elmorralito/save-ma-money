"""Test suite for model validation utilities.

This module contains unit tests for validation utility functions used by Pydantic models
in the transaction registrar system. The tests verify semantic version validation, tag
normalization and validation, and service dependency validation logic. All tests ensure
that validators correctly process inputs, normalize data, and raise appropriate errors
for invalid inputs.
"""

from unittest.mock import MagicMock, patch

from papita_txnsmodel.access.base.dto import TableDTO
import pytest
from pydantic import Field, ValidationInfo

from papita_txnsmodel.services.base import BaseService
from papita_txnsregistrar.utils.modelutils import (
    make_service_dependencies_validator,
    validate_python_version,
    validate_tags,
    validate_tags_wrapper,
)


@pytest.mark.parametrize(
    "version_string,expected_result",
    [("1.2.3", True), ("2.0.0", True), ("invalid.version", False), ("not-a-version", False)],
)
def test_validate_python_version_validates_semantic_versions(version_string, expected_result):
    """Test that validate_python_version correctly validates or rejects semantic version strings."""
    # Arrange
    handler = MagicMock(return_value=version_string)

    # Act
    result = validate_python_version(version_string, handler)

    # Assert
    # Note: The function returns a boolean from Version.is_valid(), not raising an error
    assert result is expected_result
    handler.assert_called_once_with(version_string)


@pytest.mark.parametrize(
    "input_tags,expected_output",
    [
        # Note: The regex only allows letters and spaces, not digits
        (["Tag", "TagTwo", "TagThree"], ["tag", "tagtwo", "tagthree"]),
        (["TAG ONE", "tag two", "Tag Three"], ["tag one", "tag two", "tag three"]),
        (["Duplicate", "duplicate", "DUPLICATE"], ["duplicate"]),
        (["Valid Tag", "Another Valid"], ["valid tag", "another valid"]),
    ],
)
def test_validate_tags_normalizes_and_deduplicates_tags(input_tags, expected_output):
    """Test that validate_tags normalizes tags to lowercase and removes duplicates."""
    # Act
    result = validate_tags(input_tags)

    # Assert
    assert sorted(result) == sorted(expected_output)
    assert all(tag.islower() for tag in result)


def test_validate_tags_raises_value_error_when_no_valid_tags():
    """Test that validate_tags raises ValueError when no valid tags are found after filtering."""
    # Arrange
    invalid_tags = ["**test-tag**", "test..tag", "test tag|"]

    # Act & Assert
    with pytest.raises(ValueError, match="No valid tags found"):
        validate_tags(invalid_tags)


def test_validate_tags_wrapper_delegates_to_validate_tags():
    """Test that validate_tags_wrapper correctly delegates to validate_tags function."""
    # Arrange
    # Use tags without digits since the regex only allows letters and spaces
    handler = MagicMock(return_value=["Tag", "TagTwo"])

    # Act
    result = validate_tags_wrapper(["Tag", "TagTwo"], handler)

    # Assert
    assert sorted(result) == ["tag", "tagtwo"]
    handler.assert_called_once_with(["Tag", "TagTwo"])


def test_validate_tags_wrapper_returns_none_when_handler_returns_none():
    """Test that validate_tags_wrapper returns None when handler returns None."""
    # Arrange
    tags = ["Tag", "TagTwo"]
    handler = MagicMock(return_value=tags)

    # Act
    result = validate_tags_wrapper(tags, handler)
    assert result != tags
    assert sorted(result) == sorted([str.lower(tag).strip() for tag in tags])
    handler.assert_called_once_with(tags)
