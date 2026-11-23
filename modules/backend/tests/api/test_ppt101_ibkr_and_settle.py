"""API tests for IBKR Activity Statement import and transfer settlement (PPT-101 / #262)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from papita_ingestor_core.errors import IngestorParseError
from papita_txnsapi.dependencies.services import get_ibkr_import_service
from papita_txnsapi.schemas.ingestion import assert_ingestion_response_allowlist
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import SettlementStatus, TransactionKind, TransactionStatus
from papita_txnsmodel.services.ibkr_import import IBKRImportResult, IBKRPositionImportItem


def test_ingestion_response_allowlist_includes_ibkr_response() -> None:
    assert_ingestion_response_allowlist()


def test_import_ibkr_activity_statement_endpoint_returns_200(
    authed_client: tuple[TestClient, UsersDTO],
) -> None:
    client, _owner = authed_client
    acct_id = uuid.uuid4()
    mock_svc = MagicMock()
    mock_svc.import_activity_statement.return_value = IBKRImportResult(
        account_code="U10600302",
        period="November 1, 2026 - November 13, 2026",
        as_of=datetime(2026, 11, 13, tzinfo=timezone.utc),
        fx_rate=4000.0,
        base_currency="COP",
        positions=[
            IBKRPositionImportItem(
                symbol="IAU",
                account_id=acct_id,
                action="updated",
                units=250.0,
                unit_price=72.68,
                fx_rate=4000.0,
                valued_amount=72_680_000.0,
                unrealized_pnl=-6266.75,
            )
        ],
        total_portfolio_value=72_680_000.0,
        settled_cash_value=0.0,
        margin_loan_value=36_000_000.0,
        margin_ltv_pct=49.53,
        deposits_created=1,
        deposits_updated=0,
    )
    client.app.dependency_overrides[get_ibkr_import_service] = lambda: mock_svc  # type: ignore[attr-defined]
    try:
        resp = client.post(
            "/api/v1/ingestion/ibkr/activity-statement",
            json={"csv_content": "Statement,Header,Field Name,Field Value", "fx_rate": 4000.0, "base_currency": "COP"},
        )
    finally:
        client.app.dependency_overrides.pop(get_ibkr_import_service, None)  # type: ignore[attr-defined]

    assert resp.status_code == 200
    body = resp.json()
    assert body["account_code"] == "U10600302"
    assert body["margin_ltv_pct"] == 49.53
    assert len(body["positions"]) == 1
    assert body["positions"][0]["symbol"] == "IAU"


def test_import_ibkr_activity_statement_invalid_csv_returns_422(
    authed_client: tuple[TestClient, UsersDTO],
) -> None:
    client, _owner = authed_client
    mock_svc = MagicMock()
    mock_svc.import_activity_statement.side_effect = IngestorParseError("CSV invalid")
    client.app.dependency_overrides[get_ibkr_import_service] = lambda: mock_svc  # type: ignore[attr-defined]
    try:
        resp = client.post(
            "/api/v1/ingestion/ibkr/activity-statement",
            json={"csv_content": "bad,csv"},
        )
    finally:
        client.app.dependency_overrides.pop(get_ibkr_import_service, None)  # type: ignore[attr-defined]

    assert resp.status_code == 422
    assert "CSV invalid" in resp.json()["detail"]


def test_settle_in_transit_transfer_endpoint(
    transactions_client: tuple[TestClient, UsersDTO, MagicMock],
) -> None:
    client, owner, mock_svc = transactions_client
    txn_id = uuid.uuid4()
    in_transit = TransactionsDTO(
        id=txn_id,
        owner_id=owner.id,
        transaction_kind=TransactionKind.TRANSFER,
        amount=590.40,
        currency="USD",
        transaction_ts=datetime(2026, 11, 14, 15, 0, tzinfo=timezone.utc),
        from_account_id=uuid.uuid4(),
        to_account_id=uuid.uuid4(),
        status=TransactionStatus.COMPLETED,
        settlement_status=SettlementStatus.IN_TRANSIT,
        description="Global66 wire",
    )
    settled = in_transit.model_copy(update={"settlement_status": SettlementStatus.SETTLED})
    mock_svc.get.return_value = in_transit
    mock_svc.settle_transfer.return_value = settled

    resp = client.post(f"/api/v1/transactions/{txn_id}/settle")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(txn_id)
    assert body["status"] == "completed"
    assert body["settlement_status"] == "settled"
    mock_svc.settle_transfer.assert_called_once()


def test_settle_cancelled_transfer_returns_409(
    transactions_client: tuple[TestClient, UsersDTO, MagicMock],
) -> None:
    client, owner, mock_svc = transactions_client
    txn_id = uuid.uuid4()
    cancelled = TransactionsDTO(
        id=txn_id,
        owner_id=owner.id,
        transaction_kind=TransactionKind.TRANSFER,
        amount=100.0,
        currency="USD",
        transaction_ts=datetime(2026, 11, 14, 15, 0, tzinfo=timezone.utc),
        from_account_id=uuid.uuid4(),
        to_account_id=uuid.uuid4(),
        status=TransactionStatus.CANCELLED,
        settlement_status=SettlementStatus.IN_TRANSIT,
        description="Cancelled wire",
    )
    mock_svc.get.return_value = cancelled

    resp = client.post(f"/api/v1/transactions/{txn_id}/settle")
    assert resp.status_code == 409
