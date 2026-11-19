"""Unit tests for the frequtils module in the Papita Transactions system.

This test suite validates the FrequencyHandler class functionality including initialization,
frequency comparison operations, and period calculation. All tests use time mocking to ensure
deterministic behavior and avoid external dependencies.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from papita_txnsmodel.utils.frequtils import FrequencyHandler


@pytest.fixture
def fixed_timestamp():
    """Provide a fixed timestamp for deterministic testing."""
    return pd.Timestamp("2024-01-01 00:00:00", tz="UTC")


@pytest.fixture
def daily_frequency_handler(fixed_timestamp):
    """Provide a FrequencyHandler instance with daily frequency for testing."""
    with patch("papita_txnsmodel.utils.frequtils.pd.Timestamp.now", return_value=fixed_timestamp):
        return FrequencyHandler("D", ref_dt=fixed_timestamp)


@pytest.fixture
def monthly_frequency_handler(fixed_timestamp):
    """Provide a FrequencyHandler instance with monthly frequency for testing."""
    with patch("papita_txnsmodel.utils.frequtils.pd.Timestamp.now", return_value=fixed_timestamp):
        return FrequencyHandler("M", ref_dt=fixed_timestamp)


def test_frequency_handler_initializes_with_string_frequency(fixed_timestamp):
    """Test that FrequencyHandler initializes correctly with a string frequency."""
    # Arrange
    freq_str = "D"

    # Act
    handler = FrequencyHandler(freq_str, ref_dt=fixed_timestamp)

    # Assert
    assert handler.freq == "D"
    assert isinstance(handler.offset, pd.DateOffset)
    assert handler.ref_dt == fixed_timestamp


def test_frequency_handler_initializes_with_frequency_handler_instance(daily_frequency_handler, fixed_timestamp):
    """Test that FrequencyHandler initializes correctly from another FrequencyHandler instance."""
    # Arrange
    original_handler = daily_frequency_handler

    # Act
    new_handler = FrequencyHandler(original_handler, ref_dt=fixed_timestamp)

    # Assert
    assert new_handler.freq == original_handler.freq
    assert new_handler.offset == original_handler.offset
    assert new_handler.ref_dt == fixed_timestamp
    assert new_handler.sample_dt == original_handler.sample_dt


def test_frequency_handler_initializes_with_custom_sample_periods(fixed_timestamp):
    """Test that FrequencyHandler initializes correctly with custom sample_periods parameter."""
    # Arrange
    custom_periods = 10

    # Act
    handler = FrequencyHandler("D", ref_dt=fixed_timestamp, sample_periods=custom_periods)

    # Assert
    assert handler.sample_periods == custom_periods


def test_frequency_handler_uses_default_ref_dt_when_none_provided():
    """Test that FrequencyHandler uses current timestamp when ref_dt is not provided."""
    # Arrange
    fixed_now = pd.Timestamp("2024-06-15 12:00:00", tz="UTC")

    # Act
    with patch("papita_txnsmodel.utils.frequtils.pd.Timestamp.now", return_value=fixed_now):
        handler = FrequencyHandler("D")

    # Assert
    assert handler.ref_dt == fixed_now


def test_frequency_handler_comparison_operators_work_correctly(daily_frequency_handler, monthly_frequency_handler):
    """Test that frequency comparison operators (==, !=, <, >, <=, >=) work correctly."""
    # Arrange
    daily = daily_frequency_handler
    monthly = monthly_frequency_handler

    # Act & Assert
    assert daily == "D"
    assert daily != monthly
    assert daily < monthly  # Daily is more frequent (smaller period) than monthly
    assert daily <= monthly
    assert monthly > daily
    assert monthly >= daily


def test_frequency_handler_str_returns_frequency_string(daily_frequency_handler):
    """Test that __str__ method returns the frequency string representation."""
    # Arrange
    handler = daily_frequency_handler

    # Act
    result = str(handler)

    # Assert
    assert result == "D"
    assert isinstance(result, str)


def test_frequency_handler_repr_returns_detailed_representation(daily_frequency_handler):
    """Test that __repr__ method returns detailed string representation of the instance."""
    # Arrange
    handler = daily_frequency_handler

    # Act
    result = repr(handler)

    # Assert
    assert "FrequencyHandler" in result
    assert "freq=" in result
    assert "D" in result


def test_frequency_handler_lshift_returns_one_for_equal_frequencies(daily_frequency_handler):
    """Test that __lshift__ operator returns 1 when frequencies are equal."""
    # Arrange
    handler = daily_frequency_handler

    # Act
    result = handler << "D"

    # Assert
    assert result == 1


def test_frequency_handler_lshift_calculates_periods_correctly(daily_frequency_handler):
    """Test that __lshift__ operator correctly calculates number of periods between frequencies."""
    # Arrange
    handler = daily_frequency_handler

    # Act
    result = handler << "12H"  # 12-hour frequency is more frequent than daily

    # Assert
    assert result > 1
    assert isinstance(result, int)


def test_frequency_handler_lshift_raises_value_error_for_greater_frequency(daily_frequency_handler):
    """Test that __lshift__ operator raises ValueError when other frequency is greater."""
    # Arrange
    handler = daily_frequency_handler

    # Act & Assert
    with pytest.raises(ValueError, match="is greater than"):
        handler << "M"  # Monthly is less frequent (greater period) than daily


def test_frequency_handler_initializes_with_base_offset(fixed_timestamp):
    """Test that FrequencyHandler initializes correctly with a BaseOffset object."""
    # Arrange
    from pandas.tseries.offsets import Day

    offset = Day()

    # Act
    handler = FrequencyHandler(offset, ref_dt=fixed_timestamp)

    # Assert
    assert handler.freq == "D"
    assert isinstance(handler.offset, pd.DateOffset)
    assert handler.ref_dt == fixed_timestamp


def test_frequency_handler_check_freq_raises_type_error_for_unsupported_type(daily_frequency_handler):
    """Test that _check_freq raises TypeError for unsupported input types."""
    # Arrange
    handler = daily_frequency_handler
    invalid_input = 12345

    # Act & Assert
    with pytest.raises(TypeError, match="type.*not supported"):
        handler._check_freq(invalid_input)
