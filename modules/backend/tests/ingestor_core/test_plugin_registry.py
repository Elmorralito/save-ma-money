"""Unit and contract tests for the plugin-based connector architecture."""

from __future__ import annotations

import ast
import uuid
from collections.abc import Iterable, Sequence
from pathlib import Path

import pytest

from papita_ingestor_core.errors import IngestorParseError, IngestorPluginError
from papita_ingestor_core.importers.base import BaseBatchImporter
from papita_ingestor_core.importers.ibkr import IBKRStatementImporter
from papita_ingestor_core.parsers.base import BaseRecordParser, select_parser
from papita_ingestor_core.registry import ConnectorRegistry, get_default_registry, reset_default_registry
from papita_ingestor_core.runner.ingestion_runner import IngestionRunner
from papita_ingestor_core.sources.base import BaseIngestorSource
from papita_ingestor_core.types.records import FetchFilter, ParsedRecord, RawRecord
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import IngestionSource, TransactionKind
from papita_txnsmodel.services.portfolio_import import NormalizedPortfolioBatch


class _DummySource(BaseIngestorSource):
    def __init__(self, records: list[RawRecord] | None = None) -> None:
        self._records = records or []
        self.connected = False
        self.acked: list[str] = []

    @property
    def source_id(self) -> str:
        return "dummy-source"

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def fetch(self, fetch_filter: FetchFilter | None = None) -> Iterable[RawRecord]:
        yield from self._records

    def acknowledge(self, record: RawRecord) -> None:
        if record.source_ref:
            self.acked.append(record.source_ref)


class _MultiRecordParser(BaseRecordParser):
    @property
    def parser_id(self) -> str:
        return "multi-record"

    @property
    def priority(self) -> int:
        return 50

    @property
    def supported_source_ids(self) -> frozenset[str]:
        return frozenset({"dummy-source"})

    def can_parse(self, record: RawRecord) -> bool:
        return True

    def parse(self, record: RawRecord) -> ParsedRecord:
        return ParsedRecord(
            ingestion_source=IngestionSource.API,
            source_ref=f"{record.source_ref}:0",
            transaction_kind=TransactionKind.EXPENSE,
            amount=10.0,
            currency="USD",
            from_account_id=uuid.uuid4(),
            category_id=uuid.uuid4(),
        )

    def parse_many(self, record: RawRecord) -> Sequence[ParsedRecord]:
        return [
            ParsedRecord(
                ingestion_source=IngestionSource.API,
                source_ref=f"{record.source_ref}:0",
                transaction_kind=TransactionKind.EXPENSE,
                amount=10.0,
                currency="USD",
                from_account_id=uuid.uuid4(),
                category_id=uuid.uuid4(),
            ),
            ParsedRecord(
                ingestion_source=IngestionSource.API,
                source_ref=f"{record.source_ref}:1",
                transaction_kind=TransactionKind.INCOME,
                amount=25.0,
                currency="USD",
                to_account_id=uuid.uuid4(),
                category_id=uuid.uuid4(),
            ),
        ]


class _FakeBridge:
    def __init__(self) -> None:
        self.requests: list[object] = []

    def ingest_transaction(self, *, owner: UsersDTO, request: object) -> object:
        self.requests.append(request)
        return type("_Res", (), {"outcome": "created"})()

    def record_dead_letter(self, **kwargs: object) -> None:
        raise AssertionError(f"Unexpected DLQ call: {kwargs}")


def test_default_registry_discovers_builtin_plugins_without_env_secrets() -> None:
    reset_default_registry()
    registry = get_default_registry()

    assert "gmail" in registry.source_ids()
    assert set(registry.parser_ids()) >= {
        "bancolombia-email",
        "global66-email",
        "nequi-email",
        "fallback-email",
    }
    assert "ibkr-activity-csv" in registry.importer_ids()

    manifests = registry.list_manifests()
    assert any(m.plugin_id == "gmail" and m.kind == "pull_source" for m in manifests)
    assert any(m.plugin_id == "ibkr-activity-csv" and m.kind == "batch_importer" for m in manifests)


def test_registry_duplicate_and_unknown_plugin_errors() -> None:
    reg = ConnectorRegistry()
    reg.register_source("dummy", _DummySource)
    with pytest.raises(IngestorPluginError, match="Duplicate"):
        reg.register_source("dummy", _DummySource)

    reg.register_source("dummy", _DummySource, replace=True)
    with pytest.raises(IngestorPluginError, match="Unknown"):
        reg.get_source("nonexistent")


def test_registry_parser_priority_and_source_scoping() -> None:
    reg = ConnectorRegistry()
    reg.register_parser("multi-record", _MultiRecordParser)
    assert [p.parser_id for p in reg.get_parsers(source_id="dummy-source")] == ["multi-record"]
    assert reg.get_parsers(source_id="other-source") == []

    wrong_record = RawRecord(
        source_id="other-source", source_ref="r1", content="x", ingestion_source=IngestionSource.API
    )
    with pytest.raises(LookupError):
        select_parser(wrong_record, [_MultiRecordParser()])


def test_runner_supports_parse_many_and_public_resolve_owner() -> None:
    owner = UsersDTO.model_construct(id=uuid.uuid4(), username="owner01", email="owner@example.com")
    record = RawRecord(
        source_id="dummy-source", source_ref="batch-1", content="payload", ingestion_source=IngestionSource.API
    )
    source = _DummySource([record])
    bridge = _FakeBridge()
    runner = IngestionRunner(source=source, owner=owner, bridge=bridge, parsers=[_MultiRecordParser()])

    assert runner.resolve_owner().id == owner.id
    result = runner.run()
    assert result.fetched == 1
    assert result.created == 2
    assert result.acknowledged == 1
    assert len(bridge.requests) == 2


def test_ibkr_statement_importer_contract() -> None:
    importer = IBKRStatementImporter()
    assert isinstance(importer, BaseBatchImporter)
    assert importer.importer_id == "ibkr-activity-csv"
    assert importer.can_import(filename="U12345_IBKR_2026.csv") is True
    assert importer.can_import(sample="Open Positions,Header,DataDiscriminator,Symbol\n") is True
    assert importer.can_import(filename="random.txt", sample="hello world") is False

    sample_csv = "\n".join(
        [
            "Statement,Header,Field Name,Field Value",
            "Statement,Data,Period,November 1, 2026 - November 23, 2026",
            "Account Information,Header,Field Name,Field Value",
            "Account Information,Data,Account,U9999999",
            "Open Positions,Header,DataDiscriminator,Asset Category,Currency,Symbol,Quantity,Cost Price,Close Price,Value,Unrealized P/L",
            "Open Positions,Data,Summary,Stocks,USD,VOO,2.5,450.0,500.0,1250.0,125.0",
        ]
    )
    batch = importer.parse_statement(sample_csv)
    assert isinstance(batch, NormalizedPortfolioBatch)
    assert batch.provider_id == "ibkr-activity-csv"
    assert batch.account_code == "U9999999"
    assert len(batch.positions) == 1
    assert batch.positions[0].symbol == "VOO"

    with pytest.raises(IngestorParseError):
        importer.parse_statement("")


def test_portfolio_import_service_has_no_ingestor_imports() -> None:
    """Enforce layering: papita_txnsmodel.services.portfolio_import must not import papita_ingestor_*."""
    path = Path(__file__).resolve().parents[2] / "src/papita_txnsmodel/services/portfolio_import.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("papita_ingestor")
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("papita_ingestor")


def test_registry_caches_manifests_and_respects_class_level_manifest() -> None:
    calls = 0

    def _counting_factory() -> _DummySource:
        nonlocal calls
        calls += 1
        return _DummySource()

    reg = ConnectorRegistry()
    reg.register_source("counted", _counting_factory)

    first = reg.list_manifests(kind="pull_source")
    second = reg.list_manifests(kind="pull_source")
    assert len(first) == 1
    assert first == second
    assert calls == 1  # cached after first resolution

    reg.register_source("counted", _counting_factory, replace=True)
    reg.list_manifests(kind="pull_source")
    assert calls == 2  # invalidated on replace


def test_all_builtin_plugins_satisfy_contracts() -> None:
    """Contract sweep over every built-in source, parser, and importer in the default registry."""
    reset_default_registry()
    reg = get_default_registry()

    for source_id in reg.source_ids():
        src = reg.get_source(source_id)
        assert isinstance(src, BaseIngestorSource)
        assert src.source_id == source_id
        assert src.manifest.plugin_id == source_id
        assert src.manifest.kind == "pull_source"

    parsers = reg.get_parsers()
    assert len(parsers) >= 4
    priorities = [p.priority for p in parsers]
    assert priorities == sorted(priorities, reverse=True)
    for parser in parsers:
        assert isinstance(parser, BaseRecordParser)
        assert parser.manifest.plugin_id == parser.parser_id
        assert parser.manifest.kind == "record_parser"

    for importer_id in reg.importer_ids():
        imp = reg.get_importer(importer_id)
        assert isinstance(imp, BaseBatchImporter)
        assert imp.importer_id == importer_id
        assert imp.manifest.plugin_id == importer_id
        assert imp.manifest.kind == "batch_importer"


def test_registry_entry_points_allowlist_and_resolve_importer(monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.domains.ingestion as ingestion_domain
    from papita_ingestor_core import registry as registry_mod

    assert ingestion_domain.get_default_registry is get_default_registry

    class _FakeEP:
        def __init__(self, name: str, obj: object, *, fail: bool = False) -> None:
            self.name = name
            self._obj = obj
            self._fail = fail

        def load(self) -> object:
            if self._fail:
                raise RuntimeError("boom")
            return self._obj

    def _fake_entry_points(*, group: str) -> list[_FakeEP]:
        if group == registry_mod.SOURCES_EP_GROUP:
            return [_FakeEP("ep-src", _DummySource), _FakeEP("broken-src", _DummySource, fail=True)]
        if group == registry_mod.IMPORTERS_EP_GROUP:
            return [_FakeEP("ibkr-activity-csv", IBKRStatementImporter)]
        return []

    monkeypatch.setattr(registry_mod.metadata, "entry_points", _fake_entry_points)
    reg = ConnectorRegistry()
    loaded = reg.discover_entry_points(allowlist={"ep-src", "ibkr-activity-csv"})
    assert loaded == 2
    assert reg.source_ids() == ["ep-src"]

    resolved = reg.resolve_importer(filename="U123_ibkr.csv")
    assert resolved.importer_id == "ibkr-activity-csv"
    with pytest.raises(IngestorPluginError, match="No batch importer"):
        reg.resolve_importer(filename="unknown.txt", sample="nope")
    with pytest.raises(IngestorPluginError, match="Empty plugin_id"):
        reg.register_source("   ", _DummySource)
    with pytest.raises(IngestorPluginError, match="Unknown batch_importer"):
        reg.get_importer("does-not-exist")


def test_core_execute_with_run_status_handles_failures_and_errors() -> None:
    from unittest.mock import MagicMock

    from papita_ingestor_core.run_status import execute_with_run_status
    from papita_txnsmodel.model.enums import IngestionRunStatus

    owner = UsersDTO.model_construct(id=uuid.uuid4(), username="owner01", email="owner@example.com")
    source = _DummySource([])
    runner = IngestionRunner(source=source, owner=owner, bridge=_FakeBridge(), parsers=[_MultiRecordParser()])
    assert runner.source_id == "dummy-source"

    dry = execute_with_run_status(
        runner,
        None,
        provider="dummy-source",
        flow_name="test-flow",
        deployment_name=None,
        persist_status=False,
    )
    assert dry.fetched == 0

    conn_svc = MagicMock()
    conn_svc.upsert_connection.return_value = type("_Conn", (), {"id": uuid.uuid4()})()
    run_svc = MagicMock()
    run_svc.start_run.return_value = type("_Run", (), {"id": uuid.uuid4()})()
    run_svc.finish_run.side_effect = RuntimeError("db glitch")

    execute_with_run_status(
        runner,
        None,
        provider="dummy-source",
        flow_name="test-flow",
        deployment_name="dep",
        connection_service=conn_svc,
        run_service=run_svc,
    )
    run_svc.finish_run.assert_called_once()

    failing_runner = MagicMock()
    failing_runner.resolve_owner.return_value = owner
    failing_runner.run.side_effect = RuntimeError("fetch boom")
    run_svc2 = MagicMock()
    run_svc2.start_run.return_value = type("_Run", (), {"id": uuid.uuid4()})()
    with pytest.raises(RuntimeError, match="fetch boom"):
        execute_with_run_status(
            failing_runner,
            None,
            provider="dummy-source",
            flow_name="test-flow",
            deployment_name=None,
            connection_service=conn_svc,
            run_service=run_svc2,
        )
    req = run_svc2.finish_run.call_args.kwargs["request"]
    assert req.status == IngestionRunStatus.FAILED
    assert req.error_summary == "RuntimeError"
    assert "fetch boom" not in (req.error_summary or "")
