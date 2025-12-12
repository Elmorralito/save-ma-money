"""Unit tests for the modelutils module in the Papita Transactions system.

This test suite validates model validation and data transformation utilities including
boolean validation, tag normalization, class validation, date parsing, and interest rate
normalization. All tests use mocking where necessary to ensure isolation.
"""

import inspect
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import pytz
from dateutil.parser import ParserError
from pydantic import ValidationInfo

from papita_txnsmodel.utils import modelutils


@pytest.fixture
def mock_handler():
    """Provide a mock validator function handler for Pydantic validators."""
    handler = MagicMock()
    handler.side_effect = lambda x: x
    return handler


@pytest.fixture
def sample_base_class():
    """Provide a sample base class for class validator testing."""

    class BaseClass:
        pass

    return BaseClass


@pytest.fixture
def sample_derived_class(sample_base_class):
    """Provide a sample derived class for class validator testing."""

    class DerivedClass(sample_base_class):
        pass

    return DerivedClass


@pytest.fixture
def mock_validation_info():
    """Provide a mock ValidationInfo object for Pydantic validator testing."""
    return MagicMock()


class TestValidateBool:
    """Test suite for validate_bool function."""

    def test_validate_bool_returns_true_for_boolean_true(self, mock_handler):
        """Test that validate_bool returns True when given boolean True value."""
        result = modelutils.validate_bool(True, mock_handler)
        assert result is True

    def test_validate_bool_returns_false_for_boolean_false(self, mock_handler):
        """Test that validate_bool returns False when given boolean False value."""
        result = modelutils.validate_bool(False, mock_handler)
        assert result is False

    @pytest.mark.parametrize(
        "value",
        ["true", "yes", "y", "1", "on", "s", 1, True],
    )
    def test_validate_bool_returns_true_for_allowed_true_values(self, mock_handler, value):
        """Test that validate_bool returns True for all allowed true value representations."""
        result = modelutils.validate_bool(value, mock_handler)
        assert result is True

    @pytest.mark.parametrize(
        "value",
        ["false", "no", "n", "0", "off", 0, False],
    )
    def test_validate_bool_returns_false_for_allowed_false_values(self, mock_handler, value):
        """Test that validate_bool returns False for all allowed false value representations."""
        result = modelutils.validate_bool(value, mock_handler)
        assert result is False

    def test_validate_bool_raises_value_error_for_invalid_value(self, mock_handler):
        """Test that validate_bool raises ValueError when given an invalid boolean value."""
        with pytest.raises(ValueError, match="is not a valid boolean value"):
            modelutils.validate_bool("invalid", mock_handler)

    def test_validate_bool_handles_case_insensitive_strings(self, mock_handler):
        """Test that validate_bool handles case-insensitive string boolean values correctly."""
        assert modelutils.validate_bool("TRUE", mock_handler) is True
        assert modelutils.validate_bool("FALSE", mock_handler) is False
        assert modelutils.validate_bool("Yes", mock_handler) is True
        assert modelutils.validate_bool("No", mock_handler) is False


class TestNormalizeTags:
    """Test suite for normalize_tags function."""

    def test_normalize_tags_returns_list_for_single_string_tag(self):
        """Test that normalize_tags returns a list containing the normalized tag for a single string."""
        result = modelutils.normalize_tags("tag1")
        assert result == ["tag1"]
        assert isinstance(result, list)

    @pytest.mark.parametrize(
        "delimiter",
        [",", "|", ";", ":", "\n"],
    )
    def test_normalize_tags_splits_string_by_allowed_delimiters(self, delimiter):
        """Test that normalize_tags correctly splits strings using all allowed delimiter characters."""
        tags_str = f"tag1{delimiter}tag2{delimiter}tag3"
        result = modelutils.normalize_tags(tags_str)
        assert len(result) == 3
        assert "tag1" in result
        assert "tag2" in result
        assert "tag3" in result

    def test_normalize_tags_handles_iterable_input(self):
        """Test that normalize_tags correctly processes iterable input and returns normalized list."""
        result = modelutils.normalize_tags(["tag1", "tag2", "tag3"])
        assert len(result) == 3
        assert all(tag in result for tag in ["tag1", "tag2", "tag3"])

    def test_normalize_tags_lowercases_and_strips_tags(self):
        """Test that normalize_tags converts tags to lowercase and removes whitespace."""
        result = modelutils.normalize_tags("  TAG1  ,  TAG2  ,  TAG3  ")
        assert all(tag == tag.lower() and tag == tag.strip() for tag in result)

    def test_normalize_tags_removes_duplicates(self):
        """Test that normalize_tags removes duplicate tags from the result."""
        result = modelutils.normalize_tags("tag1,tag2,tag1,tag3,tag2")
        assert len(result) == 3
        assert set(result) == {"tag1", "tag2", "tag3"}

    def test_normalize_tags_filters_invalid_characters(self):
        """Test that normalize_tags filters out tags containing invalid characters."""
        result = modelutils.normalize_tags("valid-tag,invalid@tag,another_valid")
        assert "valid-tag" in result
        assert "another_valid" in result
        assert "invalid@tag" not in result

    def test_normalize_tags_raises_value_error_when_no_valid_tags(self):
        """Test that normalize_tags raises ValueError when no valid tags are found after filtering."""
        with pytest.raises(ValueError, match="No valid tags found"):
            modelutils.normalize_tags("invalid@tag#123")

    def test_normalize_tags_handles_empty_string_raises_error(self):
        """Test that normalize_tags raises ValueError when given an empty string."""
        with pytest.raises(ValueError, match="No valid tags found"):
            modelutils.normalize_tags("")


class TestMakeClassValidator:
    """Test suite for make_class_validator function."""

    def test_make_class_validator_returns_callable(self, sample_base_class):
        """Test that make_class_validator returns a callable validator function."""
        validator = modelutils.make_class_validator(sample_base_class)
        assert callable(validator)

    def test_make_class_validator_returns_class_when_given_class_type(self, sample_derived_class, mock_validation_info):
        """Test that validator returns the class directly when given a class type."""
        validator = modelutils.make_class_validator(object)
        result = validator(sample_derived_class, mock_validation_info)
        assert result == sample_derived_class
        assert inspect.isclass(result)

    @patch("papita_txnsmodel.utils.modelutils.ClassDiscovery")
    def test_make_class_validator_loads_class_from_string(self, mock_class_discovery, sample_derived_class, mock_validation_info):
        """Test that validator loads class from string using ClassDiscovery.select."""
        mock_class_discovery.select.return_value = sample_derived_class
        validator = modelutils.make_class_validator(object)
        result = validator("module.ClassName", mock_validation_info)
        assert result == sample_derived_class
        mock_class_discovery.select.assert_called_once_with("module.ClassName", class_type=object)

    @patch("papita_txnsmodel.utils.modelutils.ClassDiscovery")
    def test_make_class_validator_raises_value_error_for_invalid_string(self, mock_class_discovery, mock_validation_info):
        """Test that validator raises ValueError when ClassDiscovery.select returns non-class."""
        mock_class_discovery.select.return_value = "not_a_class"
        validator = modelutils.make_class_validator(object)
        with pytest.raises(ValueError, match="Class type not supported"):
            validator("invalid.class", mock_validation_info)

    def test_make_class_validator_raises_value_error_for_non_class_non_string(self, sample_base_class, mock_validation_info):
        """Test that validator raises ValueError when given neither class nor string."""
        validator = modelutils.make_class_validator(sample_base_class)
        with pytest.raises(ValueError, match="Class type not supported"):
            validator(123, mock_validation_info)


class TestParseDates:
    """Test suite for parse_dates function."""

    def test_parse_dates_returns_none_for_empty_value(self):
        """Test that parse_dates returns None when given empty or falsy value."""
        assert modelutils.parse_dates(None) is None
        assert modelutils.parse_dates("") is None
        assert modelutils.parse_dates(0) is None

    def test_parse_dates_handles_pandas_timestamp(self):
        """Test that parse_dates correctly handles pandas Timestamp input."""
        ts = pd.Timestamp("2023-01-01", tz=pytz.UTC)
        result = modelutils.parse_dates(ts)
        assert isinstance(result, pd.Timestamp)
        assert result.tz == pytz.UTC

    def test_parse_dates_handles_datetime_object(self):
        """Test that parse_dates correctly converts datetime object to pandas Timestamp."""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        result = modelutils.parse_dates(dt)
        assert isinstance(result, pd.Timestamp)
        assert result.tz == pytz.UTC

    def test_parse_dates_handles_date_object(self):
        """Test that parse_dates correctly converts date object to UTC-localized Timestamp."""
        d = date(2023, 1, 1)
        result = modelutils.parse_dates(d)
        assert isinstance(result, pd.Timestamp)
        assert result.tz == pytz.UTC
        assert result.date() == d

    def test_parse_dates_handles_string_date(self):
        """Test that parse_dates correctly parses string date using dateutil parser."""
        result = modelutils.parse_dates("2023-01-01")
        assert isinstance(result, pd.Timestamp)
        assert result.tz == pytz.UTC

    def test_parse_dates_handles_unix_timestamp_seconds(self):
        """Test that parse_dates correctly converts integer unix timestamp in seconds."""
        timestamp = 1672531200  # 2023-01-01 00:00:00 UTC
        result = modelutils.parse_dates(timestamp)
        assert isinstance(result, pd.Timestamp)
        assert result.tz == pytz.UTC

    def test_parse_dates_handles_unix_timestamp_milliseconds(self):
        """Test that parse_dates correctly converts integer unix timestamp in milliseconds."""
        timestamp_ms = 1672531200000  # 2023-01-01 00:00:00 UTC in milliseconds
        result = modelutils.parse_dates(timestamp_ms)
        assert isinstance(result, pd.Timestamp)
        assert result.tz == pytz.UTC

    def test_parse_dates_handles_float_timestamp(self):
        """Test that parse_dates correctly converts float unix timestamp."""
        timestamp = 1672531200.5
        result = modelutils.parse_dates(timestamp)
        assert isinstance(result, pd.Timestamp)
        assert result.tz == pytz.UTC

    def test_parse_dates_returns_none_for_invalid_string(self):
        """Test that parse_dates returns None when string parsing fails."""
        result = modelutils.parse_dates("invalid-date-string")
        assert result is None

    def test_parse_dates_localizes_naive_timestamp_to_utc(self):
        """Test that parse_dates localizes naive timestamps to UTC timezone."""
        naive_ts = pd.Timestamp("2023-01-01")
        result = modelutils.parse_dates(naive_ts)
        assert result.tz == pytz.UTC

    def test_parse_dates_converts_timezone_aware_timestamp_to_utc(self):
        """Test that parse_dates converts timezone-aware timestamps to UTC."""
        est_ts = pd.Timestamp("2023-01-01", tz=pytz.timezone("US/Eastern"))
        result = modelutils.parse_dates(est_ts)
        assert result.tz == pytz.UTC


class TestValidateDates:
    """Test suite for validate_dates function."""

    def test_validate_dates_calls_handler_with_parsed_date(self, mock_handler):
        """Test that validate_dates calls handler with result from parse_dates."""
        mock_handler.return_value = pd.Timestamp("2023-01-01", tz=pytz.UTC)
        result = modelutils.validate_dates("2023-01-01", mock_handler)
        assert isinstance(result, pd.Timestamp)
        mock_handler.assert_called_once()

    def test_validate_dates_returns_none_when_parse_dates_returns_none(self, mock_handler):
        """Test that validate_dates returns None when parse_dates fails."""
        mock_handler.return_value = None
        result = modelutils.validate_dates("invalid-date", mock_handler)
        assert result is None


class TestValidateInterestRate:
    """Test suite for validate_interest_rate function."""

    def test_validate_interest_rate_returns_none_for_empty_value(self, mock_handler):
        """Test that validate_interest_rate returns None when given empty or falsy value."""
        mock_handler.return_value = None
        result = modelutils.validate_interest_rate(0, mock_handler)
        assert result is None

    def test_validate_interest_rate_normalizes_percentage_to_decimal(self, mock_handler):
        """Test that validate_interest_rate converts percentage values (>=1.0) to decimal format."""
        mock_handler.return_value = 5.0
        result = modelutils.validate_interest_rate(5.0, mock_handler)
        assert result == 0.05

    def test_validate_interest_rate_keeps_decimal_unchanged(self, mock_handler):
        """Test that validate_interest_rate leaves decimal values (<1.0) unchanged."""
        mock_handler.return_value = 0.05
        result = modelutils.validate_interest_rate(0.05, mock_handler)
        assert result == 0.05

    def test_validate_interest_rate_rounds_result(self, mock_handler):
        """Test that validate_interest_rate rounds the result using numpy around function."""
        mock_handler.return_value = 5.123456
        result = modelutils.validate_interest_rate(5.123456, mock_handler)
        assert result == 0.05123456

    def test_validate_interest_rate_handles_boundary_value_one(self, mock_handler):
        """Test that validate_interest_rate correctly handles boundary value of 1.0."""
        mock_handler.return_value = 1.0
        result = modelutils.validate_interest_rate(1.0, mock_handler)
        assert result == 0.01

    def test_validate_interest_rate_handles_large_percentage(self, mock_handler):
        """Test that validate_interest_rate correctly normalizes large percentage values."""
        mock_handler.return_value = 25.5
        result = modelutils.validate_interest_rate(25.5, mock_handler)
        assert result == 0.255
