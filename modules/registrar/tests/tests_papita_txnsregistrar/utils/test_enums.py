"""Test suite for OnMultipleMatchesDo enumeration.

This module contains unit tests for the OnMultipleMatchesDo enum class, which provides
strategies for handling multiple matching transactions. The tests verify that each enum
value correctly implements its strategy (FAIL, FIRST, LAST) and that the dispatcher
method properly routes to the appropriate handler. Tests cover edge cases including
empty DataFrames, single-row DataFrames, and multiple-row DataFrames.
"""

import pandas as pd
import pytest
from unittest.mock import patch

from papita_txnsregistrar.utils.enums import OnMultipleMatchesDo


def test_enum_values_are_correct():
    """Test that OnMultipleMatchesDo enum has the expected three values."""
    assert OnMultipleMatchesDo.FAIL.value == "FAIL"
    assert OnMultipleMatchesDo.FIRST.value == "FIRST"
    assert OnMultipleMatchesDo.LAST.value == "LAST"
    assert len(OnMultipleMatchesDo) == 3


@patch("papita_txnsregistrar.utils.enums.FallbackAction")
@patch("papita_txnsregistrar.utils.enums.tabulate")
def test_choose_fail_raises_value_error_with_formatted_table(mock_tabulate, mock_fallback_action):
    """Test that choose_fail formats DataFrame and raises ValueError via FallbackAction."""
    # Arrange
    matches = pd.DataFrame({"id": [1, 2], "amount": [100.0, 200.0]})
    mock_tabulate.return_value = "formatted_table"
    mock_fallback_action.RAISE.handle.side_effect = ValueError("Multiple matches error")

    # Act & Assert
    with pytest.raises(ValueError, match="Multiple matches error"):
        OnMultipleMatchesDo.FAIL.choose_fail(matches=matches)

    mock_tabulate.assert_called_once_with(matches, headers="keys", tablefmt="fancy_grid")
    mock_fallback_action.RAISE.handle.assert_called_once()
    call_args = mock_fallback_action.RAISE.handle.call_args[0][0]
    assert "There are multiple matches on transactions:" in call_args
    assert "formatted_table" in call_args


def test_choose_first_returns_first_row():
    """Test that choose_first returns the first row of a multi-row DataFrame as a Series."""
    # Arrange
    matches = pd.DataFrame({"id": [1, 2, 3], "amount": [100.0, 200.0, 300.0]})

    # Act
    result = OnMultipleMatchesDo.FIRST.choose_first(matches=matches)

    # Assert
    assert isinstance(result, pd.Series)
    assert result["id"] == 1
    assert result["amount"] == 100.0


def test_choose_first_returns_empty_dataframe_for_empty_input():
    """Test that choose_first returns empty DataFrame when input DataFrame is empty."""
    # Arrange
    matches = pd.DataFrame()

    # Act
    result = OnMultipleMatchesDo.FIRST.choose_first(matches=matches)

    # Assert
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_choose_last_returns_last_row():
    """Test that choose_last returns the last row of a multi-row DataFrame as a Series."""
    # Arrange
    matches = pd.DataFrame({"id": [1, 2, 3], "amount": [100.0, 200.0, 300.0]})

    # Act
    result = OnMultipleMatchesDo.LAST.choose_last(matches=matches)

    # Assert
    assert isinstance(result, pd.Series)
    assert result["id"] == 3
    assert result["amount"] == 300.0


def test_choose_last_returns_empty_dataframe_for_empty_input():
    """Test that choose_last returns empty DataFrame when input DataFrame is empty."""
    # Arrange
    matches = pd.DataFrame()

    # Act
    result = OnMultipleMatchesDo.LAST.choose_last(matches=matches)

    # Assert
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_choose_dispatches_to_choose_first():
    """Test that choose method correctly dispatches to choose_first when enum value is FIRST."""
    # Arrange
    matches = pd.DataFrame({"id": [1, 2], "amount": [100.0, 200.0]})

    # Act
    result = OnMultipleMatchesDo.FIRST.choose(matches=matches)

    # Assert
    assert isinstance(result, pd.Series)
    assert result["id"] == 1
    assert result["amount"] == 100.0


def test_choose_dispatches_to_choose_last():
    """Test that choose method correctly dispatches to choose_last when enum value is LAST."""
    # Arrange
    matches = pd.DataFrame({"id": [1, 2], "amount": [100.0, 200.0]})

    # Act
    result = OnMultipleMatchesDo.LAST.choose(matches=matches)

    # Assert
    assert isinstance(result, pd.Series)
    assert result["id"] == 2
    assert result["amount"] == 200.0


@patch("papita_txnsregistrar.utils.enums.FallbackAction")
@patch("papita_txnsregistrar.utils.enums.tabulate")
def test_choose_dispatches_to_choose_fail(mock_tabulate, mock_fallback_action):
    """Test that choose method correctly dispatches to choose_fail when enum value is FAIL."""
    # Arrange
    matches = pd.DataFrame({"id": [1, 2], "amount": [100.0, 200.0]})
    mock_tabulate.return_value = "formatted_table"
    mock_fallback_action.RAISE.handle.side_effect = ValueError("Multiple matches error")

    # Act & Assert
    with pytest.raises(ValueError, match="Multiple matches error"):
        OnMultipleMatchesDo.FAIL.choose(matches=matches)

    mock_tabulate.assert_called_once()
    mock_fallback_action.RAISE.handle.assert_called_once()


def test_choose_first_with_single_row_returns_series():
    """Test that choose_first returns a Series when DataFrame contains only one row."""
    # Arrange
    matches = pd.DataFrame({"id": [1], "amount": [100.0]})

    # Act
    result = OnMultipleMatchesDo.FIRST.choose_first(matches=matches)

    # Assert
    assert isinstance(result, pd.Series)
    assert result["id"] == 1
    assert result["amount"] == 100.0
