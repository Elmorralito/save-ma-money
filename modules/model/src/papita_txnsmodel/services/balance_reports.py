"""Generic read-only service for balance report materialized views."""

from __future__ import annotations

from typing import Any, Type

import pandas as pd
from pydantic import BaseModel, ConfigDict, model_validator

from papita_txnsmodel.access.balance_reports.filter_validation import validate_report_filters
from papita_txnsmodel.access.balance_reports.repository import BalanceReportsRepository
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.config.balance_report_specs import get_report_spec, list_report_ids
from papita_txnsmodel.database.connector import SQLDatabaseConnector


class BalanceReportsService(BaseModel):
    """List, describe, and query balance reports from YAML-driven filter specs."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    connector: Type[SQLDatabaseConnector] = SQLDatabaseConnector
    repository_type: type[BalanceReportsRepository] = BalanceReportsRepository

    _repository: BalanceReportsRepository | None = None

    @model_validator(mode="after")
    def _validate(self) -> "BalanceReportsService":
        """Initialize repository."""
        self._repository = self.repository_type()
        return self

    def close(self) -> None:
        """Close the database connection."""
        self.connector.close()

    def list_reports(self) -> list[str]:
        """Return report identifiers from the YAML registry."""
        return list_report_ids()

    def get_report_filter_spec(self, report_id: str) -> dict[str, Any]:
        """Return the YAML filter specification for a single report."""
        return get_report_spec(report_id)

    def get_report_data(
        self,
        *,
        report_id: str,
        owner: UsersDTO,
        filters: dict[str, Any] | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Query a balance report with validated filters for a tenant owner.

        Raises:
            UnregisteredBalanceReportError: If ``report_id`` is not listed in
                ``config/data/balance_report_filters.yaml``.
        """
        if owner is None:
            raise ValueError("owner=UsersDTO is required for balance report queries.")

        validated_filters = validate_report_filters(report_id, filters)
        return self._repository.query(
            report_id=report_id,
            owner=owner,
            filters=validated_filters,
            **kwargs,
        )
