"""Interactive Brokers (IBKR) Activity Statement CSV parser (PPT-101 / #262)."""

from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from papita_ingestor_core.errors import IngestorParseError
from papita_ingestor_core.importers.base import BaseBatchImporter
from papita_ingestor_core.plugins import PluginManifest
from papita_txnsmodel.model.enums import IngestionSource
from papita_txnsmodel.services.portfolio_import import (
    NormalizedPortfolioBatch,
    PortfolioCashBalanceInput,
    PortfolioPositionInput,
    PortfolioTransferInput,
)

_PERIOD_END_RE = re.compile(
    r"([A-Za-z]+\s+\d{1,2},\s*\d{4})\s*$",
)


def _to_float(raw: str | None) -> float | None:
    """Parse an IBKR numeric CSV cell, stripping commas and whitespace."""
    if raw is None:
        return None
    cleaned = raw.strip().replace(",", "")
    if not cleaned or cleaned in {"--", "N/A", "-"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_date(raw: str | None) -> datetime | None:
    """Parse IBKR statement dates (``YYYY-MM-DD`` or ``Month DD, YYYY``)."""
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


class IBKRPosition(BaseModel):
    """Single open equity/ETF position from an IBKR Activity Statement."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1, max_length=32)
    asset_category: str = "Stocks"
    currency: str = Field(default="USD", min_length=3, max_length=3)
    units: float = Field(gt=0)
    cost_price: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    market_value: float = Field(ge=0)
    unrealized_pnl: float | None = None


class IBKRCashBalance(BaseModel):
    """Ending cash summary per currency from IBKR ``Cash Report``."""

    model_config = ConfigDict(extra="forbid")

    currency: str = Field(min_length=3, max_length=3)
    ending_cash: float = 0.0
    ending_settled_cash: float = 0.0


class IBKRDepositWithdrawal(BaseModel):
    """Settled deposit or withdrawal row from IBKR ``Deposits & Withdrawals``."""

    model_config = ConfigDict(extra="forbid")

    currency: str = Field(min_length=3, max_length=3)
    settle_date: datetime | None = None
    description: str = ""
    amount: float
    source_ref: str = Field(min_length=1, max_length=255)


class IBKRStatementSummary(BaseModel):
    """Structured output of ``parse_ibkr_activity_statement``."""

    model_config = ConfigDict(extra="forbid")

    account_code: str | None = None
    period: str | None = None
    as_of: datetime | None = None
    positions: list[IBKRPosition] = Field(default_factory=list)
    cash_balances: list[IBKRCashBalance] = Field(default_factory=list)
    deposits_withdrawals: list[IBKRDepositWithdrawal] = Field(default_factory=list)

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


def _index_header(row: list[str]) -> dict[str, int]:
    """Map lowercased column header names to column indices."""
    return {col.strip().lower(): idx for idx, col in enumerate(row)}


def _cell(row: list[str], header: dict[str, int], *names: str) -> str:
    """Return the first matching cell value by candidate column name."""
    for name in names:
        idx = header.get(name)
        if idx is not None and idx < len(row):
            return row[idx].strip()
    return ""


def _build_deposit_ref(
    *,
    account_code: str | None,
    currency: str,
    settle_date_raw: str,
    amount: float,
    description: str,
) -> str:
    """Build deterministic idempotent ``source_ref`` for an IBKR cash movement."""
    acct = account_code or "ibkr"
    digest = hashlib.sha256(f"{acct}|{currency}|{settle_date_raw}|{amount:.2f}|{description}".encode()).hexdigest()[:16]
    return f"ibkr:{acct}:cash:{digest}"


def parse_ibkr_activity_statement(csv_text: str) -> IBKRStatementSummary:  # pylint: disable=too-many-locals,too-many-branches
    """Parse an Interactive Brokers multi-section Activity Statement CSV.

    Supports standard IBKR sections:
    - ``Statement`` (period and statement end date)
    - ``Account Information`` (account identifier)
    - ``Open Positions`` (``Summary`` rows with quantity, cost price, close price, unrealized P/L)
    - ``Cash Report`` (``Ending Cash`` / ``Ending Settled Cash`` per currency, including negative margin)
    - ``Deposits & Withdrawals`` (wire arrivals / disbursements)

    Args:
        csv_text: Raw UTF-8 CSV content exported from IBKR Client Portal.

    Returns:
        Structured ``IBKRStatementSummary`` ready for idempotent persistence.

    Raises:
        IngestorParseError: When the CSV is empty or lacks recognizable IBKR sections.
    """
    cleaned_text = csv_text.lstrip("\ufeff").strip()
    if not cleaned_text:
        raise IngestorParseError("IBKR Activity Statement CSV is empty")

    reader = csv.reader(io.StringIO(cleaned_text))
    headers: dict[str, dict[str, int]] = {}
    account_code: str | None = None
    period: str | None = None
    as_of: datetime | None = None
    positions: list[IBKRPosition] = []
    cash_by_currency: dict[str, dict[str, float]] = {}
    deposits: list[IBKRDepositWithdrawal] = []
    recognized_sections = 0

    for row in reader:
        if len(row) < 3:
            continue
        section = row[0].strip()
        row_type = row[1].strip()
        section_key = section.lower()

        if row_type == "Header":
            headers[section_key] = _index_header(row)
            if section_key in {
                "statement",
                "account information",
                "open positions",
                "cash report",
                "deposits & withdrawals",
            }:
                recognized_sections += 1
            continue

        if row_type != "Data":
            continue

        if section_key == "statement" and len(row) >= 4:
            field_name = row[2].strip().lower()
            field_val = row[3].strip()
            if field_name == "period":
                period = field_val
                end_match = _PERIOD_END_RE.search(field_val)
                if end_match:
                    as_of = _parse_date(end_match.group(1))
        elif section_key == "account information" and len(row) >= 4:
            if row[2].strip().lower() == "account":
                account_code = row[3].strip()
        elif section_key == "open positions":
            hdr = headers.get("open positions", {})
            discriminator = _cell(row, hdr, "datadiscriminator", "data discriminator")
            if discriminator and discriminator.lower() != "summary":
                continue
            symbol = _cell(row, hdr, "symbol").upper()
            if not symbol or symbol.lower() in {"total", "subtotal"}:
                continue
            currency = (_cell(row, hdr, "currency") or "USD").upper()
            if len(currency) != 3:
                continue
            units = _to_float(_cell(row, hdr, "quantity"))
            close_price = _to_float(_cell(row, hdr, "close price", "mark price"))
            cost_price = _to_float(_cell(row, hdr, "cost price"))
            market_value = _to_float(_cell(row, hdr, "value"))
            unrealized_pnl = _to_float(_cell(row, hdr, "unrealized p/l"))
            if units is None or units <= 0 or close_price is None or close_price < 0:
                continue
            resolved_cost = cost_price if (cost_price is not None and cost_price > 0) else max(close_price, 0.0001)
            resolved_value = market_value if (market_value is not None and market_value >= 0) else units * close_price
            positions.append(
                IBKRPosition(
                    symbol=symbol,
                    asset_category=_cell(row, hdr, "asset category") or "Stocks",
                    currency=currency,
                    units=units,
                    cost_price=resolved_cost,
                    unit_price=close_price,
                    market_value=round(resolved_value, 2),
                    unrealized_pnl=round(unrealized_pnl, 2) if unrealized_pnl is not None else None,
                )
            )
        elif section_key == "cash report":
            hdr = headers.get("cash report", {})
            metric = _cell(row, hdr, "currency summary", "field name").lower()
            currency = _cell(row, hdr, "currency").upper()
            total = _to_float(_cell(row, hdr, "total"))
            if len(currency) != 3 or currency == "BASE" or total is None:
                continue
            bucket = cash_by_currency.setdefault(currency, {"ending_cash": 0.0, "ending_settled_cash": 0.0})
            if metric == "ending cash":
                bucket["ending_cash"] = round(total, 2)
            elif metric == "ending settled cash":
                bucket["ending_settled_cash"] = round(total, 2)
        elif section_key == "deposits & withdrawals":
            hdr = headers.get("deposits & withdrawals", {})
            currency = _cell(row, hdr, "currency").upper()
            if len(currency) != 3 or currency.startswith("TOT"):
                continue
            amount = _to_float(_cell(row, hdr, "amount"))
            if amount is None or amount == 0:
                continue
            settle_raw = _cell(row, hdr, "settle date", "date")
            desc = _cell(row, hdr, "description") or "IBKR cash transfer"
            deposits.append(
                IBKRDepositWithdrawal(
                    currency=currency,
                    settle_date=_parse_date(settle_raw),
                    description=desc,
                    amount=round(amount, 2),
                    source_ref=_build_deposit_ref(
                        account_code=account_code,
                        currency=currency,
                        settle_date_raw=settle_raw,
                        amount=amount,
                        description=desc,
                    ),
                )
            )

    if recognized_sections == 0:
        raise IngestorParseError("CSV does not contain recognizable IBKR Activity Statement sections")

    cash_balances = [
        IBKRCashBalance(
            currency=cur,
            ending_cash=vals["ending_cash"],
            ending_settled_cash=vals["ending_settled_cash"],
        )
        for cur, vals in sorted(cash_by_currency.items())
    ]

    return IBKRStatementSummary(
        account_code=account_code,
        period=period,
        as_of=as_of,
        positions=positions,
        cash_balances=cash_balances,
        deposits_withdrawals=deposits,
    )


class IBKRStatementImporter(BaseBatchImporter):
    """``BaseBatchImporter`` plugin for IBKR Activity Statement CSV exports."""

    registry_id = "ibkr-activity-csv"
    PLUGIN_MANIFEST = PluginManifest(
        plugin_id="ibkr-activity-csv",
        kind="batch_importer",
        ingestion_source=IngestionSource.CSV,
        supported_media_types=("text/csv", "application/csv"),
        capabilities=frozenset({"batch_import", "positions", "margin_ltv", "transfers"}),
        description="Interactive Brokers Activity Statement CSV importer.",
    )

    @property
    def importer_id(self) -> str:
        return self.registry_id

    @property
    def manifest(self) -> PluginManifest:
        return self.PLUGIN_MANIFEST

    def can_import(
        self,
        *,
        filename: str | None = None,
        content_type: str | None = None,
        sample: str | bytes = "",
    ) -> bool:
        text = sample.decode("utf-8", errors="ignore") if isinstance(sample, bytes) else sample
        lowered = text.lower()
        if any(
            marker in lowered
            for marker in (
                "open positions,header",
                "cash report,header",
                "statement,header",
                "account information,header",
            )
        ):
            return True
        if filename and filename.lower().endswith(".csv") and "ibkr" in filename.lower():
            return True
        return False

    def parse_statement(self, payload: str | bytes) -> NormalizedPortfolioBatch:
        csv_text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        summary = parse_ibkr_activity_statement(csv_text)
        return NormalizedPortfolioBatch(
            provider_id=self.importer_id,
            provider_label="IBKR",
            ingestion_source=IngestionSource.CSV,
            tags=["ibkr", "activity_statement", "settled"],
            account_code=summary.account_code,
            period=summary.period,
            as_of=summary.as_of,
            positions=[PortfolioPositionInput.model_validate(pos.model_dump()) for pos in summary.positions],
            cash_balances=[PortfolioCashBalanceInput.model_validate(cb.model_dump()) for cb in summary.cash_balances],
            transfers=[PortfolioTransferInput.model_validate(dep.model_dump()) for dep in summary.deposits_withdrawals],
        )


__all__ = [
    "IBKRCashBalance",
    "IBKRDepositWithdrawal",
    "IBKRPosition",
    "IBKRStatementImporter",
    "IBKRStatementSummary",
    "parse_ibkr_activity_statement",
]
