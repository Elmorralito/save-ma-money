"""Transaction analytics read models for API report endpoints (FR-12).

All aggregations are **tenant-scoped**: every public method requires
``owner: UsersDTO`` and loads ledger/balance data only for that owner.
Callers must never omit ``owner`` or substitute another tenant's identity.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from papita_txnsmodel.access.account_details.dto import CreditCardAccountDetailsDTO, LoanAccountDetailsDTO
from papita_txnsmodel.access.account_financing.dto import AccountFinancingDTO
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO, TransactionTemplatesDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.session import get_session_manager
from papita_txnsmodel.model.enums import (
    AccountKind,
    CashflowBucket,
    LedgerSide,
    TransactionKind,
    TransactionStatus,
)
from papita_txnsmodel.services.account_balances import AccountBalancesService
from papita_txnsmodel.services.account_details import CreditCardAccountDetailsService, LoanAccountDetailsService
from papita_txnsmodel.services.account_financing import AccountFinancingService
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.balance_views import refresh_balance_materialized_views
from papita_txnsmodel.services.categories import CategoriesService
from papita_txnsmodel.services.report_common import as_uuid, dtos_from_frame, resolve_currency_scope
from papita_txnsmodel.services.report_debt import compute_debt_paydown, simulate_debt_paydown
from papita_txnsmodel.services.report_variance import compute_planned_vs_actual
from papita_txnsmodel.services.report_waterfall import compute_operating_cashflow
from papita_txnsmodel.services.transactions import TransactionsService, TransactionTemplatesService


class ReportService(BaseModel):
    """Service-layer aggregations backing ``/reports/*`` MVP endpoints.

    Tenant rule: every query path receives ``owner=`` and delegates to
    owner-scoped ``TransactionsService`` / ``AccountBalancesService`` reads.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    connector: Any = Field(default_factory=get_session_manager)
    transactions_service: TransactionsService | None = None
    account_balances_service: AccountBalancesService | None = None
    accounts_service: AccountsService | None = None
    categories_service: CategoriesService | None = None
    templates_service: TransactionTemplatesService | None = None
    cc_details_service: CreditCardAccountDetailsService | None = None
    loan_details_service: LoanAccountDetailsService | None = None
    financing_service: AccountFinancingService | None = None

    @model_validator(mode="after")
    def _wire_dependencies(self) -> "ReportService":
        """Instantiate dependent services from the shared connector when omitted."""
        if not isinstance(self.transactions_service, TransactionsService):
            self.transactions_service = TransactionsService.model_validate({"connector": self.connector})
        if not isinstance(self.account_balances_service, AccountBalancesService):
            self.account_balances_service = AccountBalancesService.model_validate({"connector": self.connector})
        if not isinstance(self.accounts_service, AccountsService):
            self.accounts_service = AccountsService.model_validate({"connector": self.connector})
        if not isinstance(self.categories_service, CategoriesService):
            self.categories_service = CategoriesService.model_validate({"connector": self.connector})
        if not isinstance(self.templates_service, TransactionTemplatesService):
            self.templates_service = TransactionTemplatesService.model_validate({"connector": self.connector})
        if not isinstance(self.cc_details_service, CreditCardAccountDetailsService):
            self.cc_details_service = CreditCardAccountDetailsService.model_validate({"connector": self.connector})
        if not isinstance(self.loan_details_service, LoanAccountDetailsService):
            self.loan_details_service = LoanAccountDetailsService.model_validate({"connector": self.connector})
        if not isinstance(self.financing_service, AccountFinancingService):
            self.financing_service = AccountFinancingService.model_validate({"connector": self.connector})
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
        """Spending breakdown for completed expenses plus separate income totals.

        Aggregates in SQL via ``TransactionsService.aggregate_spending`` so report
        cache misses do not load the full window into pandas.
        """
        owner = self._require_owner(owner)
        self._ensure_account_owned(owner=owner, account_id=account_id)
        if self.transactions_service is None:
            raise RuntimeError("transactions_service is not configured.")
        return self.transactions_service.aggregate_spending(
            owner=owner,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
            group_by=group_by,
            **kwargs,
        )

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

    def _load_accounts(self, *, owner: UsersDTO, include_deleted: bool = True, **kwargs) -> list[AccountsDTO]:
        """Load tenant accounts for lookup/aggregation."""
        if self.accounts_service is None:
            return []
        frame = self.accounts_service.get_records(None, owner=owner, include_deleted=include_deleted, **kwargs)
        return dtos_from_frame(frame, AccountsDTO)

    def _load_categories(self, *, owner: UsersDTO, **kwargs) -> list[CategoriesDTO]:
        """Load tenant + global categories visible to ``owner``."""
        if self.categories_service is None:
            return []
        frame = self.categories_service.get_records(None, owner=owner, **kwargs)
        return dtos_from_frame(frame, CategoriesDTO)

    def _load_templates(self, *, owner: UsersDTO, **kwargs) -> list[TransactionTemplatesDTO]:
        """Load active planned transaction templates for ``owner``."""
        if self.templates_service is None:
            return []
        frame = self.templates_service.get_records(None, owner=owner, **kwargs)
        return dtos_from_frame(frame, TransactionTemplatesDTO)

    def _load_cc_details(self, accounts: list[AccountsDTO]) -> dict[uuid.UUID, CreditCardAccountDetailsDTO]:
        """Batch-load credit-card extension rows for pre-validated tenant account IDs."""
        if self.cc_details_service is None:
            return {}
        cc_ids = [acct.id for acct in accounts if acct.id is not None and acct.account_kind == AccountKind.CREDIT_CARD]
        if not cc_ids:
            return {}
        raw = self.cc_details_service.get_map_by_account_ids(cc_ids)
        return {k: v for k, v in raw.items() if isinstance(v, CreditCardAccountDetailsDTO)}

    def _load_loan_details(self, accounts: list[AccountsDTO]) -> dict[uuid.UUID, LoanAccountDetailsDTO]:
        """Batch-load loan extension rows for pre-validated tenant account IDs."""
        if self.loan_details_service is None:
            return {}
        loan_ids = [
            acct.id
            for acct in accounts
            if acct.id is not None and acct.account_kind in {AccountKind.LOAN_MORTGAGE, AccountKind.OTHER_LIABILITY}
        ]
        if not loan_ids:
            return {}
        raw = self.loan_details_service.get_map_by_account_ids(loan_ids)
        return {k: v for k, v in raw.items() if isinstance(v, LoanAccountDetailsDTO)}

    def _load_balance_map(self, *, owner: UsersDTO, **kwargs) -> dict[uuid.UUID, float]:
        """Return ``account_id -> balance`` map from the account_balances MV."""
        if self.account_balances_service is None:
            return {}
        frame = self.account_balances_service.get_balances(owner=owner, **kwargs)
        if getattr(frame, "empty", True):
            return {}
        balances: dict[uuid.UUID, float] = {}
        for row in frame.to_dict(orient="records"):
            aid = as_uuid(row.get("account_id"))
            if aid is not None and row.get("balance") is not None:
                balances[aid] = float(row["balance"])
        return balances

    def _load_financing_links(self, *, owner: UsersDTO, **kwargs) -> list[AccountFinancingDTO]:
        """Load tenant asset-loan financing links."""
        if self.financing_service is None:
            return []
        frame = self.financing_service.get_records(None, owner=owner, **kwargs)
        return dtos_from_frame(frame, AccountFinancingDTO)

    def _load_transactions_dtos(
        self,
        *,
        owner: UsersDTO,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        account_id: uuid.UUID | None = None,
        **kwargs,
    ) -> list[TransactionsDTO]:
        """Load owner-scoped COMPLETED transactions in the window as typed DTOs."""
        frame = self._load_transactions(
            owner=owner,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
            status=TransactionStatus.COMPLETED,
            **kwargs,
        )
        return dtos_from_frame(frame, TransactionsDTO)

    def operating_cashflow(  # pylint: disable=too-many-arguments
        self,
        *,
        owner: UsersDTO,
        start_date: datetime,
        end_date: datetime,
        currency: str | None = None,
        account_id: uuid.UUID | None = None,
        include_monthly_series: bool = False,
        **kwargs,
    ) -> dict[str, Any]:
        """Compute Operating Free Cashflow waterfall for the authenticated tenant."""
        owner = self._require_owner(owner)
        self._ensure_account_owned(owner=owner, account_id=account_id)
        accounts = self._load_accounts(owner=owner, include_deleted=True, **kwargs)
        categories = self._load_categories(owner=owner, **kwargs)
        cc_details = self._load_cc_details(accounts)
        transactions = self._load_transactions_dtos(
            owner=owner,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
            **kwargs,
        )
        return compute_operating_cashflow(
            transactions=transactions,
            accounts=accounts,
            categories=categories,
            cc_details_by_id=cc_details,
            requested_currency=currency,
            include_monthly_series=include_monthly_series,
        )

    def planned_vs_actual(  # pylint: disable=too-many-arguments
        self,
        *,
        owner: UsersDTO,
        start_date: datetime,
        end_date: datetime,
        currency: str | None = None,
        account_id: uuid.UUID | None = None,
        cashflow_bucket: CashflowBucket | None = None,
        as_of: date | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Compare planned transaction templates against settled postings for ``owner``."""
        owner = self._require_owner(owner)
        self._ensure_account_owned(owner=owner, account_id=account_id)
        accounts = self._load_accounts(owner=owner, include_deleted=True, **kwargs)
        categories = self._load_categories(owner=owner, **kwargs)
        templates = self._load_templates(owner=owner, **kwargs)
        cc_details = self._load_cc_details(accounts)
        transactions = self._load_transactions_dtos(
            owner=owner,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
            **kwargs,
        )
        return compute_planned_vs_actual(
            templates=templates,
            transactions=transactions,
            accounts=accounts,
            categories=categories,
            cc_details_by_id=cc_details,
            start_day=start_date.date(),
            end_day=end_date.date(),
            requested_currency=currency,
            account_id=account_id,
            cashflow_bucket=cashflow_bucket,
            as_of=as_of,
        )

    def _build_debt_paydown_payload(
        self,
        *,
        owner: UsersDTO,
        currency: str | None,
        include_excluded: bool,
        target_liquidity_months: float,
        as_of: date | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Assemble debt paydown ranking + trailing 90-day burn context for ``owner``."""
        accounts = self._load_accounts(owner=owner, include_deleted=True, **kwargs)
        categories = self._load_categories(owner=owner, **kwargs)
        templates = self._load_templates(owner=owner, **kwargs)
        cc_details = self._load_cc_details(accounts)
        loan_details = self._load_loan_details(accounts)
        financing = self._load_financing_links(owner=owner, **kwargs)
        balances = self._load_balance_map(owner=owner, **kwargs)

        active_currencies = [acct.currency for acct in accounts if acct.active and acct.closed_at is None]
        liab_currencies = [
            acct.currency
            for acct in accounts
            if acct.active and acct.closed_at is None and acct.ledger_side == LedgerSide.LIABILITY
        ]
        selected_currency, _, _ = resolve_currency_scope(liab_currencies, active_currencies, currency)

        now_utc = datetime.now(timezone.utc)
        start_90d = now_utc - timedelta(days=90)
        txns_90d = self._load_transactions_dtos(owner=owner, start_date=start_90d, end_date=now_utc, **kwargs)
        outflows_90d = 0.0
        if txns_90d:
            waterfall_90d = compute_operating_cashflow(
                transactions=txns_90d,
                accounts=accounts,
                categories=categories,
                cc_details_by_id=cc_details,
                requested_currency=selected_currency,
                include_monthly_series=False,
            )
            outflows_90d = float(waterfall_90d["waterfall"]["total_operating_outflows"])

        return compute_debt_paydown(
            accounts=accounts,
            loan_details_by_id=loan_details,
            financing_links=financing,
            balance_by_account_id=balances,
            templates=templates,
            categories=categories,
            operating_outflows_90d=outflows_90d,
            requested_currency=selected_currency,
            include_excluded=include_excluded,
            target_liquidity_months=target_liquidity_months,
            as_of=as_of,
        )

    def debt_paydown(
        self,
        *,
        owner: UsersDTO,
        currency: str | None = None,
        include_excluded: bool = False,
        target_liquidity_months: float = 4.0,
        as_of: date | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Rank active tenant liabilities by normalized effective annual rate and interest drag."""
        owner = self._require_owner(owner)
        payload = self._build_debt_paydown_payload(
            owner=owner,
            currency=currency,
            include_excluded=include_excluded,
            target_liquidity_months=target_liquidity_months,
            as_of=as_of,
            **kwargs,
        )
        payload.pop("_internal_ranked", None)
        return payload

    def simulate_debt_paydown(  # pylint: disable=too-many-arguments
        self,
        *,
        owner: UsersDTO,
        currency: str | None = None,
        strategy: Literal["avalanche", "snowball"] = "avalanche",
        extra_monthly_prepayment: float = 0.0,
        lump_sum_prepayment: float = 0.0,
        lump_sum_month_offset: int = 1,
        periodic_lump_sums: list[dict[str, Any]] | None = None,
        target_liquidity_months: float = 4.0,
        horizon_months: int = 60,
        as_of: date | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Simulate accelerated debt paydown and evaluate the liquid cash runway guardrail."""
        owner = self._require_owner(owner)
        paydown_payload = self._build_debt_paydown_payload(
            owner=owner,
            currency=currency,
            include_excluded=False,
            target_liquidity_months=target_liquidity_months,
            as_of=as_of,
            **kwargs,
        )
        return simulate_debt_paydown(
            paydown_report=paydown_payload,
            strategy=strategy,
            extra_monthly_prepayment=extra_monthly_prepayment,
            lump_sum_prepayment=lump_sum_prepayment,
            lump_sum_month_offset=lump_sum_month_offset,
            periodic_lump_sums=periodic_lump_sums,
            target_liquidity_months=target_liquidity_months,
            horizon_months=horizon_months,
            as_of=as_of,
        )
