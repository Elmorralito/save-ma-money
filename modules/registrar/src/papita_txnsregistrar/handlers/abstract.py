"""
Base handler module for transaction tracking with loader functionality.

This module defines the AbstractLoadHandler class which extends the base handler functionality
with data loading capabilities. It provides a foundation for handlers that need to
load data from external sources and process transactions through specialized service objects.

Classes:
    AbstractLoadHandler: Abstract base class for handlers with data loading functionality
                         that work with service components.
"""

import abc
import logging
from typing import Generic, List, Self, TypeVar

import pandas as pd
from pydantic import BaseModel, ConfigDict

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.utils.classutils import FallbackAction

logger = logging.getLogger(__name__)

S = TypeVar("S", bound=BaseService)


class AbstractLoadHandler(BaseModel, Generic[S], metaclass=abc.ABCMeta):
    """
    Abstract base handler that incorporates data loading functionality.

    This class defines the interface for handlers that load transaction data from various
    sources and process it through a service component. It serves as a bridge between
    data sources and the transaction processing services. Implementations must provide
    concrete implementations of the abstract methods for specific loading and dumping behaviors.

    The handler uses a generic type parameter S that must be a subclass of BaseService,
    allowing for type-safe integration with different service implementations while
    maintaining a consistent interface.

    Attributes:
        service (S): Service instance used for processing the loaded data and interacting
            with the data access layer. Must be a subclass of BaseService.
        _loaded_data (pd.DataFrame | None): Internal storage for loaded data, accessible
            only to subclasses. Initially None until data is loaded.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    service: S
    on_failure_do: FallbackAction = FallbackAction.RAISE
    _loaded_data: pd.DataFrame | None = None

    @abc.abstractmethod
    def dump(self, **kwargs) -> Self:
        """
        Dump loaded data to a destination, using the service as intermediary.

        This method should be implemented by subclasses to export or persist the
        loaded transaction data. It might save to a database, file, or other storage
        medium using the service component to handle the actual data operations.

        Args:
            **kwargs: Implementation-specific parameters for controlling the dump
                operation, such as destination paths, format options, or filters.

        Returns:
            AbstractLoadHandler: Self reference for method chaining.

        Raises:
            NotImplementedError: When called directly on the abstract class.
        """

    @abc.abstractmethod
    def load(self, *, data: pd.DataFrame | List[TableDTO] | List[dict] | TableDTO, **kwargs) -> Self:
        """
        Load data from the provided DataFrame.

        This method should be implemented by subclasses to load transaction data
        from the provided DataFrame, apply any necessary transformations, and
        prepare it for processing by the service component.

        Args:
            data: DataFrame containing the transaction data to be loaded.
            **kwargs: Additional parameters for controlling the load operation,
                such as transformation options or validation settings.

        Returns:
            AbstractLoadHandler: Self reference for method chaining.

        Raises:
            NotImplementedError: When called directly on the abstract class.
            ValueError: If the data cannot be loaded or fails validation.
        """

    def _load_core_data(self, service: BaseService) -> pd.DataFrame:
        """
        Load records from the service's underlying data store.

        This protected helper method retrieves records from the data store associated
        with the specified service, using the service's data access capabilities.

        Args:
            service: BaseService instance that provides access to the data store.

        Returns:
            pd.DataFrame: DataFrame containing the records retrieved from the service.
        """
        logger.debug("Loading records from %s", service.dto_type.__dao_type__.__tablename__)
        return service.get_records(None)
