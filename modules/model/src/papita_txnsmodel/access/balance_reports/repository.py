"""Unified read-only repository for balance report materialized views."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlmodel import Session

from papita_txnsmodel.access.balance_reports.query_sql import build_balance_report_query_sql
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.config.balance_report_specs import resolve_report_view
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.classutils import MetaSingleton


class BalanceReportsRepository(metaclass=MetaSingleton):
    """Query tenant-scoped balance reports from materialized views."""

    def query(
        self,
        *,
        report_id: str,
        owner: UsersDTO,
        filters: dict[str, object] | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Return rows for a balance report, scoped to an owner.

        Raises:
            UnregisteredBalanceReportError: If ``report_id`` is absent from
                ``config/data/balance_report_filters.yaml``.
        """
        if owner is None:
            raise ValueError("owner=UsersDTO is required for balance report queries.")

        view_name = resolve_report_view(report_id)
        return self._execute_query(
            report_id=report_id,
            view_name=view_name,
            owner=owner,
            filters=filters,
            **kwargs,
        )

    @SQLDatabaseConnector.connect
    def _execute_query(
        self,
        *,
        report_id: str,
        view_name: str,
        owner: UsersDTO,
        filters: dict[str, object] | None = None,
        _db_session: Session,
        **kwargs,
    ) -> pd.DataFrame:
        """Run the SQL query after registry validation and session acquisition."""
        if not isinstance(_db_session, Session):
            raise TypeError("Session not supported.")

        if owner.id is None:
            raise ValueError("owner.id is required for balance report queries.")

        statement_sql, params = build_balance_report_query_sql(
            view_name=view_name,
            report_id=report_id,
            owner_id=owner.id,
            filters=filters,
        )
        statement = text(statement_sql)
        try:
            rows = _db_session.exec(statement, params=params).all()
            return pd.DataFrame(rows)
        except Exception:
            return pd.DataFrame([])
