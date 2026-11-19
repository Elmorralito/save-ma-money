"""Refresh helpers for balance-related materialized views."""

from __future__ import annotations

import logging
from typing import Any

from papita_txnsmodel.database.session import get_session_manager
from papita_txnsmodel.services.account_balances import AccountBalancesService
from papita_txnsmodel.services.owner_period_balances import OwnerPeriodBalancesService
from papita_txnsmodel.services.owner_yearly_balances import OwnerYearlyBalancesService

logger = logging.getLogger(__name__)


def refresh_balance_materialized_views(
    connector: Any = None,
    *,
    concurrently: bool = False,
) -> None:
    """Refresh all ledger-derived balance materialized views after transaction changes."""
    resolved = connector if connector is not None else get_session_manager()
    try:
        AccountBalancesService.model_validate({"connector": resolved}).refresh(concurrently=concurrently)
        OwnerYearlyBalancesService.model_validate({"connector": resolved}).refresh(concurrently=concurrently)
        OwnerPeriodBalancesService.model_validate({"connector": resolved}).refresh(concurrently=concurrently)
    except Exception:
        logger.exception("Failed to refresh balance materialized views.")
        raise
