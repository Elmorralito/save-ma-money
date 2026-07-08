"""Read-only repository for the account_balances materialized view."""

from __future__ import annotations

import uuid

import pandas as pd
from sqlalchemy import text
from sqlmodel import Session

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.model.contstants import ACCOUNT_BALANCES_VIEW, SCHEMA_NAME
from papita_txnsmodel.utils.classutils import MetaSingleton


class AccountBalancesRepository(metaclass=MetaSingleton):
    """Query tenant-scoped balances from the materialized view."""

    @SQLDatabaseConnector.connect
    def get_balances(
        self,
        *,
        owner: UsersDTO,
        _db_session: Session,
        account_id: uuid.UUID | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Return balance rows for an owner, optionally filtered by account."""
        if not isinstance(_db_session, Session):
            raise TypeError("Session not supported.")

        statement_sql = f"""
            SELECT owner_id, account_id, currency, balance, last_activity_ts
            FROM {SCHEMA_NAME}.{ACCOUNT_BALANCES_VIEW}
            WHERE owner_id = :owner_id
        """
        params: dict[str, object] = {"owner_id": owner.id}
        if account_id is not None:
            statement_sql += " AND account_id = :account_id"
            params["account_id"] = account_id

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
        """Refresh the account_balances materialized view after ledger changes."""
        if not isinstance(_db_session, Session):
            raise TypeError("Session not supported.")

        concurrent_clause = "CONCURRENTLY " if concurrently else ""
        statement = text(f"REFRESH MATERIALIZED VIEW {concurrent_clause}{SCHEMA_NAME}.{ACCOUNT_BALANCES_VIEW}")
        try:
            _db_session.exec(statement)
            _db_session.commit()
        except Exception:
            _db_session.rollback()
            raise
