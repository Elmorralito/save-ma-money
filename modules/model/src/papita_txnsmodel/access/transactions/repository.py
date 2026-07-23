"""Transactions repository module for the Papita Transactions system.

This module defines the repository classes for transaction entities in the system.
It provides database access operations specific to transactions, extending the base
repository functionality with transaction-specific implementations.

Classes:
    TransactionTemplatesRepository: Repository for planned or recurring template operations.
    TransactionsRepository: Repository for posted financial transaction operations.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime
from typing import Any, Literal

from sqlalchemy import case, func
from sqlmodel import Session, select

from papita_txnsmodel.access.base.repository import OwnedTableRepository
from papita_txnsmodel.access.transactions.query_filters import TransactionListFilterSpec, build_transaction_list_filters
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.model.enums import TransactionKind, TransactionStatus
from papita_txnsmodel.model.transactions import Transactions
from papita_txnsmodel.utils.classutils import MetaSingleton

from .dto import TransactionsDTO, TransactionTemplatesDTO

logger = logging.getLogger(__name__)


class TransactionTemplatesRepository(OwnedTableRepository, metaclass=MetaSingleton):
    """Repository for transaction template database operations.

    This class extends OwnedTableRepository to provide operations specific to
    transaction templates. It uses the Singleton pattern via MetaSingleton to ensure
    only one instance exists throughout the application.

    Attributes:
        __expected_dto__ (type[TransactionTemplatesDTO]): The expected DTO type for this
            repository, set to TransactionTemplatesDTO.
    """

    __expected_dto__ = TransactionTemplatesDTO


class TransactionsRepository(OwnedTableRepository, metaclass=MetaSingleton):
    """Repository for posted financial transaction database operations.

    This class extends OwnedTableRepository to provide operations specific to posted
    transactions. It uses the Singleton pattern via MetaSingleton to ensure only one
    instance exists throughout the application.

    Attributes:
        __expected_dto__ (type[TransactionsDTO]): The expected DTO type for this
            repository, set to TransactionsDTO.
    """

    __expected_dto__ = TransactionsDTO

    @SQLDatabaseConnector.connect
    def aggregate_spending(  # pylint: disable=too-many-locals,assignment-from-no-return
        self,
        *,
        owner: UsersDTO,
        _db_session: Session,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        account_id: uuid.UUID | None = None,
        group_by: Literal["category", "account"] = "category",
        **kwargs,
    ) -> dict[str, Any]:
        """Aggregate completed expense groups and income/expense totals in SQL.

        Args:
            owner: Tenant owner whose ledger is aggregated.
            _db_session: Database session (injected by connector).
            start_date: Optional inclusive window start.
            end_date: Optional inclusive window end.
            account_id: Optional account leg filter (from or to).
            group_by: Expense breakdown dimension (``category`` or ``account``).
            **kwargs: Unused; accepted for call compatibility.

        Returns:
            Dict with ``group_by``, ``expenses`` rows, ``expense_total``, and
            ``income_total`` matching ``ReportService.spending`` shape.

        Raises:
            TypeError: If ``_db_session`` is not a SQLModel ``Session``.
            ValueError: If ``owner`` is missing.
        """
        del kwargs
        if not isinstance(_db_session, Session):
            raise TypeError("Session not supported.")
        if not isinstance(owner, UsersDTO) or owner.id is None:
            raise ValueError("Owner is required for aggregate_spending")

        group_column_name = "category_id" if group_by == "category" else "from_account_id"
        group_column = getattr(Transactions, group_column_name)

        base_filters = list(
            build_transaction_list_filters(
                TransactionListFilterSpec(
                    status=TransactionStatus.COMPLETED,
                    account_id=account_id,
                    start_date=start_date,
                    end_date=end_date,
                )
            )
        )
        base_filters.extend(self._soft_delete_read_filters(Transactions, include_deleted=False))
        base_filters.append(self._get_owner_filter(owner, Transactions))

        expense_total_expr = func.coalesce(
            func.sum(
                case(
                    (Transactions.transaction_kind == TransactionKind.EXPENSE, Transactions.amount),
                    else_=0,
                )
            ),
            0,
        )
        income_total_expr = func.coalesce(
            func.sum(
                case(
                    (Transactions.transaction_kind == TransactionKind.INCOME, Transactions.amount),
                    else_=0,
                )
            ),
            0,
        )
        totals_statement = select(expense_total_expr, income_total_expr).where(*base_filters)

        expense_filters = [
            *base_filters,
            Transactions.transaction_kind == TransactionKind.EXPENSE,
        ]
        grouped_statement = (
            select(
                group_column.label(group_column_name), func.coalesce(func.sum(Transactions.amount), 0).label("total")
            )
            .where(*expense_filters)
            .group_by(group_column)
        )

        try:
            expense_total, income_total = _db_session.exec(totals_statement).one()
            grouped_rows = list(_db_session.exec(grouped_statement).all())
        except Exception as exc:
            logger.exception("Spending aggregation query failed due to: %s", exc)
            return {
                "group_by": group_by,
                "expenses": [],
                "expense_total": 0.0,
                "income_total": 0.0,
            }

        expenses = [{group_column_name: row[0], "total": float(row[1])} for row in grouped_rows]
        return {
            "group_by": group_by,
            "expenses": expenses,
            "expense_total": float(expense_total or 0.0),
            "income_total": float(income_total or 0.0),
        }
