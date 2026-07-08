"""Read-only repository for owner monthly/quarterly/biannual balance materialized views."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlmodel import Session

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.model.contstants import (
    OWNER_BIANNUAL_BALANCES_VIEW,
    OWNER_MONTHLY_BALANCES_VIEW,
    OWNER_QUARTERLY_BALANCES_VIEW,
    SCHEMA_NAME,
)
from papita_txnsmodel.utils.classutils import MetaSingleton

_PERIOD_VIEWS = (
    OWNER_MONTHLY_BALANCES_VIEW,
    OWNER_QUARTERLY_BALANCES_VIEW,
    OWNER_BIANNUAL_BALANCES_VIEW,
)


class OwnerPeriodBalancesRepository(metaclass=MetaSingleton):
    """Query combined period balances for a tenant owner."""

    @SQLDatabaseConnector.connect
    def get_monthly_balances(
        self,
        *,
        owner: UsersDTO,
        _db_session: Session,
        balance_year: int | None = None,
        balance_month: int | None = None,
        currency: str | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Return monthly combined balance rows for an owner."""
        return self._query_period_balances(
            _db_session=_db_session,
            view_name=OWNER_MONTHLY_BALANCES_VIEW,
            owner=owner,
            balance_year=balance_year,
            period_column="balance_month",
            period_value=balance_month,
            currency=currency,
            order_by="balance_year DESC, balance_month DESC, currency",
        )

    @SQLDatabaseConnector.connect
    def get_quarterly_balances(
        self,
        *,
        owner: UsersDTO,
        _db_session: Session,
        balance_year: int | None = None,
        balance_quarter: int | None = None,
        currency: str | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Return quarterly combined balance rows for an owner."""
        return self._query_period_balances(
            _db_session=_db_session,
            view_name=OWNER_QUARTERLY_BALANCES_VIEW,
            owner=owner,
            balance_year=balance_year,
            period_column="balance_quarter",
            period_value=balance_quarter,
            currency=currency,
            order_by="balance_year DESC, balance_quarter DESC, currency",
        )

    @SQLDatabaseConnector.connect
    def get_biannual_balances(
        self,
        *,
        owner: UsersDTO,
        _db_session: Session,
        balance_year: int | None = None,
        balance_half: int | None = None,
        currency: str | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Return biannual combined balance rows for an owner."""
        return self._query_period_balances(
            _db_session=_db_session,
            view_name=OWNER_BIANNUAL_BALANCES_VIEW,
            owner=owner,
            balance_year=balance_year,
            period_column="balance_half",
            period_value=balance_half,
            currency=currency,
            order_by="balance_year DESC, balance_half DESC, currency",
        )

    @SQLDatabaseConnector.connect
    def refresh_materialized_views(
        self,
        *,
        _db_session: Session,
        concurrently: bool = False,
        **kwargs,
    ) -> None:
        """Refresh monthly, quarterly, and biannual owner balance materialized views."""
        if not isinstance(_db_session, Session):
            raise TypeError("Session not supported.")

        concurrent_clause = "CONCURRENTLY " if concurrently else ""
        try:
            for view_name in _PERIOD_VIEWS:
                statement = text(f"REFRESH MATERIALIZED VIEW {concurrent_clause}{SCHEMA_NAME}.{view_name}")
                _db_session.exec(statement)
            _db_session.commit()
        except Exception:
            _db_session.rollback()
            raise

    def _query_period_balances(
        self,
        *,
        _db_session: Session,
        view_name: str,
        owner: UsersDTO,
        balance_year: int | None,
        period_column: str,
        period_value: int | None,
        currency: str | None,
        order_by: str,
    ) -> pd.DataFrame:
        """Run a filtered SELECT against a period balance materialized view."""
        if not isinstance(_db_session, Session):
            raise TypeError("Session not supported.")

        statement_sql = f"SELECT * FROM {SCHEMA_NAME}.{view_name} WHERE owner_id = :owner_id"
        params: dict[str, object] = {"owner_id": owner.id}
        if balance_year is not None:
            statement_sql += " AND balance_year = :balance_year"
            params["balance_year"] = balance_year
        if period_value is not None:
            statement_sql += f" AND {period_column} = :period_value"
            params["period_value"] = period_value
        if currency is not None:
            statement_sql += " AND currency = :currency"
            params["currency"] = currency

        statement_sql += f" ORDER BY {order_by}"
        statement = text(statement_sql)
        try:
            rows = _db_session.exec(statement, params=params).all()
            return pd.DataFrame(rows)
        except Exception:
            return pd.DataFrame([])
