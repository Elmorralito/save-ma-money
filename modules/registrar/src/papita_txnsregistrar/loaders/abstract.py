"""
Abstract loader interface for transaction data loading.

This module defines the base abstract class that all data loaders in the transaction
tracking system must implement. It establishes a common interface for loading data
from various sources, handling errors, and providing access to loaded results.
"""

import abc
from typing import Any

from pydantic import BaseModel

from papita_txnsmodel.utils.classutils import FallbackAction


class AbstractLoader(BaseModel, metaclass=abc.ABCMeta):
    """
    Abstract base class for all transaction data loaders.

    This class combines Pydantic's validation capabilities with an abstract interface
    that defines the core functionality required for all data loaders. Concrete loader
    implementations must inherit from this class and implement its abstract methods
    to provide specific loading behavior for different data sources.

    Attributes:
        error_handler: A FallbackAction instance that determines how errors
            encountered during loading should be handled.
    """

    error_handler: FallbackAction

    @property
    @abc.abstractmethod
    def result(self) -> Any:
        """
        Get the data loaded from the source.

        This property should provide access to the data that has been loaded
        from the source after a successful call to `load()`.

        Returns:
            Any: The loaded data in an implementation-specific format.
        """

    @abc.abstractmethod
    def check_source(self, **kwargs) -> bool:
        """
        Check if the data source is valid and accessible.

        This method should verify that the source exists and is in a state
        that allows data to be loaded from it.

        Args:
            **kwargs: Implementation-specific parameters needed to check the source.

        Returns:
            bool: True if the source is valid and accessible, False otherwise.
        """

    @abc.abstractmethod
    def load(self, **kwargs) -> "AbstractLoader":
        """
        Load data from the source.

        This method should implement the logic for loading data from the source
        and making it available through the `result` property.

        Args:
            **kwargs: Implementation-specific parameters needed to load data.

        Returns:
            AbstractLoader: The loader instance for method chaining.
        """
