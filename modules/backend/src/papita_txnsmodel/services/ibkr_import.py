"""Idempotent IBKR Activity Statement import service (PPT-101 / #262)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from papita_ingestor_core.importers.ibkr import IBKRStatementSummary, parse_ibkr_activity_statement
from papita_txnsmodel.access.account_details.dto import TradingAccountDetailsDTO
from papita_txnsmodel.access.account_financing.dto import AccountFinancingDTO
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import (
    AccountKind,
    IngestionSource,
    LedgerSide,
    SettlementStatus,
    TransactionKind,
    TransactionStatus,
)
from papita_txnsmodel.services.account_details import TradingAccountDetailsService
from papita_txnsmodel.services.account_financing import AccountFinancingService
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.ingestion import IngestionBridgeService, IngestTransactionRequest
from papita_txnsmodel.services.report_health import compute_position_valuation


class IBKRPositionImportItem(BaseModel):
    """Per-position outcome from importing an IBKR Activity Statement."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    account_id: uuid.UUID
    action: str
    units: float
    unit_price: float
    fx_rate: float
    valued_amount: float
    unrealized_pnl: float | None = None


class IBKRImportResult(BaseModel):
    """Aggregate summary returned by ``IBKRImportService.import_activity_statement``."""

    model_config = ConfigDict(extra="forbid")

    account_code: str | None = None
    period: str | None = None
    as_of: datetime | None = None
    fx_rate: float
    base_currency: str
    positions: list[IBKRPositionImportItem] = Field(default_factory=list)
    total_portfolio_value: float = 0.0
    settled_cash_value: float = 0.0
    margin_loan_value: float = 0.0
    margin_ltv_pct: float | None = None
    deposits_created: int = 0
    deposits_updated: int = 0


class IBKRImportService:
    """Coordinate idempotent IBKR position valuation, margin LTV linking, and deposit ingest."""

    def __init__(
        self,
        *,
        accounts_service: AccountsService,
        trading_details_service: TradingAccountDetailsService,
        financing_service: AccountFinancingService,
        bridge_service: IngestionBridgeService,
    ) -> None:
        self._accounts = accounts_service
        self._trading = trading_details_service
        self._financing = financing_service
        self._bridge = bridge_service

    def import_activity_statement(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        *,
        owner: UsersDTO,
        csv_text: str,
        fx_rate: float = 1.0,
        base_currency: str = "COP",
        cash_account_id: uuid.UUID | None = None,
        margin_account_id: uuid.UUID | None = None,
        source_account_id: uuid.UUID | None = None,
        create_missing_accounts: bool = True,
    ) -> IBKRImportResult:
        """Parse and idempotently apply an IBKR Activity Statement for ``owner``."""
        if fx_rate <= 0:
            raise ValueError("fx_rate must be positive")
        if owner.id is None:
            raise ValueError("owner.id is required")

        summary: IBKRStatementSummary = parse_ibkr_activity_statement(csv_text)
        as_of = summary.as_of or datetime.now(timezone.utc)
        target_currency = base_currency.strip().upper()

        cash_acct: AccountsDTO | None = None
        if cash_account_id is not None:
            loaded_cash = self._accounts.get(obj=cash_account_id, owner=owner)
            if not isinstance(loaded_cash, AccountsDTO):
                raise ValueError("cash_account_id not found for owner")
            cash_acct = loaded_cash

        margin_acct: AccountsDTO | None = None
        if margin_account_id is not None:
            loaded_margin = self._accounts.get(obj=margin_account_id, owner=owner)
            if not isinstance(loaded_margin, AccountsDTO):
                raise ValueError("margin_account_id not found for owner")
            margin_acct = loaded_margin

        if source_account_id is not None:
            loaded_source = self._accounts.get(obj=source_account_id, owner=owner)
            if not isinstance(loaded_source, AccountsDTO):
                raise ValueError("source_account_id not found for owner")

        existing_accounts = self._load_owner_accounts(owner)
        trading_by_symbol = self._map_trading_by_symbol(existing_accounts)

        position_items: list[IBKRPositionImportItem] = []
        linked_asset_ids: list[uuid.UUID] = []
        total_portfolio_value = 0.0

        for pos in summary.positions:
            valued = compute_position_valuation(units=pos.units, unit_price=pos.unit_price, fx_rate=fx_rate)
            total_portfolio_value += valued
            matched = trading_by_symbol.get(pos.symbol.upper())

            if matched is not None and matched.id is not None:
                acct_id = matched.id
                updated_acct = matched.model_copy(
                    update={
                        "current_value": valued,
                        "current_value_as_of": as_of,
                        "fx_rate": fx_rate,
                    }
                )
                self._accounts.update_account(
                    owner=owner,
                    obj=updated_acct,
                    extension={
                        "symbol": pos.symbol.upper(),
                        "buy_value": pos.cost_price,
                        "units": pos.units,
                        "unit_price": pos.unit_price,
                        "fx_rate": fx_rate,
                        "unrealized_pnl": pos.unrealized_pnl,
                    },
                )
                action = "updated"
            elif create_missing_accounts:
                created = self._accounts.create_account(
                    owner=owner,
                    obj=AccountsDTO(
                        owner_id=owner.id,
                        name=f"IBKR {pos.symbol.upper()}",
                        description=f"IBKR {pos.asset_category} position ({pos.symbol.upper()})",
                        account_kind=AccountKind.INVESTMENT_BROKERAGE,
                        ledger_side=LedgerSide.ASSET,
                        currency=target_currency if fx_rate != 1.0 else pos.currency,
                        fx_rate=fx_rate,
                        include_in_balance=True,
                        current_value=valued,
                        current_value_as_of=as_of,
                    ),
                    extension={
                        "symbol": pos.symbol.upper(),
                        "buy_value": pos.cost_price,
                        "units": pos.units,
                        "unit_price": pos.unit_price,
                        "fx_rate": fx_rate,
                        "unrealized_pnl": pos.unrealized_pnl,
                    },
                )
                if created.id is None:
                    raise RuntimeError(f"Created IBKR account for {pos.symbol} missing id")
                acct_id = created.id
                action = "created"
            else:
                continue

            linked_asset_ids.append(acct_id)
            position_items.append(
                IBKRPositionImportItem(
                    symbol=pos.symbol.upper(),
                    account_id=acct_id,
                    action=action,
                    units=pos.units,
                    unit_price=pos.unit_price,
                    fx_rate=fx_rate,
                    valued_amount=valued,
                    unrealized_pnl=pos.unrealized_pnl,
                )
            )

        settled_cash_value = round(summary.settled_cash_usd * fx_rate, 2)
        if cash_account_id is not None and cash_acct is not None:
            self._accounts.update_account(
                owner=owner,
                obj=cash_acct.model_copy(
                    update={
                        "current_value": settled_cash_value,
                        "current_value_as_of": as_of,
                        "fx_rate": fx_rate,
                    }
                ),
            )
            total_portfolio_value += settled_cash_value
            linked_asset_ids.append(cash_account_id)

        margin_loan_value = round(summary.margin_loan_usd * fx_rate, 2)
        if margin_account_id is not None and margin_acct is not None:
            self._accounts.update_account(
                owner=owner,
                obj=margin_acct.model_copy(
                    update={
                        "current_value": margin_loan_value,
                        "current_value_as_of": as_of,
                        "fx_rate": fx_rate,
                    }
                ),
            )
            self._ensure_financing_links(
                owner=owner,
                asset_account_ids=linked_asset_ids,
                loan_account_id=margin_account_id,
            )

        deposits_created = 0
        deposits_updated = 0
        if source_account_id is not None and cash_account_id is not None:
            for dep in summary.deposits_withdrawals:
                from_id = source_account_id if dep.amount > 0 else cash_account_id
                to_id = cash_account_id if dep.amount > 0 else source_account_id
                req = IngestTransactionRequest(
                    ingestion_source=IngestionSource.CSV,
                    source_ref=dep.source_ref,
                    transaction_kind=TransactionKind.TRANSFER,
                    amount=abs(dep.amount),
                    currency=dep.currency,
                    transaction_ts=dep.settle_date or as_of,
                    from_account_id=from_id,
                    to_account_id=to_id,
                    status=TransactionStatus.COMPLETED,
                    settlement_status=SettlementStatus.SETTLED,
                    description=f"IBKR: {dep.description}",
                    tags=["ibkr", "activity_statement", "settled"],
                )
                res = self._bridge.ingest_transaction(owner=owner, request=req)
                if res.outcome == "created":
                    deposits_created += 1
                else:
                    deposits_updated += 1

        margin_ltv_pct = (
            round((margin_loan_value / total_portfolio_value) * 100.0, 2)
            if total_portfolio_value > 0 and margin_loan_value > 0
            else None
        )

        return IBKRImportResult(
            account_code=summary.account_code,
            period=summary.period,
            as_of=as_of,
            fx_rate=fx_rate,
            base_currency=target_currency,
            positions=position_items,
            total_portfolio_value=round(total_portfolio_value, 2),
            settled_cash_value=settled_cash_value,
            margin_loan_value=margin_loan_value,
            margin_ltv_pct=margin_ltv_pct,
            deposits_created=deposits_created,
            deposits_updated=deposits_updated,
        )

    def _load_owner_accounts(self, owner: UsersDTO) -> list[AccountsDTO]:
        df, _ = self._accounts.list_accounts(owner=owner, skip=0, limit=500)
        if df.empty:
            return []
        rows: list[AccountsDTO] = []
        for record in df.to_dict(orient="records"):
            cleaned = {k: (None if v != v else v) for k, v in record.items()}  # noqa: PLR0124
            rows.append(AccountsDTO.model_validate(cleaned))
        return rows

    def _map_trading_by_symbol(self, accounts: list[AccountsDTO]) -> dict[str, AccountsDTO]:
        trading_accounts = [
            acct for acct in accounts if acct.id is not None and acct.account_kind == AccountKind.INVESTMENT_BROKERAGE
        ]
        if not trading_accounts:
            return {}
        ids = [acct.id for acct in trading_accounts if acct.id is not None]
        details_map = self._trading.get_map_by_account_ids(ids)
        by_symbol: dict[str, AccountsDTO] = {}
        for acct in trading_accounts:
            if acct.id is None:
                continue
            detail = details_map.get(acct.id)
            if isinstance(detail, TradingAccountDetailsDTO) and detail.symbol:
                by_symbol[detail.symbol.strip().upper()] = acct
        return by_symbol

    def _ensure_financing_links(
        self,
        *,
        owner: UsersDTO,
        asset_account_ids: list[uuid.UUID],
        loan_account_id: uuid.UUID,
    ) -> None:
        if not asset_account_ids or owner.id is None:
            return
        existing_df = self._financing.get_records(dto=None, owner=owner)
        existing_pairs: set[tuple[uuid.UUID, uuid.UUID]] = set()
        if not existing_df.empty:
            for rec in existing_df.to_dict(orient="records"):
                if rec.get("active", True):
                    existing_pairs.add((rec["asset_account_id"], rec["loan_account_id"]))
        for asset_id in asset_account_ids:
            if (asset_id, loan_account_id) in existing_pairs:
                continue
            self._financing.create(
                obj=AccountFinancingDTO(
                    owner_id=owner.id,
                    asset_account_id=asset_id,
                    loan_account_id=loan_account_id,
                    financing_share=1.0,
                ),
                owner=owner,
            )


__all__ = ["IBKRImportResult", "IBKRImportService", "IBKRPositionImportItem"]
