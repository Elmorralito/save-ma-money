# pylint: disable=access-member-before-definition
# mypy: disable-error-code="has-type"
"""
Account extension and financing handler modules.

Dedicated handlers ingest 1:1 account detail tables and asset–loan financing links.
Use alongside AccountsTableHandler for consolidated account rows.
"""

import inspect
from typing import Self, Tuple

from pydantic import model_validator

from papita_txnsmodel.services.account_details import (
    BankingAccountDetailsService,
    CreditCardAccountDetailsService,
    LoanAccountDetailsService,
    RealEstateAccountDetailsService,
    TradingAccountDetailsService,
)
from papita_txnsmodel.services.account_financing import AccountFinancingService
from papita_txnsmodel.services.accounts import AccountsService

from .base import BaseTableHandler


def _wire_account_dependencies(handler: BaseTableHandler, dependency_fields: Tuple[str, ...]) -> Self:
    """Instantiate AccountsService dependencies for the given DTO fields."""
    if not handler.dependencies:
        handler.dependencies = {field: AccountsService for field in dependency_fields}

    connector = handler.service.connector
    handler.dependencies = {
        name: (service.model_validate({"connector": connector}) if inspect.isclass(service) else service)
        for name, service in handler.dependencies.items()
    }
    return handler


class BankingAccountDetailsTableHandler(BaseTableHandler[BankingAccountDetailsService, AccountsService]):
    """Handler for banking account extension ingest."""

    @model_validator(mode="after")
    def _validate(self) -> Self:
        """Wire account_id dependency to AccountsService."""
        return _wire_account_dependencies(self, ("account_id",))

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        """Get handler labels."""
        return "banking_account_details", "banking_account_details_table"


class RealEstateAccountDetailsTableHandler(BaseTableHandler[RealEstateAccountDetailsService, AccountsService]):
    """Handler for real-estate account extension ingest."""

    @model_validator(mode="after")
    def _validate(self) -> Self:
        """Wire account_id dependency to AccountsService."""
        return _wire_account_dependencies(self, ("account_id",))

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        """Get handler labels."""
        return "real_estate_account_details", "real_estate_account_details_table"


class TradingAccountDetailsTableHandler(BaseTableHandler[TradingAccountDetailsService, AccountsService]):
    """Handler for trading account extension ingest."""

    @model_validator(mode="after")
    def _validate(self) -> Self:
        """Wire account_id dependency to AccountsService."""
        return _wire_account_dependencies(self, ("account_id",))

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        """Get handler labels."""
        return "trading_account_details", "trading_account_details_table"


class CreditCardAccountDetailsTableHandler(BaseTableHandler[CreditCardAccountDetailsService, AccountsService]):
    """Handler for credit-card account extension ingest."""

    @model_validator(mode="after")
    def _validate(self) -> Self:
        """Wire account_id dependency to AccountsService."""
        return _wire_account_dependencies(self, ("account_id",))

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        """Get handler labels."""
        return "credit_card_account_details", "credit_card_account_details_table"


class LoanAccountDetailsTableHandler(BaseTableHandler[LoanAccountDetailsService, AccountsService]):
    """Handler for loan account extension ingest."""

    @model_validator(mode="after")
    def _validate(self) -> Self:
        """Wire account_id dependency to AccountsService."""
        return _wire_account_dependencies(self, ("account_id",))

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        """Get handler labels."""
        return "loan_account_details", "loan_account_details_table"


class AccountFinancingTableHandler(BaseTableHandler[AccountFinancingService, AccountsService]):
    """Handler for asset–loan financing relationship ingest."""

    @model_validator(mode="after")
    def _validate(self) -> Self:
        """Wire asset and loan account dependencies."""
        return _wire_account_dependencies(self, ("asset_account_id", "loan_account_id"))

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        """Get handler labels."""
        return "account_financing", "account_financing_table"
