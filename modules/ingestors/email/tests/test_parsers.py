"""Unit tests for Bancolombia / Nequi / Fallback email parsers (PPT-081 / #175)."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from types import SimpleNamespace

import pytest
from helpers_records import raw_from_eml

from papita_ingestor_core.errors import IngestorParseError
from papita_ingestor_core.registry import ParserRegistry
from papita_ingestor_core.runner.ingestion_runner import IngestionRunner
from papita_ingestor_core.settings.base import BaseIngestorSettings
from papita_ingestor_core.sources.base import BaseIngestorSource
from papita_ingestor_core.types.records import FetchFilter, RawRecord
from papita_ingestor_email.parsers import BancolombiaParser, FallbackEmailParser, NequiParser, ensure_parsers_registered
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import TransactionKind


class _ListSource(BaseIngestorSource):
    """Minimal source that yields a fixed record list."""

    registry_id = "list-source"

    def __init__(self, records: list[RawRecord]) -> None:
        self._records = list(records)

    @property
    def source_id(self) -> str:
        return self.registry_id

    def connect(self) -> None:
        return None

    def disconnect(self) -> None:
        return None

    def fetch(self, fetch_filter: FetchFilter | None = None) -> Iterable[RawRecord]:
        return list(self._records)

    def acknowledge(self, record: RawRecord) -> None:
        return None


class _DlqBridge:
    """Bridge stub that records dead letters only."""

    def __init__(self) -> None:
        self.ingests: list[object] = []
        self.dead_letters: list[dict] = []

    def ingest_transaction(self, *, owner: UsersDTO, request: object, **kwargs: object) -> SimpleNamespace:
        self.ingests.append(request)
        return SimpleNamespace(outcome="created")

    def record_dead_letter(self, *, owner: UsersDTO, **kwargs: object) -> dict:
        payload = {"owner": owner, **kwargs}
        self.dead_letters.append(payload)
        return payload


@pytest.fixture(autouse=True)
def _parsers_registered() -> None:
    ensure_parsers_registered()


def test_ensure_parsers_registered_is_idempotent_after_clear() -> None:
    ParserRegistry.clear()
    ensure_parsers_registered()
    assert set(ParserRegistry.all()) >= {"bancolombia-email", "nequi-email", "fallback-email"}
    ensure_parsers_registered()
    assert ParserRegistry.get("bancolombia-email") is BancolombiaParser


@pytest.mark.parametrize(
    ("fixture", "kind", "amount", "merchant_substring"),
    [
        ("bancolombia_income.eml", TransactionKind.INCOME, 20_000.0, "ANA PEREZ"),
        ("bancolombia_transfer.eml", TransactionKind.TRANSFER, 3_000_000.0, "abc@breb.co"),
        ("bancolombia_expense.eml", TransactionKind.EXPENSE, 258_000.0, "CONJUNTO EJEMPLO SA"),
    ],
)
def test_bancolombia_parses_kinds(
    fixture: str,
    kind: TransactionKind,
    amount: float,
    merchant_substring: str,
) -> None:
    record = raw_from_eml(fixture, source_ref=f"bcol-{kind.value}")
    parser = BancolombiaParser()
    assert parser.can_parse(record) is True
    parsed = parser.parse(record)
    assert parsed.transaction_kind == kind
    assert parsed.amount == amount
    assert parsed.currency == "COP"
    assert parsed.source_ref == record.source_ref
    assert merchant_substring in parsed.description
    assert "bancolombia" in parsed.tags
    assert parsed.from_account_id is None
    assert parsed.to_account_id is None
    assert parsed.category_id is None
    assert parsed.transaction_ts is not None


def test_bancolombia_malformed_raises_parse_error() -> None:
    record = raw_from_eml("bancolombia_malformed.eml")
    parser = BancolombiaParser()
    assert parser.can_parse(record) is True
    with pytest.raises(IngestorParseError):
        parser.parse(record)


@pytest.mark.parametrize(
    ("fixture", "kind", "amount"),
    [
        ("nequi_income.eml", TransactionKind.INCOME, 50_000.0),
        ("nequi_expense.eml", TransactionKind.EXPENSE, 25_000.0),
    ],
)
def test_nequi_synthetic_parses(fixture: str, kind: TransactionKind, amount: float) -> None:
    record = raw_from_eml(fixture, source_ref=f"nequi-{kind.value}")
    parser = NequiParser()
    assert parser.can_parse(record) is True
    parsed = parser.parse(record)
    assert parsed.transaction_kind == kind
    assert parsed.amount == amount
    assert parsed.currency == "COP"
    assert parsed.source_ref == record.source_ref
    assert "nequi" in parsed.tags


def test_nequi_rejects_nu_sender() -> None:
    record = raw_from_eml("nequi_income.eml")
    record.metadata["sender"] = "Nu <nu@nu.com.co>"
    assert NequiParser().can_parse(record) is False


def test_registry_priority_prefers_bancolombia_over_fallback() -> None:
    record = raw_from_eml("bancolombia_expense.eml")
    selected = ParserRegistry.select_for(
        record,
        instances=[FallbackEmailParser(), BancolombiaParser(), NequiParser()],
    )
    assert selected.parser_id == "bancolombia-email"


def test_unrecognized_with_fallback_raises_parse_error() -> None:
    record = raw_from_eml("unrecognized.eml")
    selected = ParserRegistry.select_for(
        record,
        instances=[BancolombiaParser(), NequiParser(), FallbackEmailParser()],
    )
    assert selected.parser_id == "fallback-email"
    with pytest.raises(IngestorParseError, match="unrecognized email"):
        selected.parse(record)


def test_unrecognized_without_fallback_raises_lookup_error() -> None:
    record = raw_from_eml("unrecognized.eml")
    with pytest.raises(LookupError):
        ParserRegistry.select_for(record, instances=[BancolombiaParser(), NequiParser()])


def test_runner_unmatched_dead_letters() -> None:
    """AC2: unmatched → LookupError → runner DLQ (no invented ledger write)."""
    record = raw_from_eml("unrecognized.eml", source_ref="unmatched-1")
    bridge = _DlqBridge()
    owner = UsersDTO(
        id=uuid.uuid4(),
        username="ingest_owner",
        email="ingest_owner@example.local",
        password="Password1!",
        auth_provider="local",
    )
    runner = IngestionRunner(
        source=_ListSource([record]),
        owner=owner,
        bridge=bridge,
        parsers=[BancolombiaParser(), NequiParser()],
        settings=BaseIngestorSettings(dry_run=False),
    )
    result = runner.run()
    assert result.fetched == 1
    assert result.dead_lettered == 1
    assert result.failed == 1
    assert bridge.ingests == []
    assert len(bridge.dead_letters) == 1
