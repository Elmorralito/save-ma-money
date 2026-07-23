"""Read-only repository for the account_balances materialized view."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import pandas as pd
from sqlmodel import Session, select

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.model.account_balances import AccountBalances
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
        account_ids: Sequence[uuid.UUID] | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Return balance rows for an owner, optionally filtered by account(s).

        Args:
            owner: Tenant owner whose balances are queried.
            _db_session: Database session (injected by connector).
            account_id: Optional single account filter.
            account_ids: Optional page-scoped account ID filter (``IN``). When an
                empty sequence is provided, returns an empty DataFrame without
                querying. Mutually exclusive with ``account_id``.
            **kwargs: Unused; accepted for decorator/call compatibility.

        Returns:
            DataFrame of balance rows, or empty on no match / query failure.

        Raises:
            TypeError: If ``_db_session`` is not a SQLModel ``Session``.
            ValueError: If both ``account_id`` and ``account_ids`` are provided.
        """
        if not isinstance(_db_session, Session):
            raise TypeError("Session not supported.")
        if account_id is not None and account_ids is not None:
            raise ValueError("Provide account_id or account_ids, not both.")

        statement = select(AccountBalances).where(AccountBalances.owner_id == owner.id)
        if account_ids is not None:
            ids = list(account_ids)
            if not ids:
                return pd.DataFrame([])
            statement = statement.where(AccountBalances.account_id.in_(ids))
        elif account_id is not None:
            statement = statement.where(AccountBalances.account_id == account_id)

        try:
            rows = _db_session.exec(statement).all()
            if not rows:
                return pd.DataFrame([])
            return pd.DataFrame([row.model_dump(mode="python") for row in rows])
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

        from sqlalchemy import text

        from papita_txnsmodel.model.contstants import ACCOUNT_BALANCES_VIEW, SCHEMA_NAME

        concurrent_clause = "CONCURRENTLY " if concurrently else ""
        statement = text(f"REFRESH MATERIALIZED VIEW {concurrent_clause}{SCHEMA_NAME}.{ACCOUNT_BALANCES_VIEW}")
        try:
            _db_session.exec(statement)
            _db_session.commit()
        except Exception:
            _db_session.rollback()
            raise
