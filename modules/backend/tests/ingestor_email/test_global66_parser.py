"""Tests for Global66 international wire email parser (PPT-101 / #262)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from papita_ingestor_core.errors import IngestorParseError
from papita_ingestor_core.mapping import to_ingest_transaction_request
from papita_ingestor_core.types.records import RawRecord
from papita_ingestor_email.parsers import Global66Parser, default_email_parsers
from papita_txnsmodel.model.enums import IngestionSource, SettlementStatus, TransactionKind, TransactionStatus


def _make_record(
    *,
    sender: str = "notificaciones@global66.com",
    subject: str = "Your Global66 wire transfer confirmation",
    body: str,
    source_ref: str | None = "gmail:msg-global66-001",
    ingestion_source: IngestionSource = IngestionSource.EMAIL,
) -> RawRecord:
    return RawRecord(
        source_id="gmail",
        source_ref=source_ref,
        content=body,
        metadata={"sender": sender, "subject": subject},
        ingestion_source=ingestion_source,
    )


def test_global66_registered_in_default_parsers() -> None:
    parsers = default_email_parsers()
    assert any(isinstance(p, Global66Parser) for p in parsers)


def test_global66_parses_usd_wire_to_ibkr_as_in_transit() -> None:
    parser = Global66Parser()
    record = _make_record(
        body=(
            "Your 590.40 USD wire transfer via Global66 (Transaction No. 17020398 "
            "destined for UMB Bank / Interactive Brokers) was sent on November 14, 2026, at 3:00 PM."
        ),
    )

    assert parser.can_parse(record) is True
    parsed = parser.parse(record)

    assert parsed.transaction_kind == TransactionKind.TRANSFER
    assert parsed.amount == pytest.approx(590.40)
    assert parsed.currency == "USD"
    assert parsed.status == TransactionStatus.COMPLETED
    assert parsed.settlement_status == SettlementStatus.IN_TRANSIT
    assert parsed.reference_number == "17020398"
    assert parsed.source_ref == "gmail:msg-global66-001"
    assert parsed.transaction_ts == datetime(2026, 11, 14, 15, 0, tzinfo=timezone.utc)
    assert "global66" in parsed.tags
    assert "in_transit" in parsed.tags

    # Verify bridge mapping preserves settlement_status=IN_TRANSIT
    complete = parsed.model_copy(
        update={
            "from_account_id": uuid.uuid4(),
            "to_account_id": uuid.uuid4(),
        }
    )
    bridge_req = to_ingest_transaction_request(complete)
    assert bridge_req.settlement_status == SettlementStatus.IN_TRANSIT


def test_global66_parses_spanish_settled_notification() -> None:
    parser = Global66Parser()
    record = _make_record(
        subject="Tu transferencia internacional fue acreditada",
        body="Tu envío por USD 1,250.00 (Transacción #99887766) para Interactive Brokers fue acreditada el 2026-11-16.",
        source_ref="gmail:msg-global66-002",
    )

    assert parser.can_parse(record) is True
    parsed = parser.parse(record)

    assert parsed.amount == pytest.approx(1250.0)
    assert parsed.currency == "USD"
    assert parsed.settlement_status == SettlementStatus.SETTLED
    assert parsed.reference_number == "99887766"
    assert "settled" in parsed.tags


def test_global66_rejects_non_global66_sender() -> None:
    parser = Global66Parser()
    record = _make_record(
        sender="alerts@notificacionesbancolombia.com",
        body="Your 590.40 USD wire transfer (Transaction No. 17020398).",
    )
    assert parser.can_parse(record) is False


def test_global66_requires_source_ref_and_amount() -> None:
    parser = Global66Parser()
    with pytest.raises(IngestorParseError, match="source_ref"):
        parser.parse(_make_record(body="590.40 USD wire transfer", source_ref=None))

    with pytest.raises(IngestorParseError, match="amount"):
        parser.parse(_make_record(body="Global66 wire transfer confirmation without number"))
