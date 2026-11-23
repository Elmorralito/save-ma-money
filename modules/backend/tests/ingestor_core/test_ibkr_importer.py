"""Tests for IBKR Activity Statement CSV parser and idempotent importer (PPT-101 / #262)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest

from papita_ingestor_core.errors import IngestorParseError
from papita_ingestor_core.importers.ibkr import parse_ibkr_activity_statement
from papita_txnsmodel.access.account_details.dto import TradingAccountDetailsDTO
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import AccountKind, IngestionSource, LedgerSide, SettlementStatus
from papita_txnsmodel.services.ibkr_import import IBKRImportService

_SAMPLE_IBKR_CSV = """\
Statement,Header,Field Name,Field Value
Statement,Data,Period,"November 1, 2026 - November 13, 2026"
Account Information,Header,Field Name,Field Value
Account Information,Data,Account,U10600302
Open Positions,Header,DataDiscriminator,Asset Category,Currency,Symbol,Quantity,Mult,Cost Price,Cost Basis,Close Price,Value,Unrealized P/L,Code
Open Positions,Data,Summary,Stocks,USD,IAU,250,1,97.75,24436.75,72.68,"18,170.00","-6,266.75",
Open Positions,Data,Summary,Stocks,USD,SLV,165,1,75.19,12406.35,42.57,"7,024.05","-5,382.30",
Open Positions,Data,Summary,Stocks,USD,NU,200,1,16.58,3316.00,12.81,"2,562.00","-754.00",
Open Positions,Data,Total,,USD,,, , ,40159.10,,27756.05,-12403.05,
Cash Report,Header,Currency Summary,Currency,Total,Securities,Futures
Cash Report,Data,Ending Cash,USD,"-19,419.25","-19,419.25",0
Cash Report,Data,Ending Settled Cash,USD,"-19,419.25","-19,419.25",0
Deposits & Withdrawals,Header,Currency,Settle Date,Description,Amount
Deposits & Withdrawals,Data,USD,2026-11-14,"Global66 Wire Transfer 17020398",590.40
Deposits & Withdrawals,Data,Total,,,590.40
"""


def test_parse_ibkr_activity_statement_extracts_positions_margin_and_deposits() -> None:
    summary = parse_ibkr_activity_statement(_SAMPLE_IBKR_CSV)

    assert summary.account_code == "U10600302"
    assert summary.as_of == datetime(2026, 11, 13, 0, 0, tzinfo=timezone.utc)
    assert len(summary.positions) == 3

    by_symbol = {p.symbol: p for p in summary.positions}
    assert by_symbol["IAU"].units == pytest.approx(250.0)
    assert by_symbol["IAU"].unit_price == pytest.approx(72.68)
    assert by_symbol["IAU"].unrealized_pnl == pytest.approx(-6266.75)
    assert by_symbol["SLV"].units == pytest.approx(165.0)
    assert by_symbol["NU"].unit_price == pytest.approx(12.81)

    assert summary.margin_loan_usd == pytest.approx(19419.25)
    assert summary.settled_cash_usd == pytest.approx(0.0)
    assert len(summary.deposits_withdrawals) == 1
    dep = summary.deposits_withdrawals[0]
    assert dep.currency == "USD"
    assert dep.amount == pytest.approx(590.40)
    assert dep.source_ref.startswith("ibkr:U10600302:cash:")


def test_parse_ibkr_activity_statement_errors_on_empty_or_invalid() -> None:
    with pytest.raises(IngestorParseError, match="empty"):
        parse_ibkr_activity_statement("   ")

    with pytest.raises(IngestorParseError, match="recognizable"):
        parse_ibkr_activity_statement("col1,col2,col3\n1,2,3\n")


def test_ibkr_import_service_idempotent_valuation_margin_ltv_and_deposit() -> None:
    owner_id = uuid.uuid4()
    owner = UsersDTO.model_construct(id=owner_id, email="u@test.local", username="u")

    iau_id = uuid.uuid4()
    existing_iau = AccountsDTO(
        id=iau_id,
        owner_id=owner_id,
        name="IBKR IAU",
        account_kind=AccountKind.INVESTMENT_BROKERAGE,
        ledger_side=LedgerSide.ASSET,
        currency="COP",
    )
    cash_id = uuid.uuid4()
    margin_id = uuid.uuid4()
    source_id = uuid.uuid4()
    cash_acct = AccountsDTO(
        id=cash_id,
        owner_id=owner_id,
        name="IBKR Cash",
        account_kind=AccountKind.INVESTMENT_BROKERAGE,
        ledger_side=LedgerSide.ASSET,
        currency="COP",
    )
    margin_acct = AccountsDTO(
        id=margin_id,
        owner_id=owner_id,
        name="IBKR Leverage",
        account_kind=AccountKind.LOAN_MORTGAGE,
        ledger_side=LedgerSide.LIABILITY,
        currency="COP",
    )

    source_acct = AccountsDTO(
        id=source_id,
        owner_id=owner_id,
        name="Global66 USD",
        account_kind=AccountKind.CHECKING,
        ledger_side=LedgerSide.ASSET,
        currency="USD",
    )

    accounts_by_id = {cash_id: cash_acct, margin_id: margin_acct, source_id: source_acct}
    accounts_svc = MagicMock()
    accounts_svc.list_accounts.return_value = (pd.DataFrame([existing_iau.model_dump()]), 1)
    accounts_svc.get.side_effect = lambda *, obj, owner: accounts_by_id.get(obj)
    accounts_svc.create_account.side_effect = lambda *, owner, obj, extension=None: obj.model_copy(
        update={"id": uuid.uuid4()}
    )

    trading_svc = MagicMock()
    trading_svc.get_map_by_account_ids.return_value = {
        iau_id: TradingAccountDetailsDTO(account_id=iau_id, symbol="IAU", buy_value=97.75, units=250.0),
    }

    financing_svc = MagicMock()
    financing_svc.get_records.return_value = pd.DataFrame()

    bridge_svc = MagicMock()
    bridge_svc.ingest_transaction.return_value = MagicMock(outcome="created")

    svc = IBKRImportService(
        accounts_service=accounts_svc,
        trading_details_service=trading_svc,
        financing_service=financing_svc,
        bridge_service=bridge_svc,
    )

    fx_rate = 4000.0
    result = svc.import_activity_statement(
        owner=owner,
        csv_text=_SAMPLE_IBKR_CSV,
        fx_rate=fx_rate,
        base_currency="COP",
        cash_account_id=cash_id,
        margin_account_id=margin_id,
        source_account_id=source_id,
    )

    actions = {p.symbol: p.action for p in result.positions}
    assert actions == {"IAU": "updated", "SLV": "created", "NU": "created"}

    # Verify units * unit_price * fx_rate
    iau_item = next(p for p in result.positions if p.symbol == "IAU")
    assert iau_item.valued_amount == pytest.approx(250.0 * 72.68 * fx_rate)

    expected_portfolio = round((250 * 72.68 + 165 * 42.57 + 200 * 12.81) * fx_rate, 2)
    expected_margin = round(19419.25 * fx_rate, 2)
    assert result.total_portfolio_value == pytest.approx(expected_portfolio)
    assert result.margin_loan_value == pytest.approx(expected_margin)
    assert result.margin_ltv_pct == pytest.approx(round((expected_margin / expected_portfolio) * 100.0, 2))
    assert result.deposits_created == 1
    assert result.deposits_updated == 0

    # Verify deposit ingested idempotently with CSV source & SETTLED status
    ingested_req = bridge_svc.ingest_transaction.call_args.kwargs["request"]
    assert ingested_req.ingestion_source == IngestionSource.CSV
    assert ingested_req.settlement_status == SettlementStatus.SETTLED
    assert ingested_req.source_ref.startswith("ibkr:U10600302:cash:")
    # Verify AccountFinancing links created for all 3 positions + cash account
    assert financing_svc.create.call_count == 4


def test_ibkr_import_rejects_foreign_or_missing_account_ids() -> None:
    owner_id = uuid.uuid4()
    owner = UsersDTO.model_construct(id=owner_id, email="u@test.local", username="u")

    accounts_svc = MagicMock()
    accounts_svc.get.return_value = None

    svc = IBKRImportService(
        accounts_service=accounts_svc,
        trading_details_service=MagicMock(),
        financing_service=MagicMock(),
        bridge_service=MagicMock(),
    )

    with pytest.raises(ValueError, match="cash_account_id not found"):
        svc.import_activity_statement(owner=owner, csv_text=_SAMPLE_IBKR_CSV, cash_account_id=uuid.uuid4())

    with pytest.raises(ValueError, match="margin_account_id not found"):
        svc.import_activity_statement(owner=owner, csv_text=_SAMPLE_IBKR_CSV, margin_account_id=uuid.uuid4())

    with pytest.raises(ValueError, match="source_account_id not found"):
        svc.import_activity_statement(owner=owner, csv_text=_SAMPLE_IBKR_CSV, source_account_id=uuid.uuid4())
