"""Hatchet orchestrator tasks, dispatcher, and worker entrypoint for email ingestion."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any
from uuid import UUID

from hatchet_sdk import (
    ConcurrencyExpression,
    ConcurrencyLimitStrategy,
    Context,
    EmptyModel,
    Hatchet,
    NonRetryableException,
)
from pydantic import BaseModel, ValidationError

from papita_ingestor_core.types.records import RunResult
from papita_ingestor_email.flow_settings import EmailFlowSettings
from papita_ingestor_email.flows.email_flow import build_email_ingestion_flow
from papita_ingestor_email.runtime import load_environment_file
from papita_ingestor_email.wiring import EmailFlowDeps

logger = logging.getLogger(__name__)

_INGEST_CONCURRENCY = ConcurrencyExpression(
    expression="'constant'",
    max_runs=1,
    limit_strategy=ConcurrencyLimitStrategy.CANCEL_NEWEST,
)


class EmailIngestInput(BaseModel):
    """Optional overrides for an on-demand ``email-ingest`` Hatchet run."""

    owner_id: UUID | None = None
    lookback_hours: int | None = None
    dry_run: bool | None = None
    senders: list[str] | None = None
    subjects: list[str] | None = None
    source_label: str | None = None
    query: str | None = None


def parse_email_ingest_input(raw: Any) -> EmailIngestInput:
    """Validate task input; malformed payloads must not retry."""
    try:
        if isinstance(raw, EmailIngestInput):
            return raw
        return EmailIngestInput.model_validate(raw or {})
    except ValidationError as exc:
        raise NonRetryableException("email-ingest received invalid input payload") from exc


def _settings_with_overrides(base: EmailFlowSettings, payload: EmailIngestInput) -> EmailFlowSettings:
    """Apply non-None payload overrides onto ``EmailFlowSettings``."""
    updates: dict[str, object] = {}
    if payload.owner_id is not None:
        updates["owner_id"] = payload.owner_id
    if payload.lookback_hours is not None:
        updates["lookback_hours"] = payload.lookback_hours
    if payload.dry_run is not None:
        updates["dry_run"] = payload.dry_run
    if payload.senders is not None:
        updates["email_senders"] = payload.senders
    if payload.subjects is not None:
        updates["email_subjects"] = payload.subjects
    if payload.source_label is not None:
        updates["email_source_label"] = payload.source_label
    if payload.query is not None:
        updates["email_query"] = payload.query
    if not updates:
        return base
    return base.model_copy(update=updates)


def _run_result_summary(result: RunResult) -> dict[str, int]:
    """Serialize ``RunResult`` counters for Hatchet task output."""
    return {
        "fetched": result.fetched,
        "created": result.created,
        "updated": result.updated,
        "reactivated": result.reactivated,
        "failed": result.failed,
        "dead_lettered": result.dead_lettered,
        "acknowledged": result.acknowledged,
        "dry_run_skipped": result.dry_run_skipped,
    }


def build_email_ingest_task(hatchet: Any, *, settings: EmailFlowSettings | None = None) -> Any:
    """Register the on-demand ``email-ingest`` task on a Hatchet client."""
    base_cfg = settings or EmailFlowSettings()

    @hatchet.task(
        name="email-ingest",
        concurrency=_INGEST_CONCURRENCY,
        execution_timeout=timedelta(minutes=15),
        schedule_timeout=timedelta(minutes=10),
        retries=2,
        backoff_factor=2.0,
        backoff_max_seconds=120,
    )
    def email_ingest(payload: EmptyModel, ctx: Context) -> dict[str, int]:
        """Fetch, parse, and persist (or dry-run) Gmail messages for the configured owner."""
        del ctx
        parsed = parse_email_ingest_input(payload.model_dump())
        effective = _settings_with_overrides(base_cfg, parsed)
        flow_fn = build_email_ingestion_flow(deps=EmailFlowDeps(flow_settings=effective))
        result = flow_fn(None)
        summary = _run_result_summary(result)
        logger.info("orchestrator email-ingest done %s", summary)
        return summary

    return email_ingest


def build_email_ingest_cron_task(hatchet: Any, *, settings: EmailFlowSettings | None = None) -> Any:
    """Register the scheduled ``email-ingest-cron`` task on a Hatchet client."""
    cfg = settings or EmailFlowSettings()

    @hatchet.task(
        name="email-ingest-cron",
        on_crons=[cfg.orchestrator_email_ingest_cron],
        concurrency=_INGEST_CONCURRENCY,
        execution_timeout=timedelta(minutes=15),
        schedule_timeout=timedelta(minutes=10),
        retries=1,
    )
    def email_ingest_cron(payload: EmptyModel, ctx: Context) -> dict[str, int]:
        """Scheduled Gmail ingestion pass."""
        del payload, ctx
        flow_fn = build_email_ingestion_flow(deps=EmailFlowDeps(flow_settings=cfg))
        result = flow_fn(None)
        summary = _run_result_summary(result)
        logger.info("orchestrator email-ingest-cron done %s", summary)
        return summary

    return email_ingest_cron


class _TaskHolder:
    """Lazy singleton for the default Hatchet task (avoids module-level ``global``)."""

    task: Any | None = None


def _default_task() -> Any:
    if _TaskHolder.task is None:
        _TaskHolder.task = build_email_ingest_task(Hatchet())
    return _TaskHolder.task


class HatchetEmailIngestionDispatcher:
    """Trigger ``email-ingest`` via ``hatchet-sdk`` (requires ``HATCHET_CLIENT_TOKEN``)."""

    def __init__(self, *, task: Any | None = None) -> None:
        self._task = task

    def enqueue_email_ingestion(self, payload: EmailIngestInput | None = None) -> str | None:
        """Fire-and-forget an ``email-ingest`` run and return its workflow run id if available."""
        task = self._task if self._task is not None else _default_task()
        model = payload or EmailIngestInput()
        ref = task.run(model.model_dump(mode="json", exclude_none=True), wait_for_result=False)
        run_id = getattr(ref, "workflow_run_id", None) or getattr(ref, "run_id", None)
        logger.info("enqueued hatchet email-ingest run_id=%s", run_id)
        return str(run_id) if run_id is not None else None

    def run_email_ingestion(self, payload: EmailIngestInput | None = None) -> dict[str, Any]:
        """Trigger ``email-ingest`` and wait for the Hatchet worker result."""
        task = self._task if self._task is not None else _default_task()
        model = payload or EmailIngestInput()
        result = task.run(model.model_dump(mode="json", exclude_none=True), wait_for_result=True)
        return dict(result) if isinstance(result, dict) else {"result": result}


def run_orchestrator_worker(*, slots: int | None = None, skip_env_file: bool = False) -> int:
    """Block as a Hatchet worker serving ``email-ingest`` and ``email-ingest-cron``."""
    if not skip_env_file:
        load_environment_file(override=False)
    settings = EmailFlowSettings()
    effective_slots = slots if slots is not None else settings.orchestrator_worker_slots
    hatchet = Hatchet()
    workflows = [
        build_email_ingest_task(hatchet, settings=settings),
        build_email_ingest_cron_task(hatchet, settings=settings),
    ]
    worker = hatchet.worker(
        name="papita-ingestor-email",
        slots=effective_slots,
        labels={"workload": "ingestion", "app": "save-ma-money"},
        workflows=workflows,
    )
    logger.info(
        "Starting Hatchet worker papita-ingestor-email (slots=%d, cron=%s)",
        effective_slots,
        settings.orchestrator_email_ingest_cron,
    )
    worker.start()
    return 0


__all__ = [
    "EmailIngestInput",
    "HatchetEmailIngestionDispatcher",
    "build_email_ingest_cron_task",
    "build_email_ingest_task",
    "parse_email_ingest_input",
    "run_orchestrator_worker",
]
