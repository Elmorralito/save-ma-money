"""Read-only handler for balance report queries and export."""

from __future__ import annotations

from typing import Any, Tuple

import pandas as pd

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.handlers.abstract import AbstractHandler
from papita_txnsmodel.services.balance_reports import BalanceReportsService


class BalanceReportsHandler(AbstractHandler[BalanceReportsService]):
    """Handler for listing balance reports and fetching tenant-scoped report data."""

    service: BalanceReportsService

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        """Registry labels for balance report read operations."""
        return "balance_reports", "balance_report", "reports"

    def list_reports(self) -> list[str]:
        """Return available balance report identifiers."""
        return self.service.list_reports()

    def get_filter_config(self, report_id: str) -> dict[str, Any]:
        """Return YAML filter configuration for a single report."""
        return self.service.get_report_filter_spec(report_id)

    def fetch_report(
        self,
        *,
        report_id: str,
        owner: UsersDTO,
        filters: dict[str, Any] | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Fetch report rows for a tenant owner with optional validated filters."""
        return self.service.get_report_data(
            report_id=report_id,
            owner=owner,
            filters=filters,
            **kwargs,
        )

    def load(self, *, data: pd.DataFrame | list[TableDTO] | list[dict] | TableDTO, **kwargs) -> "BalanceReportsHandler":
        """Balance reports are read-only; loading is not supported."""
        raise NotImplementedError("Balance reports are read-only; use fetch_report() instead.")

    def dump(
        self,
        *,
        report_id: str | None = None,
        owner: UsersDTO | None = None,
        filters: dict[str, Any] | None = None,
        **kwargs,
    ) -> "BalanceReportsHandler":
        """Export a balance report into _loaded_data for downstream consumers."""
        if report_id is None:
            raise ValueError("report_id is required for balance report dump.")
        if owner is None:
            raise ValueError("owner=UsersDTO is required for balance report dump.")

        self._loaded_data = self.fetch_report(report_id=report_id, owner=owner, filters=filters, **kwargs)
        return self
