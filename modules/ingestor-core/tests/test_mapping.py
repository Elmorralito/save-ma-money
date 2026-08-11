"""Unit tests for RawRecord encoding and bridge mapping."""

from __future__ import annotations

import uuid

import pytest

from papita_ingestor_core.errors.taxonomy import IngestorValidationError
from papita_ingestor_core.mapping.raw_payload import encode_raw_payload
from papita_ingestor_core.mapping.to_bridge import to_ingest_transaction_request
from papita_ingestor_core.types.records import ParsedRecord, RawRecord
from papita_txnsmodel.model.enums import IngestionSource, TransactionKind


def test_encode_raw_payload_str_passthrough() -> None:
    record = RawRecord(source_id="s", content="hello", ingestion_source=IngestionSource.EMAIL)
    assert encode_raw_payload(record) == "hello"


def test_encode_raw_payload_bytes_b64_prefix() -> None:
    record = RawRecord(source_id="s", content=b"\x00\xff", ingestion_source=IngestionSource.EMAIL)
    encoded = encode_raw_payload(record)
    assert encoded.startswith("b64:")
    assert "AP8=" in encoded or encoded.endswith("AP8=")


def test_to_bridge_expense_complete() -> None:
    account = uuid.uuid4()
    category = uuid.uuid4()
    parsed = ParsedRecord(
        ingestion_source=IngestionSource.EMAIL,
        source_ref="r1",
        transaction_kind=TransactionKind.EXPENSE,
        amount=9.99,
        from_account_id=account,
        category_id=category,
    )
    request = to_ingest_transaction_request(parsed)
    assert request.from_account_id == account
    assert request.category_id == category
    assert request.to_account_id is None


@pytest.mark.parametrize(
    "kind,kwargs,match",
    [
        (
            TransactionKind.EXPENSE,
            {"from_account_id": None, "to_account_id": None, "category_id": uuid.uuid4()},
            "EXPENSE",
        ),
        (
            TransactionKind.INCOME,
            {"from_account_id": uuid.uuid4(), "to_account_id": uuid.uuid4(), "category_id": uuid.uuid4()},
            "INCOME",
        ),
        (
            TransactionKind.TRANSFER,
            {"from_account_id": uuid.uuid4(), "to_account_id": uuid.uuid4(), "category_id": uuid.uuid4()},
            "TRANSFER",
        ),
    ],
)
def test_to_bridge_rejects_incomplete_fks(kind: TransactionKind, kwargs: dict, match: str) -> None:
    parsed = ParsedRecord(
        ingestion_source=IngestionSource.EMAIL,
        transaction_kind=kind,
        amount=1.0,
        **kwargs,
    )
    with pytest.raises(IngestorValidationError, match=match):
        to_ingest_transaction_request(parsed)
