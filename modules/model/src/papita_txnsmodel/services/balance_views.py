"""Refresh helpers for balance-related materialized views."""

from __future__ import annotations

import logging
from typing import Type

from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.services.account_balances import AccountBalancesService
from papita_txnsmodel.services.owner_period_balances import OwnerPeriodBalancesService
from papita_txnsmodel.services.owner_yearly_balances import OwnerYearlyBalancesService

logger = logging.getLogger(__name__)


def refresh_balance_materialized_views(
    connector: Type[SQLDatabaseConnector],
    *,
    concurrently: bool = False,
) -> None:
    """Refresh all ledger-derived balance materialized views after transaction changes."""
    try:
        AccountBalancesService.model_validate({"connector": connector}).refresh(concurrently=concurrently)
        OwnerYearlyBalancesService.model_validate({"connector": connector}).refresh(concurrently=concurrently)
        OwnerPeriodBalancesService.model_validate({"connector": connector}).refresh(concurrently=concurrently)
    except Exception:
        logger.exception("Failed to refresh balance materialized views.")
        raise
