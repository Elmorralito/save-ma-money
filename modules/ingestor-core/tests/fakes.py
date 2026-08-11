"""Reusable fakes for papita_ingestor_core unit tests."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from types import SimpleNamespace
from typing import Any

from papita_ingestor_core.parsers.base import BaseRecordParser
from papita_ingestor_core.sources.base import BaseIngestorSource
from papita_ingestor_core.types.records import FetchFilter, ParsedRecord, RawRecord
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import IngestionSource, TransactionKind


def make_owner() -> UsersDTO:
    """Minimal trusted owner for runner tests."""
    return UsersDTO(
        id=uuid.uuid4(),
        username="ingest_owner",
        email="ingest_owner@example.local",
        password="Password1!",
        auth_provider="local",
    )


class FakeBridge:
    """In-memory stand-in for ``IngestionBridgeService``."""

    def __init__(self, *, fail_persist: bool = False, fail_dead_letter: bool = False) -> None:
        self.fail_persist = fail_persist
        self.fail_dead_letter = fail_dead_letter
        self.ingests: list[Any] = []
        self.dead_letters: list[dict[str, Any]] = []

    def ingest_transaction(self, *, owner: UsersDTO, request: Any, **kwargs: Any) -> Any:
        if self.fail_persist:
            raise RuntimeError("bridge persist failed")
        self.ingests.append({"owner": owner, "request": request, "kwargs": kwargs})
        return SimpleNamespace(outcome="created", transaction=None, provenance=None)

    def record_dead_letter(self, *, owner: UsersDTO, **kwargs: Any) -> Any:
        if self.fail_dead_letter:
            raise RuntimeError("dlq failed")
        payload = {"owner": owner, **kwargs}
        self.dead_letters.append(payload)
        return payload


class FakeSource(BaseIngestorSource):
    """Deterministic source for runner tests."""

    registry_id = "fake-source"

    def __init__(
        self,
        records: list[RawRecord] | None = None,
        *,
        fail_connect: bool = False,
        fail_ack_refs: set[str] | None = None,
    ) -> None:
        self._records = list(records or [])
        self.fail_connect = fail_connect
        self.fail_ack_refs = set(fail_ack_refs or ())
        self.connected = False
        self.acked: list[RawRecord] = []

    @property
    def source_id(self) -> str:
        return self.registry_id

    def connect(self) -> None:
        if self.fail_connect:
            raise ConnectionError("cannot connect")
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def fetch(self, fetch_filter: FetchFilter | None = None) -> Iterable[RawRecord]:
        records = list(self._records)
        if fetch_filter is not None and fetch_filter.limit is not None:
            records = records[: fetch_filter.limit]
        return records

    def acknowledge(self, record: RawRecord) -> None:
        if record.source_ref in self.fail_ack_refs:
            raise RuntimeError(f"ack failed for {record.source_ref}")
        self.acked.append(record)


class FakeParser(BaseRecordParser):
    """Parser that accepts any record and emits a complete EXPENSE ParsedRecord."""

    registry_id = "fake-parser"

    def __init__(
        self,
        *,
        from_account_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        incomplete: bool = False,
        raise_on_parse: bool = False,
        priority_value: int = 10,
    ) -> None:
        self._from_account_id = from_account_id or uuid.uuid4()
        self._category_id = category_id or uuid.uuid4()
        self._incomplete = incomplete
        self._raise_on_parse = raise_on_parse
        self._priority_value = priority_value

    @property
    def parser_id(self) -> str:
        return self.registry_id

    @property
    def priority(self) -> int:
        return self._priority_value

    def can_parse(self, record: RawRecord) -> bool:
        return True

    def parse(self, record: RawRecord) -> ParsedRecord:
        if self._raise_on_parse:
            raise ValueError("boom parse")
        return ParsedRecord(
            ingestion_source=record.ingestion_source,
            source_ref=record.source_ref,
            transaction_kind=TransactionKind.EXPENSE,
            amount=12.5,
            from_account_id=None if self._incomplete else self._from_account_id,
            to_account_id=None,
            category_id=None if self._incomplete else self._category_id,
            description="fake expense",
        )


def make_raw(*, source_ref: str = "msg-1", content: str | bytes = "opaque") -> RawRecord:
    """Build a minimal RawRecord."""
    return RawRecord(
        source_id="fake-source",
        source_ref=source_ref,
        content=content,
        ingestion_source=IngestionSource.EMAIL,
    )
