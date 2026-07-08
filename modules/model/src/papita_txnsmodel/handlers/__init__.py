"""Concrete table handlers for HandlerFactory discovery.

Import all handler modules so ``HandlerFactory.load("papita_txnsmodel.handlers")``
registers v3 ingest pipelines without per-module load calls.
"""

from papita_txnsmodel.handlers.account_extensions import (
    AccountFinancingTableHandler,
    BankingAccountDetailsTableHandler,
    CreditCardAccountDetailsTableHandler,
    LoanAccountDetailsTableHandler,
    RealEstateAccountDetailsTableHandler,
    TradingAccountDetailsTableHandler,
)
from papita_txnsmodel.handlers.accounts import AccountsTableHandler
from papita_txnsmodel.handlers.balance_reports import BalanceReportsHandler
from papita_txnsmodel.handlers.categories import CategoriesTableHandler
from papita_txnsmodel.handlers.transactions import (
    IdentifiedTransactionsTableHandler,
    TransactionsHandler,
    TransactionTemplatesTableHandler,
)
from papita_txnsmodel.handlers.users import UsersTableHandler

__all__ = [
    "AccountFinancingTableHandler",
    "AccountsTableHandler",
    "BalanceReportsHandler",
    "BankingAccountDetailsTableHandler",
    "CategoriesTableHandler",
    "CreditCardAccountDetailsTableHandler",
    "IdentifiedTransactionsTableHandler",
    "LoanAccountDetailsTableHandler",
    "RealEstateAccountDetailsTableHandler",
    "TradingAccountDetailsTableHandler",
    "TransactionTemplatesTableHandler",
    "TransactionsHandler",
    "UsersTableHandler",
]
