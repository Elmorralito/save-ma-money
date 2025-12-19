# pylint: disable=access-member-before-definition
# mypy: disable-error-code="has-type"
"""
Types Table Handler Module.

This module provides functionality for loading and processing type table data
in the Papita transaction system. It defines a type table handler class that
serves as an interface between the transaction registrar and the type data
service layer.

The module includes a handler for type entities:
- General types (TypesTableHandler)

The handler leverages the TypesService to load, transform, and process type
data from various sources, providing a clean abstraction layer over the data
processing operations. Types are used to categorize various entities in the
system, such as different kinds of accounts, assets, or liabilities.
"""

from typing import Tuple

from papita_txnsmodel.services.types import TypesService

from .core import BaseLoadTableHandler


class TypesTableHandler(BaseLoadTableHandler[TypesService, ...]):
    """Handler for loading and processing type table data.

    This handler specializes in managing type-related data by leveraging the
    TypesService. It provides methods to load, process, and dump type data
    through the service layer.

    The handler acts as an intermediary between raw data sources and the type
    service, performing necessary transformations and validations on the data
    before it's processed by the service.

    Types are used to categorize various entities in the system, such as
    different kinds of accounts, assets, or liabilities. This handler manages
    the creation and retrieval of these type classifications.

    Attributes:
        Inherits all attributes from BaseLoadTableHandler, with TypesService
        as the parameterized service type. These typically include configuration
        settings, connection parameters, and processing options.

    Examples:
        ```python
        handler = TypesTableHandler(config)
        handler.load_data(source)
        processed_data = handler.process()
        handler.dump_results(destination)
        ```
    """

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        """Get the label identifiers for this handler.

        Returns:
            Tuple[str, ...]: A tuple of string labels that identify this handler
                in the handler registry system. These labels can be used to look up
                or reference this specific handler type.
        """
        return "types", "types_table", "type_table", "general_types"
