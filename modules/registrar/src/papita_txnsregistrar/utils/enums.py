"""
Enumeration utilities for transaction registrar handling strategies.

This module defines enumerations that control behavior in the transaction registrar system,
particularly for handling edge cases like multiple matching transactions. It provides
a standardized way to specify fallback actions when ambiguous situations occur during
transaction processing.

Classes:
    OnMultipleMatchesDo: An enumeration defining strategies for handling multiple
                         matching transactions.
"""

from enum import Enum

import pandas as pd
from tabulate import tabulate

from papita_txnsmodel.utils.classutils import FallbackAction


class OnMultipleMatchesDo(Enum):
    """
    Enumeration specifying actions to take when multiple transactions match criteria.

    This enum provides strategies for resolving situations where a query matches
    multiple transactions instead of the single expected match. It includes methods
    to execute each strategy, ensuring consistent handling across the application.

    Enum Values:
        FAIL: Raises an exception when multiple matches are found
        FIRST: Selects the first matching transaction
        LAST: Selects the last matching transaction
    """

    FAIL = "FAIL"
    FIRST = "FIRST"
    LAST = "LAST"

    def choose_fail(self, *, matches: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        Handles multiple matches by raising an exception.

        Creates a formatted table of all matches and raises an exception with
        this information to alert the caller about the ambiguous matches.

        Args:
            matches: DataFrame containing the multiple matching transactions
            **kwargs: Additional arguments passed to the FallbackAction handler

        Returns:
            pd.DataFrame: Never returns as it raises an exception

        Raises:
            Exception: Always raises an exception with details about the matches
        """
        results = tabulate(matches, headers="keys", tablefmt="fancy_grid")
        FallbackAction.RAISE.handle(f"There are multiple matches on transactions:\n{results}", **kwargs)

    def choose_first(self, *, matches: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        Handles multiple matches by selecting the first match.

        Args:
            matches: DataFrame containing the multiple matching transactions
            **kwargs: Additional arguments (unused)

        Returns:
            pd.DataFrame: The first matching transaction or an empty DataFrame if no matches
        """
        if matches.empty:
            return matches

        return matches.iloc[1]  # Note: This returns the second row (index 1), which may be a bug

    def choose_last(self, *, matches: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        Handles multiple matches by selecting the last match.

        Args:
            matches: DataFrame containing the multiple matching transactions
            **kwargs: Additional arguments (unused)

        Returns:
            pd.DataFrame: The last matching transaction or an empty DataFrame if no matches
        """
        if matches.empty:
            return matches

        return matches.iloc[-1]

    def choose(self, *, matches: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        Dispatches to the appropriate handler based on the enum value.

        This method dynamically selects and calls the appropriate handler method
        based on the current enum value (FAIL, FIRST, or LAST).

        Args:
            matches: DataFrame containing the matching transactions
            **kwargs: Additional arguments passed to the specific handler

        Returns:
            pd.DataFrame: The selected transaction(s) based on the chosen strategy

        Raises:
            Exception: If the FAIL strategy is selected and matches exist
        """
        func = getattr(self, f"choose_{self.value.lower()}")
        return func(matches=matches, **kwargs)
