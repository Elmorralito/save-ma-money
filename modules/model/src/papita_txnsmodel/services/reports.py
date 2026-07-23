"""Transaction analytics read models for API report endpoints (FR-12).

All aggregations are **tenant-scoped**: every public method requires
``owner: UsersDTO`` and loads ledger/balance data only for that owner.
Callers must never omit ``owner`` or substitute another tenant's identity.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime
from typing import Any, Literal, Type

import pandas as pd
from pydantic import BaseModel, ConfigDict, model_validator

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.model.enums import TransactionKind, TransactionStatus
from papita_txnsmodel.services.account_balances import AccountBalancesService
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.balance_views import refresh_balance_materialized_views
from papita_txnsmodel.services.transactions import TransactionsService


class ReportService(BaseModel):
    """Service-layer aggregations backing ``/reports/*`` MVP endpoints.

    Tenant rule: every query path receives ``owner=`` and delegates to
    owner-scoped ``TransactionsService`` / ``AccountBalancesService`` reads.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    connector: Type[SQLDatabaseConnector] = SQLDatabaseConnector
    transactions_service: TransactionsService | None = None
    account_balances_service: AccountBalancesService | None = None
    accounts_service: AccountsService | None = None

    @model_validator(mode="after")
    def _wire_dependencies(self) -> "ReportService":
        """Instantiate dependent services from the shared connector when omitted."""
        if not isinstance(self.transactions_service, TransactionsService):
            self.transactions_service = TransactionsService.model_validate({"connector": self.connector})
        if not isinstance(self.account_balances_service, AccountBalancesService):
            self.account_balances_service = AccountBalancesService.model_validate({"connector": self.connector})
        if not isinstance(self.accounts_service, AccountsService):
            self.accounts_service = AccountsService.model_validate({"connector": self.connector})
        return self

    def close(self) -> None:
        """Close the database connection."""
        self.connector.close()

    @staticmethod
    def _require_owner(owner: UsersDTO | None) -> UsersDTO:
        """Reject missing tenant context before any report aggregation."""
        if owner is None or owner.id is None:
            raise ValueError("Reports require owner=UsersDTO with a tenant id.")
        return owner

    def _ensure_account_owned(self, *, owner: UsersDTO, account_id: uuid.UUID | None) -> None:
        """Ensure optional ``account_id`` belongs to the authenticated tenant."""
        if account_id is None:
            return
        if self.accounts_service is None:
            raise RuntimeError("accounts_service is not configured.")
        account = self.accounts_service.get(obj=account_id, owner=owner)
        if account is None:
            raise ValueError("Account not found for tenant.")

    def _load_transactions(
        self,
        *,
        owner: UsersDTO,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        account_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        status: TransactionStatus | None = TransactionStatus.COMPLETED,
        **kwargs,
    ) -> pd.DataFrame:
        """Load tenant-scoped transactions with SQL date/account/status filters.

        Uses ``TransactionsService.get_transactions_frame`` so report paths do not
        pull the full ledger into pandas before windowing. DAO-shaped frames are
        flattened to JSON-serialized DTO rows for aggregation helpers.
        """
        owner = self._require_owner(owner)
        if self.transactions_service is None:
            raise RuntimeError("transactions_service is not configured.")
        records = self.transactions_service.get_transactions_frame(
            owner=owner,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
            category_id=category_id,
            status=status,
            exclude_transfer=False,
            **kwargs,
        )
        if getattr(records, "empty", True):
            return pd.DataFrame()
        if "transaction_ts" in records.columns:
            return records

        dto_type = self.transactions_service.dto_type
        dao_type = dto_type.__dao_type__
        if len(records.columns) == 1 and isinstance(records.iloc[0, 0], dao_type):
            return pd.DataFrame([dto_type.from_dao(row).model_dump(mode="json") for row in records.iloc[:, 0].tolist()])
        return pd.DataFrame()

    def spending(
        self,
        *,
        owner: UsersDTO,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        group_by: Literal["category", "account"] = "category",
        account_id: uuid.UUID | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Spending breakdown for completed expenses plus separate income totals."""
        owner = self._require_owner(owner)
        self._ensure_account_owned(owner=owner, account_id=account_id)
        frame = self._load_transactions(
            owner=owner,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
            **kwargs,
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

    @staticmethod
    def _completed_cash_flow_totals(
        completed: pd.DataFrame, *, account_id: uuid.UUID | None = None
    ) -> tuple[float, float]:
        """Sum inflows and outflows for COMPLETED income, expense, and transfer rows.

        Portfolio mode (no ``account_id``) counts each transfer on both sides so net
        is unchanged. Account-scoped mode attributes transfer amount as an outflow
        when the account is the source leg and an inflow when it is the destination.
        """
        if completed.empty:
            return 0.0, 0.0
        income = completed[completed["transaction_kind"] == TransactionKind.INCOME.value]
        expenses = completed[completed["transaction_kind"] == TransactionKind.EXPENSE.value]
        transfers = completed[completed["transaction_kind"] == TransactionKind.TRANSFER.value]
        income_total = float(income["amount"].sum()) if not income.empty else 0.0
        expense_total = float(expenses["amount"].sum()) if not expenses.empty else 0.0
        if transfers.empty:
            return income_total, expense_total

        if account_id is None:
            transfer_total = float(transfers["amount"].sum())
            return income_total + transfer_total, expense_total + transfer_total

        account_key = str(account_id)
        transfer_in = 0.0
        transfer_out = 0.0
        if "to_account_id" in transfers.columns:
            transfer_in = float(transfers.loc[transfers["to_account_id"].astype(str) == account_key, "amount"].sum())
        if "from_account_id" in transfers.columns:
            transfer_out = float(transfers.loc[transfers["from_account_id"].astype(str) == account_key, "amount"].sum())
        return income_total + transfer_in, expense_total + transfer_out

    def _portfolio_total(self, *, owner: UsersDTO, account_id: uuid.UUID | None, **kwargs) -> float:
        """Sum tenant account balances, optionally filtered to one account."""
        if self.account_balances_service is None:
            return 0.0
        balances = self.account_balances_service.get_balances(owner=owner, account_id=account_id, **kwargs)
        if balances.empty or "balance" not in balances.columns:
            return 0.0
        return float(balances["balance"].sum())

    def cash_flow(
        self,
        *,
        owner: UsersDTO,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        account_id: uuid.UUID | None = None,
        refresh_balances: bool = False,
        **kwargs,
    ) -> dict[str, Any]:
        """Cash-flow summary including transfer legs and portfolio balances.

        ``refresh_balances`` defaults to ``False`` so export/cash-flow reads do not
        pay for MV refresh unless the caller opts in.
        """
        owner = self._require_owner(owner)
        self._ensure_account_owned(owner=owner, account_id=account_id)
        if refresh_balances:
            refresh_balance_materialized_views(
                self.connector, concurrently=kwargs.get("refresh_balances_concurrently", False)
            )

        frame = self._load_transactions(
            owner=owner,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
            **kwargs,
        )
        completed = frame[frame["status"] == TransactionStatus.COMPLETED.value] if not frame.empty else frame
        inflows, outflows = self._completed_cash_flow_totals(completed, account_id=account_id)
        portfolio_total = self._portfolio_total(owner=owner, account_id=account_id, **kwargs)

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
        account_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Time-series totals for completed income and expense rows."""
        owner = self._require_owner(owner)
        self._ensure_account_owned(owner=owner, account_id=account_id)
        frame = self._load_transactions(
            owner=owner,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
            category_id=category_id,
            **kwargs,
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
        owner = self._require_owner(owner)
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
