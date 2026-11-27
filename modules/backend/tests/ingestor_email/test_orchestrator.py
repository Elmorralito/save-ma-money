"""Unit tests for Hatchet email ingestion orchestrator module."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from hatchet_sdk import EmptyModel, NonRetryableException

from papita_ingestor_core.types.records import RunResult
from papita_ingestor_email.flow_settings import EmailFlowSettings
from papita_ingestor_email.orchestrator import (
    EmailIngestInput,
    HatchetEmailIngestionDispatcher,
    build_email_ingest_cron_task,
    build_email_ingest_task,
    parse_email_ingest_input,
    run_orchestrator_worker,
)


class _FakeHatchet:
    def __init__(self) -> None:
        self.registered: list[dict] = []
        self.worker_calls: list[dict] = []
        self.worker_instance = MagicMock()

    def task(self, **kwargs):
        def _decorator(fn):
            self.registered.append({"kwargs": kwargs, "fn": fn})
            return fn

        return _decorator

    def worker(self, **kwargs):
        self.worker_calls.append(kwargs)
        return self.worker_instance


def test_parse_email_ingest_input_defaults_and_invalid() -> None:
    parsed = parse_email_ingest_input({})
    assert parsed.owner_id is None
    assert parsed.dry_run is None

    with pytest.raises(NonRetryableException):
        parse_email_ingest_input({"owner_id": "not-a-uuid"})


def test_build_email_ingest_task_executes_flow_with_overrides() -> None:
    owner_id = uuid.uuid4()
    other_owner_id = uuid.uuid4()
    base_cfg = EmailFlowSettings(owner_id=owner_id, lookback_hours=24, dry_run=False)
    hatchet = _FakeHatchet()
    task_fn = build_email_ingest_task(hatchet, settings=base_cfg)

    captured_deps = []

    def _fake_flow_builder(*, deps):
        captured_deps.append(deps)
        return lambda _f: RunResult(fetched=3, created=2, acknowledged=2)

    with patch("papita_ingestor_email.orchestrator.build_email_ingestion_flow", side_effect=_fake_flow_builder):
        payload = EmptyModel.model_validate({"owner_id": str(other_owner_id), "dry_run": True, "lookback_hours": 12})
        summary = task_fn(payload, MagicMock())

    assert summary == {
        "fetched": 3,
        "created": 2,
        "updated": 0,
        "reactivated": 0,
        "failed": 0,
        "dead_lettered": 0,
        "acknowledged": 2,
        "dry_run_skipped": 0,
    }
    assert captured_deps[0].flow_settings.owner_id == other_owner_id
    assert captured_deps[0].flow_settings.dry_run is True
    assert captured_deps[0].flow_settings.lookback_hours == 12


def test_build_email_ingest_cron_task_registers_cron() -> None:
    cfg = EmailFlowSettings(owner_id=uuid.uuid4(), orchestrator_email_ingest_cron="15 * * * *")
    hatchet = _FakeHatchet()
    build_email_ingest_cron_task(hatchet, settings=cfg)

    assert len(hatchet.registered) == 1
    assert hatchet.registered[0]["kwargs"]["name"] == "email-ingest-cron"
    assert hatchet.registered[0]["kwargs"]["on_crons"] == ["15 * * * *"]


def test_dispatcher_enqueue_and_run() -> None:
    fake_task = MagicMock()
    fake_task.run.side_effect = [
        SimpleNamespace(workflow_run_id="run-123"),
        {"fetched": 1, "created": 1},
    ]
    dispatcher = HatchetEmailIngestionDispatcher(task=fake_task)
    run_id = dispatcher.enqueue_email_ingestion(EmailIngestInput(dry_run=True))
    assert run_id == "run-123"
    result = dispatcher.run_email_ingestion(EmailIngestInput(dry_run=True, lookback_hours=6))
    assert result == {"fetched": 1, "created": 1}
    assert fake_task.run.call_count == 2


def test_run_orchestrator_worker_starts_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPITA_INGESTOR_OWNER_ID", str(uuid.uuid4()))
    fake_hatchet = _FakeHatchet()
    with patch("papita_ingestor_email.orchestrator.Hatchet", return_value=fake_hatchet):
        rc = run_orchestrator_worker(slots=2, skip_env_file=True)

    assert rc == 0
    assert len(fake_hatchet.worker_calls) == 1
    assert fake_hatchet.worker_calls[0]["name"] == "papita-ingestor-email"
    assert fake_hatchet.worker_calls[0]["slots"] == 2
    assert len(fake_hatchet.worker_calls[0]["workflows"]) == 2
    fake_hatchet.worker_instance.start.assert_called_once()
