"""Read-only repository for the owner_yearly_balances materialized view."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlmodel import Session

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.model.contstants import OWNER_YEARLY_BALANCES_VIEW, SCHEMA_NAME
from papita_txnsmodel.utils.classutils import MetaSingleton


class OwnerYearlyBalancesRepository(metaclass=MetaSingleton):
    """Query combined yearly balances for a tenant owner."""

    @SQLDatabaseConnector.connect
    def get_yearly_balances(
        self,
        *,
        owner: UsersDTO,
        _db_session: Session,
        balance_year: int | None = None,
        currency: str | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Return yearly combined balance rows for an owner."""
        if not isinstance(_db_session, Session):
            raise TypeError("Session not supported.")

        statement_sql = f"""
            SELECT owner_id, balance_year, currency, yearly_net_change, total_balance
            FROM {SCHEMA_NAME}.{OWNER_YEARLY_BALANCES_VIEW}
            WHERE owner_id = :owner_id
        """
        params: dict[str, object] = {"owner_id": owner.id}
        if balance_year is not None:
            statement_sql += " AND balance_year = :balance_year"
            params["balance_year"] = balance_year
        if currency is not None:
            statement_sql += " AND currency = :currency"
            params["currency"] = currency

        statement_sql += " ORDER BY balance_year DESC, currency"

        statement = text(statement_sql)
        try:
            rows = _db_session.exec(statement, params=params).all()
            return pd.DataFrame(rows)
        except Exception:
            return pd.DataFrame([])

    @SQLDatabaseConnector.connect
    def refresh_materialized_view(
        self,
        *,
        _db_session: Session,
        concurrently: bool = False,
        **kwargs,
    ) -> None:
        """Refresh the owner_yearly_balances materialized view after ledger changes."""
        if not isinstance(_db_session, Session):
            raise TypeError("Session not supported.")

        concurrent_clause = "CONCURRENTLY " if concurrently else ""
        statement = text(f"REFRESH MATERIALIZED VIEW {concurrent_clause}{SCHEMA_NAME}.{OWNER_YEARLY_BALANCES_VIEW}")
        try:
            _db_session.exec(statement)
            _db_session.commit()
        except Exception:
            _db_session.rollback()
            raise
