"""
Account Table Handler Module.
This module provides functionality for loading and processing account table data
in the Papita transaction system. It defines the AccountTableHandler class which
serves as an interface between the transaction registrar and the accounts data
service layer.

The module specializes in handling account-related operations by leveraging the
AccountsService to load, transform, and process account data from various sources.
"""

from papita_txnsmodel.services.accounts import AccountsService

from .core import BaseLoadTableHandler


class AccountTableHandler(BaseLoadTableHandler[AccountsService]):
    """
    Handler for loading and processing account table data.

    This handler specializes in managing account-related data by leveraging the
    AccountsService. It provides methods to load, process, and dump account data
    through the service layer.

    The handler acts as an intermediary between raw data sources and the account
    service, performing necessary transformations and validations on the data
    before it's processed by the service.

    Attributes:
        Inherits all attributes from BaseLoadTableHandler, with AccountsService
        as the parameterized service type. These typically include configuration
        settings, connection parameters, and processing options.

    Examples:
        ```python
        handler = AccountTableHandler(config)
        handler.load_data(source)
        processed_data = handler.process()
        handler.dump_results(destination)
        ```
    """
