"""Cover Redis cache BYPASS branches when ``owner.id`` is missing (Codecov patch)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
from fastapi import Response

from auth_helpers import make_user
from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.dependencies.pagination import PaginationParams
from papita_txnsapi.routers.v1 import accounts, categories, reports, transactions
from papita_txnsapi.schemas.query_params import (
    ReportCashFlowQuery,
    ReportSpendingQuery,
    ReportTrendsQuery,
    TransactionListQuery,
)
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.model.enums import TransactionKind, TransactionStatus


def _owner_without_id():
    owner = make_user()
    owner.id = None
    return owner


class TestCacheBypassOwnerNone:
    """``X-Cache: BYPASS`` when authenticated owner lacks a primary key."""

    def test_list_accounts_bypass(self) -> None:
        owner = _owner_without_id()
        response = Response()
        service = MagicMock()
        service.list_accounts.return_value = (pd.DataFrame([]), 0)
        service.balances_service = None
        accounts.list_accounts(
            owner,
            PaginationParams(skip=0, limit=20),
            service,
            get_settings(),
            None,
            response,
        )
        assert response.headers["X-Cache"] == "BYPASS"

    def test_list_categories_bypass(self) -> None:
        owner = _owner_without_id()
        response = Response()
        service = MagicMock()
        service.list_categories.return_value = (pd.DataFrame([]), 0)
        service.get_categories_for_parents.return_value = pd.DataFrame([])
        categories.list_categories(
            owner,
            PaginationParams(skip=0, limit=20),
            service,
            get_settings(),
            None,
            response,
        )
        assert response.headers["X-Cache"] == "BYPASS"

    def test_list_transactions_bypass(self) -> None:
        owner = _owner_without_id()
        response = Response()
        service = MagicMock()
        service.list_transactions.return_value = (pd.DataFrame([]), 0)
        transactions.list_transactions(
            owner,
            PaginationParams(skip=0, limit=20),
            service,
            TransactionListQuery(),
            get_settings(),
            None,
            response,
        )
        assert response.headers["X-Cache"] == "BYPASS"

    def test_get_transaction_bypass(self) -> None:
        owner = _owner_without_id()
        response = Response()
        now = datetime.now(timezone.utc)
        txn = TransactionsDTO(
            id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            transaction_kind=TransactionKind.EXPENSE,
            amount=1.0,
            currency="USD",
            transaction_ts=now,
            from_account_id=uuid.uuid4(),
            category_id=uuid.uuid4(),
            status=TransactionStatus.COMPLETED,
            description="x",
            created_at=now,
            updated_at=now,
        )
        service = MagicMock()
        service.get.return_value = txn
        transactions.get_transaction(
            txn.id,
            owner,
            service,
            get_settings(),
            None,
            response,
        )
        assert response.headers["X-Cache"] == "BYPASS"

    def test_reports_bypass(self) -> None:
        owner = _owner_without_id()
        settings = get_settings()
        spending_service = MagicMock()
        spending_service.spending.return_value = {
            "group_by": "category",
            "expenses": [],
            "expense_total": 0.0,
            "income_total": 0.0,
        }
        cash_service = MagicMock()
        cash_service.cash_flow.return_value = {
            "inflows": 0.0,
            "outflows": 0.0,
            "net": 0.0,
            "portfolio_total": 0.0,
        }
        trends_service = MagicMock()
        trends_service.trends.return_value = {"period": "month", "series": []}

        for fn, service, filters in (
            (
                reports.get_spending_report,
                spending_service,
                ReportSpendingQuery(start_date=date(2026, 1, 1), end_date=date(2026, 1, 31)),
            ),
            (
                reports.get_cash_flow_report,
                cash_service,
                ReportCashFlowQuery(start_date=date(2026, 1, 1), end_date=date(2026, 1, 31)),
            ),
            (
                reports.get_trends_report,
                trends_service,
                ReportTrendsQuery(months=3),
            ),
        ):
            response = Response()
            fn(owner, service, filters, settings, None, response)
            assert response.headers["X-Cache"] == "BYPASS"
