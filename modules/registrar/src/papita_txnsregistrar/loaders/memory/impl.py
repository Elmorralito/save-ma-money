"""In-memory data loader implementation for the Papita Transactions system.

This module provides an implementation of a loader that works with in-memory data sources,
particularly pandas DataFrames. The InMemoryLoader enables loading, validating, and
managing in-memory data structures that can be used in the transaction registration process.
It serves as a utility for handling data that's already loaded into memory and needs to be
processed by the transaction system.
"""

from typing import Self

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class InMemoryLoader(BaseModel):
    """Loader implementation for in-memory data sources using pandas DataFrames.

    This class provides functionality to handle data that's already in memory,
    specifically in the form of pandas DataFrames. It allows for validating the data
    structure, loading it into the loader, and clearing it when needed. The loader
    maintains a dictionary mapping data source names to their corresponding DataFrames.

    Attributes:
        _result: Dictionary mapping data source names to pandas DataFrames.
            This internal attribute stores the loaded data.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    _result: dict[str, pd.DataFrame] = Field(default_factory=dict)

    @property
    def result(self) -> dict[str, pd.DataFrame]:
        """Get the loaded in-memory data.

        Returns:
            dict[str, pd.DataFrame]: Dictionary mapping data source names to pandas DataFrames.
        """
        return self._result

    def check_source(self, **kwargs) -> Self:
        """Validate the data source structure and format.

        Checks if the provided data source is a valid dictionary containing pandas DataFrames.
        The data can be provided through several possible kwargs: 'data', 'data_source', or 'result'.

        Args:
            **kwargs: Keyword arguments containing the data source. Expected keys are:
                - data: Primary key for the data source
                - data_source: Alternative key for the data source
                - result: Fallback key for the data source

        Returns:
            Self: The loader instance for method chaining.

        Raises:
            ValueError: If the data is not a dictionary or if any values in the dictionary
                are not pandas DataFrames.
        """
        data = kwargs.get("data", kwargs.get("data_source", kwargs.get("result", {})))
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary and non-empty mapping.")

        if not all(isinstance(value, pd.DataFrame) for value in data.values()):
            raise ValueError("All values in the dictionary must be pandas DataFrames.")

        self._result = data
        return self

    def load(self, **kwargs) -> Self:
        """Load data from the provided source into the loader.

        This method validates and loads the data source by calling check_source.
        It's a convenience method that ensures data is properly validated before use.

        Args:
            **kwargs: Keyword arguments to pass to check_source for data validation.

        Returns:
            Self: The loader instance for method chaining.
        """
        self.check_source(**kwargs)
        return self

    def unload(self, **kwargs) -> Self:
        """Clear all loaded data from the loader.

        Removes all previously loaded data and resets the internal storage to an empty dictionary.
        This is useful when reusing the loader instance for different data sources.

        Args:
            **kwargs: Optional keyword arguments (not used in the current implementation).

        Returns:
            Self: The loader instance for method chaining.
        """
        del self._result
        self._result = {}.copy()
        return self
