"""Transaction analytics read models for API report endpoints (FR-12)."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any, Literal, Type

import pandas as pd
from pydantic import BaseModel, ConfigDict, model_validator

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.model.enums import TransactionKind, TransactionStatus
from papita_txnsmodel.services.account_balances import AccountBalancesService
from papita_txnsmodel.services.balance_views import refresh_balance_materialized_views
from papita_txnsmodel.services.transactions import TransactionsService


class ReportService(BaseModel):
    """Service-layer aggregations backing ``/reports/*`` MVP endpoints."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    connector: Type[SQLDatabaseConnector] = SQLDatabaseConnector
    transactions_service: TransactionsService | None = None
    account_balances_service: AccountBalancesService | None = None

    @model_validator(mode="after")
    def _wire_dependencies(self) -> "ReportService":
        """Instantiate dependent services from the shared connector when omitted."""
        if not isinstance(self.transactions_service, TransactionsService):
            self.transactions_service = TransactionsService.model_validate({"connector": self.connector})
        if not isinstance(self.account_balances_service, AccountBalancesService):
            self.account_balances_service = AccountBalancesService.model_validate({"connector": self.connector})
        return self

    def close(self) -> None:
        """Close the database connection."""
        self.connector.close()

    def _load_transactions(self, *, owner: UsersDTO, **kwargs) -> pd.DataFrame:
        """Load all tenant transactions for in-memory report filtering."""
        if self.transactions_service is None:
            raise RuntimeError("transactions_service is not configured.")
        return self.transactions_service.get_records(dto=None, owner=owner, **kwargs)

    @staticmethod
    def _apply_date_window(
        frame: pd.DataFrame,
        *,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> pd.DataFrame:
        """Filter a transaction frame to an inclusive ``transaction_ts`` window."""
        if frame.empty:
            return frame
        if start_date is not None:
            frame = frame[frame["transaction_ts"] >= start_date]
        if end_date is not None:
            frame = frame[frame["transaction_ts"] <= end_date]
        return frame

    def spending(
        self,
        *,
        owner: UsersDTO,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        group_by: Literal["category", "account"] = "category",
        **kwargs,
    ) -> dict[str, Any]:
        """Spending breakdown for completed expenses plus separate income totals."""
        frame = self._apply_date_window(
            self._load_transactions(owner=owner, **kwargs), start_date=start_date, end_date=end_date
        )
        if frame.empty:
            return {"expenses": [], "income_total": 0.0, "expense_total": 0.0}

        completed = frame[frame["status"] == TransactionStatus.COMPLETED.value]
        expenses = completed[completed["transaction_kind"] == TransactionKind.EXPENSE.value]
        income = completed[completed["transaction_kind"] == TransactionKind.INCOME.value]

        group_column = "category_id" if group_by == "category" else "from_account_id"
        grouped = (
            expenses.groupby(group_column, dropna=False)["amount"]
            .sum()
            .reset_index()
            .rename(columns={"amount": "total"})
            .to_dict(orient="records")
            if not expenses.empty
            else []
        )

        return {
            "group_by": group_by,
            "expenses": grouped,
            "expense_total": float(expenses["amount"].sum()) if not expenses.empty else 0.0,
            "income_total": float(income["amount"].sum()) if not income.empty else 0.0,
        }

    def cash_flow(
        self,
        *,
        owner: UsersDTO,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        refresh_balances: bool = True,
        **kwargs,
    ) -> dict[str, Any]:
        """Cash-flow summary including transfer legs and portfolio balances."""
        if refresh_balances:
            refresh_balance_materialized_views(
                self.connector, concurrently=kwargs.get("refresh_balances_concurrently", False)
            )

        frame = self._apply_date_window(
            self._load_transactions(owner=owner, **kwargs), start_date=start_date, end_date=end_date
        )
        completed = frame[frame["status"] == TransactionStatus.COMPLETED.value] if not frame.empty else frame

        inflows = 0.0
        outflows = 0.0
        if not completed.empty:
            income = completed[completed["transaction_kind"] == TransactionKind.INCOME.value]
            expenses = completed[completed["transaction_kind"] == TransactionKind.EXPENSE.value]
            transfers = completed[completed["transaction_kind"] == TransactionKind.TRANSFER.value]

            inflows = float(income["amount"].sum()) + float(transfers["amount"].sum())
            outflows = float(expenses["amount"].sum()) + float(transfers["amount"].sum())

        portfolio_total = 0.0
        if self.account_balances_service is not None:
            balances = self.account_balances_service.get_balances(owner=owner, **kwargs)
            if not balances.empty and "balance" in balances.columns:
                portfolio_total = float(balances["balance"].sum())

        return {
            "inflows": inflows,
            "outflows": outflows,
            "net": inflows - outflows,
            "portfolio_total": portfolio_total,
        }

    def trends(
        self,
        *,
        owner: UsersDTO,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        period: Literal["daily", "weekly", "monthly", "yearly"] = "monthly",
        **kwargs,
    ) -> dict[str, Any]:
        """Time-series totals for completed income and expense rows."""
        frame = self._apply_date_window(
            self._load_transactions(owner=owner, **kwargs), start_date=start_date, end_date=end_date
        )
        if frame.empty:
            return {"period": period, "series": []}

        completed = frame[frame["status"] == TransactionStatus.COMPLETED.value]
        relevant = completed[
            completed["transaction_kind"].isin([TransactionKind.INCOME.value, TransactionKind.EXPENSE.value])
        ]
        if relevant.empty:
            return {"period": period, "series": []}

        freq_map = {"daily": "D", "weekly": "W", "monthly": "ME", "yearly": "YE"}
        indexed = relevant.set_index(pd.to_datetime(relevant["transaction_ts"]))
        grouped = (
            indexed.groupby([pd.Grouper(freq=freq_map[period]), "transaction_kind"])["amount"]
            .sum()
            .reset_index()
            .rename(columns={"transaction_ts": "period_start", "amount": "total"})
        )
        series = grouped.to_dict(orient="records")
        return {"period": period, "series": series}

    def export(
        self,
        *,
        owner: UsersDTO,
        report_type: Literal["spending", "cash-flow", "trends"] = "spending",
        export_format: Literal["csv", "json"] = "csv",
        **kwargs,
    ) -> str | dict[str, Any]:
        """Delegate to analytics helpers and return CSV (MVP stub) or JSON."""
        if report_type == "spending":
            payload = self.spending(owner=owner, **kwargs)
        elif report_type == "cash-flow":
            payload = self.cash_flow(owner=owner, **kwargs)
        else:
            payload = self.trends(owner=owner, **kwargs)

        if export_format == "json":
            return payload

        buffer = io.StringIO()
        if report_type == "trends":
            fieldnames = ["period_start", "transaction_kind", "total"]
            trends_writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
            trends_writer.writeheader()
            for row in payload.get("series", []):
                trends_writer.writerow(row)
        elif report_type == "spending":
            spending_writer = csv.writer(buffer)
            spending_writer.writerow(["metric", "value"])
            spending_writer.writerow(["expense_total", payload.get("expense_total", 0.0)])
            spending_writer.writerow(["income_total", payload.get("income_total", 0.0)])
            spending_writer.writerow([])
            spending_writer.writerow(["group_by", payload.get("group_by", "")])
            spending_writer.writerow(["group_id", "total"])
            for row in payload.get("expenses", []):
                group_key = row.get("category_id") or row.get("from_account_id")
                spending_writer.writerow([group_key, row.get("total", 0.0)])
        else:
            cashflow_writer = csv.writer(buffer)
            cashflow_writer.writerow(["metric", "value"])
            for key, value in payload.items():
                cashflow_writer.writerow([key, value])

        return buffer.getvalue()
