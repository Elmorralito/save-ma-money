"""Papita Transactions model services.

Services provide the business logic layer and work with the owner column via
UsersDTO. Use UsersService.get_owner(owner_id) to resolve an owner id to a
UsersDTO for passing as owner= to other services and handlers.
"""

from papita_txnsmodel.services.account_balances import AccountBalancesService
from papita_txnsmodel.services.account_details import (
    BankingAccountDetailsService,
    CreditCardAccountDetailsService,
    LoanAccountDetailsService,
    RealEstateAccountDetailsService,
    TradingAccountDetailsService,
)
from papita_txnsmodel.services.account_financing import AccountFinancingService
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.balance_reports import BalanceReportsService
from papita_txnsmodel.services.balance_views import refresh_balance_materialized_views
from papita_txnsmodel.services.categories import CategoriesService
from papita_txnsmodel.services.dues import UpcomingDueDTO
from papita_txnsmodel.services.ingestion import (
    IngestionBridgeService,
    IngestTransactionRequest,
    IngestTransactionResult,
)
from papita_txnsmodel.services.ingestion_status import (
    IngestionConnectionService,
    IngestionRunService,
    RecordIngestionRunRequest,
    UpsertIngestionConnectionRequest,
)
from papita_txnsmodel.services.owner_period_balances import OwnerPeriodBalancesService
from papita_txnsmodel.services.owner_yearly_balances import OwnerYearlyBalancesService
from papita_txnsmodel.services.reports import ReportService
from papita_txnsmodel.services.transactions import TransactionsService, TransactionTemplatesService
from papita_txnsmodel.services.users import UsersService

__all__ = [
    "AccountBalancesService",
    "BalanceReportsService",
    "AccountFinancingService",
    "AccountsService",
    "BankingAccountDetailsService",
    "CategoriesService",
    "CreditCardAccountDetailsService",
    "IngestTransactionRequest",
    "IngestTransactionResult",
    "IngestionBridgeService",
    "IngestionConnectionService",
    "IngestionRunService",
    "LoanAccountDetailsService",
    "RecordIngestionRunRequest",
    "UpsertIngestionConnectionRequest",
    "OwnerPeriodBalancesService",
    "OwnerYearlyBalancesService",
    "RealEstateAccountDetailsService",
    "ReportService",
    "TradingAccountDetailsService",
    "TransactionTemplatesService",
    "TransactionsService",
    "UpcomingDueDTO",
    "UsersService",
    "refresh_balance_materialized_views",
]
