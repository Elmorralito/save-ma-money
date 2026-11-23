"""Provider-agnostic idempotent portfolio/statement import service.

Accepts a ``NormalizedPortfolioBatch`` produced by any ``BaseBatchImporter``
plugin so ``papita_txnsmodel`` stays decoupled from concrete broker parsers.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

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


class PortfolioPositionInput(BaseModel):
    """Provider-agnostic open equity/ETF position snapshot."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1, max_length=32)
    asset_category: str = "Stocks"
    currency: str = Field(default="USD", min_length=3, max_length=3)
    units: float = Field(gt=0)
    cost_price: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    market_value: float = Field(ge=0)
    unrealized_pnl: float | None = None


class PortfolioCashBalanceInput(BaseModel):
    """Provider-agnostic ending cash summary per currency."""

    model_config = ConfigDict(extra="forbid")

    currency: str = Field(min_length=3, max_length=3)
    ending_cash: float = 0.0
    ending_settled_cash: float = 0.0


class PortfolioTransferInput(BaseModel):
    """Provider-agnostic settled deposit or withdrawal movement."""

    model_config = ConfigDict(extra="forbid")

    currency: str = Field(min_length=3, max_length=3)
    settle_date: datetime | None = None
    description: str = ""
    amount: float
    source_ref: str = Field(min_length=1, max_length=255)


class NormalizedPortfolioBatch(BaseModel):
    """Provider-agnostic statement batch ready for idempotent persistence."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str = Field(default="ibkr-activity-csv", min_length=1, max_length=64)
    provider_label: str = Field(default="IBKR", min_length=1, max_length=32)
    ingestion_source: IngestionSource = IngestionSource.CSV
    tags: list[str] = Field(default_factory=lambda: ["ibkr", "activity_statement", "settled"])
    account_code: str | None = None
    period: str | None = None
    as_of: datetime | None = None
    positions: list[PortfolioPositionInput] = Field(default_factory=list)
    cash_balances: list[PortfolioCashBalanceInput] = Field(default_factory=list)
    transfers: list[PortfolioTransferInput] = Field(default_factory=list)

    @property
    def margin_loan_usd(self) -> float:
        """Return positive USD margin debt when ending USD cash is negative."""
        for row in self.cash_balances:
            if row.currency.upper() == "USD" and row.ending_cash < 0:
                return round(abs(row.ending_cash), 2)
        return 0.0

    @property
    def settled_cash_usd(self) -> float:
        """Return positive settled USD cash (0.0 when account is on margin)."""
        for row in self.cash_balances:
            if row.currency.upper() == "USD" and row.ending_settled_cash > 0:
                return round(row.ending_settled_cash, 2)
        return 0.0


class PortfolioPositionImportItem(BaseModel):
    """Per-position outcome from importing a normalized portfolio statement."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    account_id: uuid.UUID
    action: str
    units: float
    unit_price: float
    fx_rate: float
    valued_amount: float
    unrealized_pnl: float | None = None


class PortfolioImportResult(BaseModel):
    """Aggregate summary returned by ``PortfolioImportService.import_batch``."""

    model_config = ConfigDict(extra="forbid")

    account_code: str | None = None
    period: str | None = None
    as_of: datetime | None = None
    fx_rate: float
    base_currency: str
    positions: list[PortfolioPositionImportItem] = Field(default_factory=list)
    total_portfolio_value: float = 0.0
    settled_cash_value: float = 0.0
    margin_loan_value: float = 0.0
    margin_ltv_pct: float | None = None
    deposits_created: int = 0
    deposits_updated: int = 0


class PortfolioImportService:
    """Coordinate idempotent position valuation, margin LTV linking, and transfer ingest."""

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

    def import_batch(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        *,
        owner: UsersDTO,
        batch: NormalizedPortfolioBatch,
        fx_rate: float = 1.0,
        base_currency: str = "COP",
        cash_account_id: uuid.UUID | None = None,
        margin_account_id: uuid.UUID | None = None,
        source_account_id: uuid.UUID | None = None,
        create_missing_accounts: bool = True,
    ) -> PortfolioImportResult:
        """Apply a ``NormalizedPortfolioBatch`` idempotently for ``owner``."""
        if fx_rate <= 0:
            raise ValueError("fx_rate must be positive")
        if owner.id is None:
            raise ValueError("owner.id is required")

        as_of = batch.as_of or datetime.now(timezone.utc)
        target_currency = base_currency.strip().upper()

        cash_acct = self._require_optional_account(cash_account_id, owner=owner, field="cash_account_id")
        margin_acct = self._require_optional_account(margin_account_id, owner=owner, field="margin_account_id")
        self._require_optional_account(source_account_id, owner=owner, field="source_account_id")

        existing_accounts = self._load_owner_accounts(owner)
        trading_by_symbol = self._map_trading_by_symbol(existing_accounts)

        position_items: list[PortfolioPositionImportItem] = []
        linked_asset_ids: list[uuid.UUID] = []
        total_portfolio_value = 0.0

        for pos in batch.positions:
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
                        name=f"{batch.provider_label} {pos.symbol.upper()}",
                        description=f"{batch.provider_label} {pos.asset_category} position ({pos.symbol.upper()})",
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
                    raise RuntimeError(f"Created {batch.provider_label} account for {pos.symbol} missing id")
                acct_id = created.id
                action = "created"
            else:
                continue

            linked_asset_ids.append(acct_id)
            position_items.append(
                PortfolioPositionImportItem(
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

        settled_cash_value = round(batch.settled_cash_usd * fx_rate, 2)
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

        margin_loan_value = round(batch.margin_loan_usd * fx_rate, 2)
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
            for dep in batch.transfers:
                from_id = source_account_id if dep.amount > 0 else cash_account_id
                to_id = cash_account_id if dep.amount > 0 else source_account_id
                req = IngestTransactionRequest(
                    ingestion_source=batch.ingestion_source,
                    source_ref=dep.source_ref,
                    transaction_kind=TransactionKind.TRANSFER,
                    amount=abs(dep.amount),
                    currency=dep.currency,
                    transaction_ts=dep.settle_date or as_of,
                    from_account_id=from_id,
                    to_account_id=to_id,
                    status=TransactionStatus.COMPLETED,
                    settlement_status=SettlementStatus.SETTLED,
                    description=f"{batch.provider_label}: {dep.description}",
                    tags=list(batch.tags),
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

        return PortfolioImportResult(
            account_code=batch.account_code,
            period=batch.period,
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

    def _require_optional_account(
        self,
        account_id: uuid.UUID | None,
        *,
        owner: UsersDTO,
        field: str,
    ) -> AccountsDTO | None:
        if account_id is None:
            return None
        loaded = self._accounts.get(obj=account_id, owner=owner)
        if not isinstance(loaded, AccountsDTO):
            raise ValueError(f"{field} not found for owner")
        return loaded

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


__all__ = [
    "NormalizedPortfolioBatch",
    "PortfolioCashBalanceInput",
    "PortfolioImportResult",
    "PortfolioImportService",
    "PortfolioPositionImportItem",
    "PortfolioPositionInput",
    "PortfolioTransferInput",
]
