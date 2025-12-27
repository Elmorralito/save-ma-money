"""
Excel contract builder module for transaction registration.

This module provides the ExcelContractBuilder class which builds contract handlers
and services for processing Excel files. It creates appropriate handlers for each
sheet in an Excel file and builds the necessary services to process transaction data.
The builder acts as a coordinator between Excel data sources and transaction handlers.
"""

import logging
from typing import Annotated, Dict, Self, Type

from pydantic import Field

from papita_txnsmodel.handlers.abstract import AbstractHandler
from papita_txnsmodel.handlers.factory import HandlerFactory
from papita_txnsregistrar.builders.base import BaseContractBuilder

logger = logging.getLogger(__name__)


class ExcelContractBuilder(BaseContractBuilder):
    """Builder for creating and configuring Excel file processing contracts.

    This builder is responsible for constructing the processing pipeline for Excel files.
    It creates handlers for each sheet in an Excel file, builds corresponding services,
    and manages the relationships between loaders, handlers, and services. The builder
    follows a fluent interface pattern, allowing method chaining for construction steps.

    The builder workflow includes:
    1. Building a loader to read Excel files
    2. Creating appropriate handlers for each sheet found in the Excel file
    3. Building services that utilize these handlers for data processing

    Attributes:
        handlers: Dictionary mapping sheet names to their corresponding handler
            instances or handler types. Each handler is responsible for processing
            a specific sheet in the Excel file.
    """

    handlers: Annotated[Dict[str, Type[AbstractHandler] | AbstractHandler], Field(default_factory=dict)]

    def build_handler(self, **kwargs) -> Self:
        """Build handlers for each sheet in the Excel file.

        Creates handler instances for each sheet found in the Excel file. The method
        loads the Excel file using the previously built loader, identifies all available
        sheets, and creates appropriate handlers for each sheet using the HandlerFactory.

        Args:
            **kwargs: Configuration parameters including:
                handler_modules: List of modules where handlers are defined.
                Other parameters passed to the loader and handlers.

        Returns:
            Self: The builder instance for method chaining.

        Raises:
            ValueError: If the loader has not been built before calling this method.
        """
        if not self.loader:
            raise ValueError("Loader not built.")

        logger.info("Checking source for loader %s", self.loader)
        sheets = self.loader.check_source(**kwargs).load(**kwargs).result
        logger.info("Building handlers for sheets %s", set(sheets))
        factory = HandlerFactory.load(*tuple(kwargs.get("handler_modules", [])), **kwargs)
        self.handlers = {sheet.strip(): factory.get(sheet.strip(), **kwargs) for sheet in sheets}
        return self

    def build_service(self, **kwargs) -> Self:
        """Build services for each handler.

        Creates service instances for each handler previously built. This connects
        the handlers to their respective service implementations for processing the
        data from each Excel sheet.

        Args:
            **kwargs: Configuration parameters to pass to the service builders.

        Returns:
            Self: The builder instance for method chaining.
        """
        handlers = {}.copy()
        for handler_name, handler_type in self.handlers.items():
            self.handler = handler_type
            super().build_service(**kwargs)
            handlers[handler_name] = self.handler.model_validate({"service": self.service, **kwargs})
            logger.debug(
                "Built handler %s(labels=%s)",
                handlers[handler_name].__class__.__name__,
                handlers[handler_name].labels(),
            )

        self.handlers = handlers
        return self

    def build(self, **kwargs) -> Self:
        """Execute the complete build process.

        Chains together all build steps in the correct order: loader, handler, and service.
        This is a convenience method for performing the entire build process in one call.

        Args:
            **kwargs: Configuration parameters to pass to all build methods.

        Returns:
            Self: The builder instance after completing all build steps.
        """
        return self.build_loader(**kwargs).build_handler(**kwargs).build_service(**kwargs)
