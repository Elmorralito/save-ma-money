"""Abstract base for API request handlers."""

import abc


class AbstractHandler(abc.ABC):
    """Contract for classes that handle an API or domain operation."""

    @abc.abstractmethod
    def handle(self, *args, **kwargs):
        """Run the handler logic; subclasses define parameters and return type."""
