"""Email Prefect flow wiring (PPT-082 / #176) — mocked source/bridge; H1=B FK disposition."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from papita_ingestor_core.parsers.base import BaseRecordParser
from papita_ingestor_core.sources.base import BaseIngestorSource
from papita_ingestor_core.types.records import FetchFilter, ParsedRecord, RawRecord
from papita_ingestor_email.flow_settings import EmailFlowSettings
from papita_ingestor_email.flows.email_flow import build_email_ingestion_flow, build_email_runner, default_fetch_filter
from papita_ingestor_email.owner import users_dto_for_owner_id
from papita_ingestor_email.wiring import EmailFlowDeps
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import IngestionSource, TransactionKind

pytest.importorskip("prefect")


@pytest.fixture(scope="module", autouse=True)
def _prefect_harness():
    """Use Prefect test harness to avoid ephemeral API shutdown log noise."""
    from prefect.testing.utilities import prefect_test_harness

    with prefect_test_harness():
        yield


class _FakeBridge:
    def __init__(self) -> None:
        self.ingests: list[dict] = []
        self.dead_letters: list[dict] = []

    def ingest_transaction(self, *, owner: UsersDTO, request: object, **kwargs: object) -> object:
        self.ingests.append({"owner": owner, "request": request, "kwargs": kwargs})
        return SimpleNamespace(outcome="created", transaction=None, provenance=None)

    def record_dead_letter(self, *, owner: UsersDTO, **kwargs: object) -> dict:
        payload = {"owner": owner, **kwargs}
        self.dead_letters.append(payload)
        return payload


class _FakeSource(BaseIngestorSource):
    registry_id = "fake-gmail"

    def __init__(self, records: list[RawRecord]) -> None:
        self._records = list(records)
        self.acked: list[RawRecord] = []
        self.last_filter: FetchFilter | None = None

    @property
    def source_id(self) -> str:
        return self.registry_id

    def connect(self) -> None:
        return None

    def disconnect(self) -> None:
        return None

    def fetch(self, fetch_filter: FetchFilter | None = None) -> list[RawRecord]:
        self.last_filter = fetch_filter
        records = list(self._records)
        if fetch_filter is not None and fetch_filter.limit is not None:
            records = records[: fetch_filter.limit]
        return records

    def acknowledge(self, record: RawRecord) -> None:
        self.acked.append(record)


class _CompleteFkParser(BaseRecordParser):
    """Injects complete FKs (H1=B) so persist path can be asserted without live enricher."""

    registry_id = "test-complete-fk"

    def __init__(self) -> None:
        self._from_account_id = uuid.uuid4()
        self._category_id = uuid.uuid4()

    @property
    def parser_id(self) -> str:
        return self.registry_id

    @property
    def priority(self) -> int:
        return 1000

    def can_parse(self, record: RawRecord) -> bool:
        return True

    def parse(self, record: RawRecord) -> ParsedRecord:
        return ParsedRecord(
            ingestion_source=record.ingestion_source,
            source_ref=record.source_ref,
            transaction_kind=TransactionKind.EXPENSE,
            amount=25.0,
            currency="COP",
            from_account_id=self._from_account_id,
            to_account_id=None,
            category_id=self._category_id,
            description="fk-injected",
        )


class _IncompleteFkParser(BaseRecordParser):
    """Mirrors bank parsers: FKs left None → validation → DLQ-then-ack."""

    registry_id = "test-incomplete-fk"

    @property
    def parser_id(self) -> str:
        return self.registry_id

    @property
    def priority(self) -> int:
        return 1000

    def can_parse(self, record: RawRecord) -> bool:
        return True

    def parse(self, record: RawRecord) -> ParsedRecord:
        return ParsedRecord(
            ingestion_source=record.ingestion_source,
            source_ref=record.source_ref,
            transaction_kind=TransactionKind.EXPENSE,
            amount=10.0,
            currency="COP",
            from_account_id=None,
            to_account_id=None,
            category_id=None,
            description="no-fks",
        )


def _raw(ref: str = "msg-1") -> RawRecord:
    return RawRecord(
        source_id="fake-gmail",
        source_ref=ref,
        content=b"opaque",
        ingestion_source=IngestionSource.EMAIL,
    )


def test_users_dto_for_owner_id_uses_env_uuid_only() -> None:
    owner_id = uuid.uuid4()
    owner = users_dto_for_owner_id(owner_id)
    assert owner.id == owner_id
    assert owner.email == "ingest_owner@local.invalid"
    assert owner.password is None


def test_default_fetch_filter_lookback_only_sets_since() -> None:
    settings = EmailFlowSettings(
        owner_id=uuid.uuid4(),
        lookback_hours=2,
        fetch_limit=5,
    )
    filt = default_fetch_filter(settings)
    assert filt.limit is None  # runner applies settings.fetch_limit
    assert filt.since is not None
    assert filt.since <= datetime.now(timezone.utc)


def test_runner_incomplete_fks_dead_letter_then_ack() -> None:
    """H1=B: missing FKs DLQ then ack — no live upsert claim."""
    bridge = _FakeBridge()
    source = _FakeSource([_raw("poison-1")])
    owner_id = uuid.uuid4()
    settings = EmailFlowSettings(owner_id=owner_id)
    runner = build_email_runner(
        EmailFlowDeps(
            flow_settings=settings,
            source=source,
            bridge=bridge,
            owner=users_dto_for_owner_id(owner_id),
        )
    )
    runner._parsers = [_IncompleteFkParser()]  # noqa: SLF001 — test seam
    result = runner.run()
    assert result.fetched == 1
    assert result.created == 0
    assert bridge.ingests == []
    assert len(bridge.dead_letters) == 1
    assert len(source.acked) == 1
    assert source.acked[0].source_ref == "poison-1"


def test_email_flow_applies_lookback_and_persists_injected_fks() -> None:
    """``build_email_ingestion_flow`` applies lookback and calls bridge when FKs injected."""
    bridge = _FakeBridge()
    source = _FakeSource([_raw("ok-1")])
    owner_id = uuid.uuid4()
    settings = EmailFlowSettings(owner_id=owner_id, flow_retries=0, lookback_hours=3, fetch_limit=7)

    import papita_ingestor_email.flows.email_flow as email_flow_mod

    real_build = email_flow_mod.build_email_runner

    def _wrap_build_runner(deps=None):
        runner = real_build(deps)
        runner._parsers = [_CompleteFkParser()]  # noqa: SLF001
        return runner

    with patch.object(email_flow_mod, "build_email_runner", side_effect=_wrap_build_runner):
        flow_fn = email_flow_mod.build_email_ingestion_flow(
            deps=EmailFlowDeps(
                flow_settings=settings,
                source=source,
                bridge=bridge,
                owner=users_dto_for_owner_id(owner_id),
                establish_db=False,
                verify_owner=False,
                persist_status=False,
            )
        )
        result = flow_fn()

    assert result.fetched == 1
    assert result.created == 1
    assert len(bridge.ingests) == 1
    assert bridge.ingests[0]["owner"].id == owner_id
    assert source.last_filter is not None
    assert source.last_filter.limit == 7  # merged from settings by runner
    assert source.last_filter.since is not None


class _FakeConnectionService:
    def __init__(self) -> None:
        self.upserts: list[dict] = []

    def upsert_connection(self, *, owner: UsersDTO, request: object, **kwargs: object) -> object:
        self.upserts.append({"owner": owner, "request": request, "kwargs": kwargs})
        return SimpleNamespace(id=uuid.uuid4())


class _FakeRunService:
    def __init__(self) -> None:
        self.starts: list[dict] = []
        self.finishes: list[dict] = []
        self._run_id = uuid.uuid4()

    def start_run(self, *, owner: UsersDTO, **kwargs: object) -> object:
        self.starts.append({"owner": owner, **kwargs})
        return SimpleNamespace(id=self._run_id)

    def finish_run(self, *, owner: UsersDTO, run_id: uuid.UUID, request: object, **kwargs: object) -> object:
        self.finishes.append({"owner": owner, "run_id": run_id, "request": request, "kwargs": kwargs})
        return SimpleNamespace(id=run_id, status=getattr(request, "status", None))


def test_email_flow_persists_connection_and_run_status() -> None:
    """PPT-083: upsert connection + start/finish run around runner (allowlisted fields only)."""
    bridge = _FakeBridge()
    source = _FakeSource([_raw("ok-status-1")])
    owner_id = uuid.uuid4()
    settings = EmailFlowSettings(owner_id=owner_id, flow_retries=0, lookback_hours=6)
    conn_svc = _FakeConnectionService()
    run_svc = _FakeRunService()

    import papita_ingestor_email.flows.email_flow as email_flow_mod

    real_build = email_flow_mod.build_email_runner

    def _wrap_build_runner(deps=None):
        runner = real_build(deps)
        runner._parsers = [_CompleteFkParser()]  # noqa: SLF001
        return runner

    with patch.object(email_flow_mod, "build_email_runner", side_effect=_wrap_build_runner):
        flow_fn = email_flow_mod.build_email_ingestion_flow(
            deps=EmailFlowDeps(
                flow_settings=settings,
                source=source,
                bridge=bridge,
                owner=users_dto_for_owner_id(owner_id),
                establish_db=False,
                verify_owner=False,
                connection_service=conn_svc,
                run_service=run_svc,
                persist_status=True,
            )
        )
        result = flow_fn()

    assert result.created == 1
    assert len(conn_svc.upserts) == 1
    upsert_req = conn_svc.upserts[0]["request"]
    assert upsert_req.provider == "email"
    assert upsert_req.flow_name == "papita-email-ingestion"
    assert upsert_req.deployment_name == "papita-email-ingestion-hourly"
    assert upsert_req.lookback_hours == 6
    assert not hasattr(upsert_req, "client_secret")
    assert not hasattr(upsert_req, "refresh_token")
    assert len(run_svc.starts) == 1
    assert len(run_svc.finishes) == 1
    finish_req = run_svc.finishes[0]["request"]
    assert finish_req.fetched == 1
    assert finish_req.created == 1
    assert finish_req.status.value == "SUCCEEDED"


def test_serve_email_ingestion_propagates_deployment_name_to_deps() -> None:
    """Serve arg must win for status persistence (PPT-083 audit fix)."""
    import papita_ingestor_email.flows.email_flow as email_flow_mod

    captured: dict[str, object] = {}

    def _fake_build_flow(*, deps=None, name=None):
        captured["deps"] = deps
        flow = MagicMock()
        flow.serve = MagicMock()
        captured["flow"] = flow
        return flow

    settings = EmailFlowSettings(owner_id=uuid.uuid4(), schedule_interval_minutes=15)
    with patch.object(email_flow_mod, "build_email_ingestion_flow", side_effect=_fake_build_flow):
        email_flow_mod.serve_email_ingestion(
            deps=EmailFlowDeps(flow_settings=settings, deployment_name="stale-name"),
            deployment_name="custom-hourly",
            webserver=False,
        )

    deps = captured["deps"]
    assert deps is not None
    assert deps.deployment_name == "custom-hourly"
    captured["flow"].serve.assert_called_once()
    assert captured["flow"].serve.call_args.kwargs["name"] == "custom-hourly"


def test_email_flow_skips_status_persist_when_dry_run() -> None:
    bridge = _FakeBridge()
    source = _FakeSource([_raw("dry-1")])
    owner_id = uuid.uuid4()
    settings = EmailFlowSettings(owner_id=owner_id, flow_retries=0, dry_run=True)
    conn_svc = _FakeConnectionService()
    run_svc = _FakeRunService()

    import papita_ingestor_email.flows.email_flow as email_flow_mod

    real_build = email_flow_mod.build_email_runner

    def _wrap_build_runner(deps=None):
        runner = real_build(deps)
        runner._parsers = [_CompleteFkParser()]  # noqa: SLF001
        return runner

    with patch.object(email_flow_mod, "build_email_runner", side_effect=_wrap_build_runner):
        flow_fn = email_flow_mod.build_email_ingestion_flow(
            deps=EmailFlowDeps(
                flow_settings=settings,
                source=source,
                bridge=bridge,
                owner=users_dto_for_owner_id(owner_id),
                establish_db=False,
                verify_owner=False,
                connection_service=conn_svc,
                run_service=run_svc,
            )
        )
        result = flow_fn()

    assert result.dry_run_skipped == 1
    assert conn_svc.upserts == []
    assert run_svc.starts == []
    assert run_svc.finishes == []


def test_real_bridge_path_establishes_database_and_verifies_owner() -> None:
    """Default bridge wiring establishes DB and verifies owner exists."""
    owner_id = uuid.uuid4()
    settings = EmailFlowSettings(owner_id=owner_id, dry_run=False)
    db_owner = users_dto_for_owner_id(owner_id)
    with (
        patch("papita_ingestor_email.flows.email_flow.IngestionBridgeService") as bridge_cls,
        patch("papita_ingestor_email.flows.email_flow.establish_database_from_env") as establish,
        patch("papita_ingestor_email.flows.email_flow.require_owner_in_database", return_value=db_owner) as verify,
        patch("papita_ingestor_email.flows.email_flow.GmailSource") as gmail_cls,
    ):
        gmail_cls.return_value = _FakeSource([])
        bridge_cls.return_value = _FakeBridge()
        build_email_runner(EmailFlowDeps(flow_settings=settings))
        establish.assert_called_once_with(require=True)
        verify.assert_called_once_with(owner_id)
