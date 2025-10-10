"""Base handler module for transaction tracking with loader functionality.

This module defines the BaseLoadHandler class which extends the base handler functionality
with data loading capabilities. It provides a foundation for handlers that need to
load data from external sources using specialized loader objects.
"""

from typing import Generic, TypeVar

from papita_txnstracker.loaders.abstract import AbstractLoader

from papita_txnsmodel.handlers.base import BaseHandler, S

L = TypeVar("L", bound=AbstractLoader)


class BaseLoadHandler(BaseHandler[S], Generic[L]):
    """Base handler that incorporates data loading functionality.

    This class extends the BaseHandler to add the ability to load data
    from various sources using an AbstractLoader implementation. It provides
    methods to set up loaders, validate sources, and perform load operations.

    Attributes:
        loader: An instance of a class derived from AbstractLoader that handles
            the actual data loading operations, or None if not yet set up.
    """

    loader: L | None = None

    @property
    def checked_loader(self) -> L:
        """Get the loader after verifying it has been set up.

        Returns:
            The configured loader instance.

        Raises:
            ValueError: If the loader has not been set up yet.
        """
        if not self.loader:
            raise ValueError("Loader not setup.")

        return self.loader

    def setup_loader(self, loader: L, **kwargs) -> "BaseLoadHandler":
        """Configure the handler with a specific loader instance.

        Args:
            loader: An instance of a class derived from AbstractLoader.
            **kwargs: Additional configuration parameters for the loader.
        Returns:
            Self, to allow for method chaining.

        Raises:
            TypeError: If the provided loader is not an instance of AbstractLoader.
        """
        if not isinstance(loader, AbstractLoader):
            raise TypeError("Service type not compatible with this handler.")

        self.loader = loader
        return self

    def load(self, **kwargs) -> "BaseLoadHandler":
        """Load data from the source using the configured loader.

        This method first validates the source using the loader's check_source method
        before proceeding with the actual loading operation.

        Args:
            **kwargs: Parameters to pass to the loader's check_source and load methods.

        Returns:
            Self, to allow for method chaining.

        Raises:
            ValueError: If the source validation fails.
        """
        if not self.checked_loader.check_source(**kwargs):
            raise ValueError("The source to load seems to not be valid.")

        self.checked_loader.load(**kwargs)
        return self

    def dump(self) -> "BaseLoadHandler":
        """Dump loaded data to a destination.

        This method is meant to be implemented by subclasses to provide
        functionality to export or save the loaded data.

        Returns:
            Self, to allow for method chaining.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError()
