# pylint: disable=access-member-before-definition
# mypy: disable-error-code="has-type"
"""
Account Table Handler Module.

This module provides functionality for loading and processing v3 consolidated account
table data in the Papita transaction system.
"""

from typing import Tuple

from papita_txnsmodel.services.accounts import AccountsService

from .base import BaseTableHandler


class AccountsTableHandler(BaseTableHandler[AccountsService, ...]):
    """Handler for loading and processing general account table data.

    This handler specializes in managing account-related data by leveraging the
    AccountsService. It provides methods to load, process, and dump account data
    through the service layer.
    """

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        """Get the label identifiers for this handler.

        Returns:
            Tuple[str, ...]: Labels that identify this handler in the registry.
        """
        return "accounts", "accounts_table", "account_table", "general_accounts"
