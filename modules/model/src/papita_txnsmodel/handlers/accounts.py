# pylint: disable=access-member-before-definition
# mypy: disable-error-code="has-type"
"""
Account Table Handler Module.

This module provides functionality for loading and processing account table data
in the Papita transaction system. It defines various account table handler classes
that serve as interfaces between the transaction registrar and different account
data service layers.

The module includes specialized handlers for different types of accounts:
- General accounts (AccountsTableHandler)
- Asset accounts (AssetAccountsTableHandler)
- Liability accounts (LiabilityAccountsTableHandler)
- Financed asset accounts (FinancedAssetAccountsTableHandler)
- Account indexing (AccountsIndexerTableHandler)

Each handler leverages corresponding service classes to load, transform,
and process account data from various sources, providing a clean abstraction
layer over the data processing operations.
"""

from typing import Self, Tuple

from pydantic import model_validator

from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.assets import (
    AssetAccountsService,
    FinancedAssetAccountsService,
    RealEstateAssetAccountsService,
    TradingAssetAccountsService,
)
from papita_txnsmodel.services.indexers import AccountsIndexerService
from papita_txnsmodel.services.liabilities import (
    BankCreditLiabilityAccountsService,
    CreditCardLiabilityAccountsService,
    LiabilityAccountsService,
)
from papita_txnsmodel.services.types import TypesService

from .base import BaseTableHandler


class AccountsTableHandler(BaseTableHandler[AccountsService, ...]):
    """Handler for loading and processing general account table data.

    This handler specializes in managing account-related data by leveraging the
    AccountsService. It provides methods to load, process, and dump account data
    through the service layer.

    The handler acts as an intermediary between raw data sources and the account
    service, performing necessary transformations and validations on the data
    before it's processed by the service.

    Attributes:
        Inherits all attributes from BaseTableHandler, with AccountsService
        as the parameterized service type. These typically include configuration
        settings, connection parameters, and processing options.

    Examples:
        ```python
        handler = AccountsTableHandler(config)
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
        return "accounts", "accounts_table", "account_table", "general_accounts"


class AssetAccountsTableHandler(BaseTableHandler[AssetAccountsService, ...]):
    """Handler for loading and processing asset account table data.

    This specialized handler manages accounts that represent assets, such as
    savings accounts, investment accounts, or property holdings. It leverages
    the AssetAccountsService to perform operations specific to asset accounts.

    The handler ensures that asset account data is correctly loaded, transformed,
    and processed according to the business rules defined in the service layer.

    Attributes:
        Inherits attributes from BaseTableHandler with AssetAccountsService
        as the parameterized service type. These typically include configuration
        settings, connection parameters, and processing options specific to
        asset accounts.
    """

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        """Get the label identifiers for this asset accounts handler.

        Returns:
            Tuple[str, ...]: A tuple of string labels that identify this handler
                in the handler registry system. These labels can be used to look up
                or reference this specific asset account handler type.
        """
        return "asset_accounts_table", "asset_accounts", "assets_table", "assets"


class LiabilityAccountsTableHandler(BaseTableHandler[LiabilityAccountsService, ...]):
    """Handler for loading and processing liability account table data.

    This specialized handler manages accounts that represent liabilities, such as
    loans, credit card debts, or mortgages. It utilizes the LiabilityAccountsService
    to handle operations specific to liability accounts.

    The handler ensures that liability account data is accurately loaded,
    transformed, and processed in accordance with the rules defined in the
    service layer.

    Attributes:
        Inherits attributes from BaseTableHandler with LiabilityAccountsService
        as the parameterized service type. These typically include configuration
        settings, connection parameters, and processing options specific to
        liability accounts.
    """

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        """Get the label identifiers for this liability accounts handler.

        Returns:
            Tuple[str, ...]: A tuple of string labels that identify this handler
                in the handler registry system. These labels can be used to look up
                or reference this specific liability account handler type.
        """
        return "liability_accounts_table", "liability_accounts", "liabilities_table", "liabilities"


class FinancedAssetAccountsTableHandler(
    BaseTableHandler[FinancedAssetAccountsService, (BankCreditLiabilityAccountsService, AssetAccountsService)]
):
    """Handler for loading and processing financed asset account table data.

    This specialized handler manages accounts that represent assets acquired through
    financing, such as mortgaged properties or financed vehicles. It combines aspects
    of both asset accounts and liability accounts, requiring coordination between
    different services.

    The handler establishes dependencies with both AssetAccountsService and
    BankCreditLiabilityAccountsService to properly process the dual nature of
    financed assets.

    Attributes:
        dependencies: A dictionary mapping service names to service types, used for
            resolving dependencies during processing. Typically includes references to
            asset_account and bank_credit_liability_account services.
    """

    @model_validator(mode="after")
    def _validate(self) -> Self:
        """Validate and set up the dependencies for the financed asset accounts handler.

        This method ensures that the handler has the necessary service dependencies
        established. If no dependencies are defined, it initializes them with the
        required services for processing financed asset accounts.

        Returns:
            Self: The validated instance of FinancedAssetAccountsTableHandler.
        """
        if not self.dependencies:
            self.dependencies = {
                "asset_account": AssetAccountsService,
                "bank_credit_liability_account": BankCreditLiabilityAccountsService,
            }

        return self

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        """Get the label identifiers for this financed asset accounts handler.

        Returns:
            Tuple[str, ...]: A tuple of string labels that identify this handler
                in the handler registry system. These labels can be used to look up
                or reference this specific financed asset account handler type.
        """
        return "financed_asset_accounts_table", "financed_asset_accounts", "assets"


class AccountsIndexerTableHandler(
    BaseTableHandler[
        AccountsIndexerService,
        (
            AccountsService,
            AssetAccountsService,
            LiabilityAccountsService,
            TypesService,
        ),
    ]
):
    """Handler for indexing and cross-referencing different types of account data.

    This comprehensive handler serves as a central point for indexing various account
    types, enabling cross-referencing and unified processing of different account
    categories. It combines functionality from multiple service types to provide
    a consolidated view of the account ecosystem.

    The handler establishes dependencies with a wide range of account-related services,
    including general accounts, assets, liabilities, and type classification services.
    This allows it to index and categorize accounts across the entire system.

    Attributes:
        dependencies: A dictionary mapping service names to service types, used for
            resolving dependencies during the indexing process. Includes references to
            various account-related services for comprehensive indexing.
    """

    @model_validator(mode="after")
    def _validate(self) -> Self:
        """Validate and set up the dependencies for the accounts indexer handler.

        This method ensures that the handler has all necessary service dependencies
        established for comprehensive account indexing. If no dependencies are defined,
        it initializes them with the full range of required services to handle
        different account types and their classifications.

        Returns:
            Self: The validated instance of AccountsIndexerTableHandler.
        """
        if not self.dependencies:
            self.dependencies = {
                "account": AccountsService,
                "asset_account": AssetAccountsService,
                "real_estate_asset_account": RealEstateAssetAccountsService,
                "trading_asset_account": TradingAssetAccountsService,
                "liability_account": LiabilityAccountsService,
                "bank_credit_liability_account": BankCreditLiabilityAccountsService,
                "credit_card_liability_account": CreditCardLiabilityAccountsService,
                "type": TypesService,
            }

        return self

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        """Get the label identifiers for this accounts indexer handler.

        Returns:
            Tuple[str, ...]: A tuple of string labels that identify this handler
                in the handler registry system. These labels can be used to look up
                or reference this specific accounts indexer handler type.
        """
        return "accounts_indexer_table", "accounts_indexer", "account_indexer", "indexer_table", "indexer"
