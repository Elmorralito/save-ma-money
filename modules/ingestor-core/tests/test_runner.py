"""IngestionRunner persist-then-ack and failure routing."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fakes import FakeBridge, FakeParser, FakeSource, make_owner, make_raw

from papita_ingestor_core.errors.taxonomy import IngestorConnectionError
from papita_ingestor_core.flows.base import build_base_ingestion_flow
from papita_ingestor_core.registry.parsers import ParserRegistry
from papita_ingestor_core.runner.ingestion_runner import IngestionRunner
from papita_ingestor_core.settings.base import BaseIngestorSettings
from papita_ingestor_core.types.records import FetchFilter


def test_runner_happy_path_persist_then_ack() -> None:
    record = make_raw()
    source = FakeSource([record])
    bridge = FakeBridge()
    runner = IngestionRunner(
        source=source,
        owner=make_owner(),
        bridge=bridge,
        parsers=[FakeParser()],
    )
    result = runner.run()
    assert result.fetched == 1
    assert result.created == 1
    assert result.acknowledged == 1
    assert result.failed == 0
    assert len(bridge.ingests) == 1
    assert source.acked == [record]


def test_runner_parse_failure_dead_letters_then_acks() -> None:
    """Poison-message semantics: successful DLQ must ack to stop redelivery."""
    record = make_raw(source_ref="bad")
    source = FakeSource([record])
    bridge = FakeBridge()
    runner = IngestionRunner(
        source=source,
        owner=make_owner(),
        bridge=bridge,
        parsers=[FakeParser(raise_on_parse=True)],
    )
    result = runner.run()
    assert result.failed == 1
    assert result.dead_lettered == 1
    assert result.acknowledged == 1
    assert source.acked == [record]
    assert len(bridge.dead_letters) == 1


def test_runner_incomplete_fk_dead_letters_then_acks() -> None:
    source = FakeSource([make_raw()])
    bridge = FakeBridge()
    runner = IngestionRunner(
        source=source,
        owner=make_owner(),
        bridge=bridge,
        parsers=[FakeParser(incomplete=True)],
    )
    result = runner.run()
    assert result.failed == 1
    assert result.dead_lettered == 1
    assert result.acknowledged == 1


def test_runner_persist_failure_no_ack_no_dlq() -> None:
    source = FakeSource([make_raw()])
    bridge = FakeBridge(fail_persist=True)
    runner = IngestionRunner(
        source=source,
        owner=make_owner(),
        bridge=bridge,
        parsers=[FakeParser()],
    )
    result = runner.run()
    assert result.failed == 1
    assert result.dead_lettered == 0
    assert result.acknowledged == 0
    assert bridge.dead_letters == []


def test_runner_ack_failure_continues_batch() -> None:
    first = make_raw(source_ref="a")
    second = make_raw(source_ref="b")
    source = FakeSource([first, second], fail_ack_refs={"a"})
    bridge = FakeBridge()
    runner = IngestionRunner(
        source=source,
        owner=make_owner(),
        bridge=bridge,
        parsers=[FakeParser()],
    )
    result = runner.run()
    assert result.fetched == 2
    assert result.created == 2
    assert result.acknowledged == 1
    assert result.failed == 1
    assert source.acked == [second]
    assert any(f.error_type == "IngestorAckError" for f in result.failures)


def test_runner_unknown_outcome_no_ack() -> None:
    class WeirdBridge(FakeBridge):
        def ingest_transaction(self, *, owner, request, **kwargs):  # type: ignore[no-untyped-def]
            self.ingests.append({"owner": owner, "request": request})
            return SimpleNamespace(outcome="mystery")

    source = FakeSource([make_raw()])
    runner = IngestionRunner(
        source=source,
        owner=make_owner(),
        bridge=WeirdBridge(),
        parsers=[FakeParser()],
    )
    result = runner.run()
    assert result.failed == 1
    assert result.acknowledged == 0
    assert source.acked == []


def test_runner_requires_source_ref() -> None:
    from papita_ingestor_core.types.records import RawRecord
    from papita_txnsmodel.model.enums import IngestionSource

    bare = RawRecord(source_id="fake-source", source_ref=None, content="x", ingestion_source=IngestionSource.EMAIL)
    source = FakeSource([bare])
    bridge = FakeBridge()
    runner = IngestionRunner(
        source=source,
        owner=make_owner(),
        bridge=bridge,
        parsers=[FakeParser()],
    )
    result = runner.run()
    assert result.failed == 1
    assert result.dead_lettered == 1
    assert result.acknowledged == 1
    assert bridge.ingests == []


def test_runner_dry_run_skips_persist_dlq_ack() -> None:
    source = FakeSource([make_raw(source_ref="ok"), make_raw(source_ref="bad")])
    bridge = FakeBridge()

    class Selective(FakeParser):
        def parse(self, record):  # type: ignore[no-untyped-def]
            if record.source_ref == "bad":
                raise ValueError("nope")
            return super().parse(record)

    runner = IngestionRunner(
        source=source,
        owner=make_owner(),
        bridge=bridge,
        parsers=[Selective()],
        settings=BaseIngestorSettings(dry_run=True),
    )
    result = runner.run()
    assert result.fetched == 2
    assert result.dry_run_skipped == 2
    assert result.created == 0
    assert result.acknowledged == 0
    assert result.dead_lettered == 0
    assert bridge.ingests == []
    assert bridge.dead_letters == []
    assert source.acked == []


def test_runner_fetch_limit_from_settings() -> None:
    records = [make_raw(source_ref=f"m{i}") for i in range(5)]
    source = FakeSource(records)
    bridge = FakeBridge()
    runner = IngestionRunner(
        source=source,
        owner=make_owner(),
        bridge=bridge,
        parsers=[FakeParser()],
        settings=BaseIngestorSettings(fetch_limit=2),
    )
    result = runner.run()
    assert result.fetched == 2
    assert result.created == 2


def test_runner_fetch_filter_limit_wins_over_settings() -> None:
    records = [make_raw(source_ref=f"m{i}") for i in range(5)]
    source = FakeSource(records)
    runner = IngestionRunner(
        source=source,
        owner=make_owner(),
        bridge=FakeBridge(),
        parsers=[FakeParser()],
        settings=BaseIngestorSettings(fetch_limit=2),
    )
    result = runner.run(FetchFilter(limit=3))
    assert result.fetched == 3


def test_runner_empty_parsers_raises() -> None:
    runner = IngestionRunner(
        source=FakeSource([make_raw()]),
        owner=make_owner(),
        bridge=FakeBridge(),
        parsers=[],
    )
    with pytest.raises(ValueError, match="at least one parser"):
        runner.run()


def test_runner_connect_failure_aborts() -> None:
    runner = IngestionRunner(
        source=FakeSource(fail_connect=True),
        owner=make_owner(),
        bridge=FakeBridge(),
        parsers=[FakeParser()],
    )
    with pytest.raises(IngestorConnectionError):
        runner.run()


def test_runner_uses_registry_when_parsers_omitted() -> None:
    @ParserRegistry.register
    class Registered(FakeParser):
        registry_id = "registered-parser"

        def __init__(self) -> None:
            super().__init__()

        @property
        def parser_id(self) -> str:
            return "registered-parser"

    source = FakeSource([make_raw()])
    bridge = FakeBridge()
    runner = IngestionRunner(source=source, owner=make_owner(), bridge=bridge)
    result = runner.run()
    assert result.created == 1
    assert result.acknowledged == 1


def test_build_base_ingestion_flow_requires_prefect_or_runs() -> None:
    """Factory either imports Prefect or raises a clear InstallError."""
    source = FakeSource([make_raw()])
    bridge = FakeBridge()
    owner = make_owner()

    def factory() -> IngestionRunner:
        return IngestionRunner(source=source, owner=owner, bridge=bridge, parsers=[FakeParser()])

    try:
        flow = build_base_ingestion_flow(runner_factory=factory)
    except ImportError as exc:
        assert "prefect" in str(exc).lower()
        return
    result = flow()
    assert result.created == 1
