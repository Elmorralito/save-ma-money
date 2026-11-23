"""Idempotent IBKR Activity Statement import facade (PPT-101 / #262).

Delegates persistence to provider-agnostic ``PortfolioImportService`` while
keeping ``papita_txnsmodel`` free of top-level ``papita_ingestor_*`` imports.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.account_details import TradingAccountDetailsService
from papita_txnsmodel.services.account_financing import AccountFinancingService
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.ingestion import IngestionBridgeService
from papita_txnsmodel.services.portfolio_import import (
    NormalizedPortfolioBatch,
    PortfolioImportResult,
    PortfolioImportService,
    PortfolioPositionImportItem,
)

IBKRPositionImportItem = PortfolioPositionImportItem
IBKRImportResult = PortfolioImportResult
StatementParserFn = Callable[[str], NormalizedPortfolioBatch]


def _default_ibkr_statement_parser(csv_text: str) -> NormalizedPortfolioBatch:
    """Resolve the registered ``ibkr-activity-csv`` importer lazily."""
    from papita_ingestor_core.registry import get_default_registry  # pylint: disable=import-outside-toplevel

    importer = get_default_registry().get_importer("ibkr-activity-csv")
    return importer.parse_statement(csv_text)


class IBKRImportService(PortfolioImportService):
    """Backward-compatible IBKR facade over ``PortfolioImportService``."""

    def __init__(
        self,
        *,
        accounts_service: AccountsService,
        trading_details_service: TradingAccountDetailsService,
        financing_service: AccountFinancingService,
        bridge_service: IngestionBridgeService,
        statement_parser: StatementParserFn | None = None,
    ) -> None:
        super().__init__(
            accounts_service=accounts_service,
            trading_details_service=trading_details_service,
            financing_service=financing_service,
            bridge_service=bridge_service,
        )
        self._statement_parser = statement_parser or _default_ibkr_statement_parser

    def import_activity_statement(  # pylint: disable=too-many-arguments
        self,
        *,
        owner: UsersDTO,
        csv_text: str,
        fx_rate: float = 1.0,
        base_currency: str = "COP",
        cash_account_id: uuid.UUID | None = None,
        margin_account_id: uuid.UUID | None = None,
        source_account_id: uuid.UUID | None = None,
        create_missing_accounts: bool = True,
    ) -> IBKRImportResult:
        """Parse via the registered importer plugin and apply idempotently."""
        batch = self._statement_parser(csv_text)
        return self.import_batch(
            owner=owner,
            batch=batch,
            fx_rate=fx_rate,
            base_currency=base_currency,
            cash_account_id=cash_account_id,
            margin_account_id=margin_account_id,
            source_account_id=source_account_id,
            create_missing_accounts=create_missing_accounts,
        )


__all__ = ["IBKRImportResult", "IBKRImportService", "IBKRPositionImportItem"]
