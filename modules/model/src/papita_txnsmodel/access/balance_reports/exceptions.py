"""Exceptions for balance report read operations."""

from __future__ import annotations

from papita_txnsmodel.config.constants import BALANCE_REPORT_FILTERS_CONFIG

__all__ = ["BALANCE_REPORT_FILTERS_CONFIG", "UnregisteredBalanceReportError"]


class UnregisteredBalanceReportError(ValueError):
    """Raised when a balance report view is not registered in the YAML config.

    Balance report materialized views can only be queried when their ``report_id``
    is defined under ``reports`` in ``balance_report_filters.yaml``.
    """

    def __init__(self, report_id: str, *, known_reports: list[str] | None = None) -> None:
        """Initialize with the rejected report id and optional known report ids."""
        known = ", ".join(known_reports or [])
        message = (
            f"Balance report '{report_id}' is not registered in "
            f"{BALANCE_REPORT_FILTERS_CONFIG} and cannot be executed."
        )
        if known:
            message = f"{message} Known reports: {known}"

        super().__init__(message)
        self.report_id = report_id
        self.known_reports = known_reports or []
