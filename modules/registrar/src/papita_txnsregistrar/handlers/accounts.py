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

from typing import Self

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

from .core import BaseLoadTableHandler


class AccountsTableHandler(BaseLoadTableHandler[AccountsService]):
    """
    Handler for loading and processing general account table data.

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


class AssetAccountsTableHandler(BaseLoadTableHandler[AssetAccountsService]):
    """
    Handler for loading and processing asset account table data.

    This specialized handler manages asset-related account data through the
    AssetAccountsService. It inherits the core functionality from the
    BaseLoadTableHandler and customizes it for asset account operations.

    Asset accounts typically represent investments, properties, or other resources
    that hold value. This handler provides the interface to load, process, and
    export such data.

    Attributes:
        Inherits all attributes from BaseLoadTableHandler, with AssetAccountsService
        as the parameterized service type.
    """


class LiabilityAccountsTableHandler(BaseLoadTableHandler[LiabilityAccountsService]):
    """
    Handler for loading and processing liability account table data.

    This specialized handler manages liability-related account data through the
    LiabilityAccountsService. It inherits the core functionality from the
    BaseLoadTableHandler and customizes it for liability account operations.

    Liability accounts represent debts, loans, or other financial obligations.
    This handler provides the interface to load, process, and export such data.

    Attributes:
        Inherits all attributes from BaseLoadTableHandler, with LiabilityAccountsService
        as the parameterized service type.
    """


class FinancedAssetAccountsTableHandler(
    BaseLoadTableHandler[FinancedAssetAccountsService, BankCreditLiabilityAccountsService, AssetAccountsService]
):
    """
    Handler for loading and processing financed asset account table data.

    This specialized handler manages accounts that represent assets acquired through
    financing, such as mortgaged properties or financed vehicles. It combines aspects
    of both asset accounts and liability accounts, requiring coordination between
    different services.

    The handler establishes dependencies with both AssetAccountsService and
    BankCreditLiabilityAccountsService to properly process the dual nature of
    financed assets.

    Attributes:
        Inherits attributes from BaseLoadTableHandler with FinancedAssetAccountsService
        as the parameterized service type, as well as from BankCreditLiabilityAccountsService
        and AssetAccountsService.

        dependencies: A dictionary mapping service names to service types, used for
                      resolving dependencies during processing.
    """

    @model_validator(mode="after")
    def _validate(self) -> Self:
        """
        Validates and sets up the dependencies for the FinancedAssetAccountsTableHandler.

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


class AccountsIndexerTableHandler(
    BaseLoadTableHandler[
        AccountsIndexerService,
        AccountsService,
        AssetAccountsService,
        LiabilityAccountsService,
        TypesService,
    ]
):
    """
    Handler for indexing and cross-referencing different types of account data.

    This comprehensive handler serves as a central point for indexing various account
    types, enabling cross-referencing and unified processing of different account
    categories. It combines functionality from multiple service types to provide
    a consolidated view of the account ecosystem.

    The handler establishes dependencies with a wide range of account-related services,
    including general accounts, assets, liabilities, and type classification services.
    This allows it to index and categorize accounts across the entire system.

    Attributes:
        Inherits attributes from BaseLoadTableHandler with AccountsIndexerService
        as the parameterized service type, as well as from AccountsService,
        AssetAccountsService, LiabilityAccountsService, and TypesService.

        dependencies: A dictionary mapping service names to service types, used for
                      resolving dependencies during the indexing process.
    """

    @model_validator(mode="after")
    def _validate(self) -> Self:
        """
        Validates and sets up the dependencies for the AccountsIndexerTableHandler.

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
