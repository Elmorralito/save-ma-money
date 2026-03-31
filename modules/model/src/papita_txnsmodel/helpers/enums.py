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

import logging
from enum import Enum

import pandas as pd
from tabulate import tabulate

_UTILS_LOGGER = logging.getLogger(__name__)


class FallbackAction(Enum):
    """Defines actions to take when post-check validations fail.

    This enum provides strategies for handling validation failures, with methods
    to execute the appropriate action based on the enum value.

    Attributes:
        LOG: Log the error message as a warning but continue execution.
        RAISE: Raise a ValueError with the error message.
        IGNORE: Ignore the error and continue silently.
    """

    LOG = "LOG"
    RAISE = "RAISE"
    IGNORE = "IGNORE"

    def get_logger(self, **kwargs) -> logging.Logger:
        """Retrieves a logger instance from kwargs or returns the default logger.

        Args:
            **kwargs: Keyword arguments that may contain a 'logger' entry.
                If provided, the logger should be an instance of logging.Logger.

        Returns:
            logging.Logger: Either the logger provided in kwargs if valid, or
                the default module logger.
        """
        logger = kwargs.get("logger", _UTILS_LOGGER)
        return logger if isinstance(logger, logging.Logger) else _UTILS_LOGGER

    def handle_ignore(self, message: str | Exception, **kwargs) -> None:
        """Handle failure by ignoring it with minimal logging.

        Args:
            message: The error message to log.
            logger: Optional - Custom logger instance. Default module's logger instance.
            **kwargs: Additional context for the error.
        """
        self.get_logger(**kwargs).debug("Ignoring message: %s", message)

    def handle_log(self, message: str | Exception, logger: logging.Logger, **kwargs) -> None:
        """Handle failure by logging it as a warning.

        Args:
            message: The error message to log.
            logger: Optional - Custom logger instance. Default module's logger instance.
            **kwargs: Additional context for the error.
        """
        logger_ = self.get_logger(logger=logger, **kwargs)
        if isinstance(message, Exception):
            logger_.exception(message, stack_info=True)
            return

        logger_.warning(message)

    def handle_raise(self, message: str | Exception, **kwargs) -> None:
        """Handle failure by raising an exception.

        Args:
            message: The error message to include in the exception.
            **kwargs: Additional context for the error.

        Raises:
            ValueError: Always raised with the provided message.
        """
        if isinstance(message, Exception):
            raise message

        raise ValueError(message)

    def handle(self, message: str | Exception, **kwargs) -> None:
        """Apply the appropriate failure handling strategy.

        Dynamically dispatches to the specific handler method based on the enum value.

        Args:
            message: The error message to handle.
            logger: Optional - Custom logger instance. Default module's logger instance.
            **kwargs: Additional context for the error.
        """
        return getattr(self, f"handle_{self.value.lower()}")(message, **kwargs)


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

    def choose_fail(self, *, matches: pd.DataFrame, **kwargs) -> pd.Series:
        """
        Handles multiple matches by raising an exception.

        Creates a formatted table of all matches and raises an exception with
        this information to alert the caller about the ambiguous matches.

        Args:
            matches: DataFrame containing the multiple matching transactions
            **kwargs: Additional arguments passed to the FallbackAction handler

        Returns:
            pd.Series: Never returns as it raises an exception

        Raises:
            Exception: Always raises an exception with details about the matches
        """
        results = tabulate(matches, headers="keys", tablefmt="fancy_grid")
        FallbackAction.RAISE.handle(f"There are multiple matches on transactions:\n{results}", **kwargs)

    def choose_first(self, *, matches: pd.DataFrame, **kwargs) -> pd.Series:
        """
        Handles multiple matches by selecting the first match.

        Args:
            matches: DataFrame containing the multiple matching transactions
            **kwargs: Additional arguments (unused)

        Returns:
            pd.Series: The first matching transaction or an empty DataFrame if no matches
        """
        if matches.empty:
            return matches

        return matches.iloc[0]  # Note: This returns the second row (index 1), which may be a bug

    def choose_last(self, *, matches: pd.DataFrame, **kwargs) -> pd.Series:
        """
        Handles multiple matches by selecting the last match.

        Args:
            matches: DataFrame containing the multiple matching transactions
            **kwargs: Additional arguments (unused)

        Returns:
            pd.Series: The last matching transaction or an empty DataFrame if no matches
        """
        if matches.empty:
            return matches

        return matches.iloc[-1]

    def choose(self, *, matches: pd.DataFrame, **kwargs) -> pd.Series | pd.DataFrame:
        """
        Dispatches to the appropriate handler based on the enum value.

        This method dynamically selects and calls the appropriate handler method
        based on the current enum value (FAIL, FIRST, or LAST). It handles the
        cases of zero or one match before dispatching to the specific strategy.

        Args:
            matches: DataFrame containing the matching transactions
            **kwargs: Additional arguments passed to the specific handler

        Returns:
            pd.Series | pd.DataFrame: The selected transaction or an empty DataFrame if no match.

        Raises:
            Exception: If the FAIL strategy is selected and multiple matches exist
        """
        if matches.empty:
            return matches

        if len(matches) == 1:
            return matches.iloc[0]

        func = getattr(self, f"choose_{self.value.lower()}")
        return func(matches=matches, **kwargs)
