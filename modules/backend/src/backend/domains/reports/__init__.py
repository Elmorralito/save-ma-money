"""Reports vertical slice (MV reads, aggregations, schemas, router)."""

from papita_txnsapi.routers.v1.reports import router
from papita_txnsapi.schemas.reports import (
    CashFlowReportResponse,
    DebtPaydownReportResponse,
    DebtPaydownSimulationRequest,
    DebtPaydownSimulationResponse,
    OperatingCashflowReportResponse,
    PlannedVsActualReportResponse,
    SpendingReportResponse,
    TrendsReportResponse,
)
from papita_txnsmodel.services.account_balances import AccountBalancesService
from papita_txnsmodel.services.owner_period_balances import OwnerPeriodBalancesService
from papita_txnsmodel.services.owner_yearly_balances import OwnerYearlyBalancesService
from papita_txnsmodel.services.reports import ReportService

__all__ = [
    "AccountBalancesService",
    "CashFlowReportResponse",
    "DebtPaydownReportResponse",
    "DebtPaydownSimulationRequest",
    "DebtPaydownSimulationResponse",
    "OperatingCashflowReportResponse",
    "OwnerPeriodBalancesService",
    "OwnerYearlyBalancesService",
    "PlannedVsActualReportResponse",
    "ReportService",
    "SpendingReportResponse",
    "TrendsReportResponse",
    "router",
]
