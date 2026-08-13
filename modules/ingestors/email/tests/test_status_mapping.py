"""Unit tests for RunResult → model status mapping (PPT-083 / #177)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from papita_ingestor_core.types.records import RecordFailure, RunResult
from papita_ingestor_email.status_mapping import (
    derive_run_status,
    run_result_to_record_request,
    summarize_failures,
)
from papita_txnsmodel.model.enums import IngestionRunStatus


def test_derive_run_status_succeeded() -> None:
    assert derive_run_status(RunResult(fetched=2, created=2)) == IngestionRunStatus.SUCCEEDED


def test_derive_run_status_partial_with_dead_letters() -> None:
    result = RunResult(fetched=2, failed=2, dead_lettered=2)
    assert derive_run_status(result) == IngestionRunStatus.PARTIAL


def test_derive_run_status_failed() -> None:
    result = RunResult(fetched=1, failed=1)
    assert derive_run_status(result) == IngestionRunStatus.FAILED


def test_summarize_failures_omits_raw_and_truncates_count() -> None:
    failures = [
        RecordFailure(source_ref=f"r-{i}", error_type="X", message=f"m{i}") for i in range(7)
    ]
    summary = summarize_failures(RunResult(failures=failures), max_lines=3)
    assert summary is not None
    assert "r-0" in summary
    assert "+4 more" in summary
    assert "opaque" not in summary


def test_run_result_to_record_request_copies_counters() -> None:
    started = datetime(2026, 8, 12, tzinfo=timezone.utc)
    finished = datetime(2026, 8, 12, 1, tzinfo=timezone.utc)
    conn_id = uuid.uuid4()
    result = RunResult(fetched=3, created=1, updated=1, reactivated=0, failed=1, acknowledged=2)
    request = run_result_to_record_request(
        result,
        status=IngestionRunStatus.PARTIAL,
        started_at=started,
        finished_at=finished,
        connection_id=conn_id,
        flow_name="papita-email-ingestion",
        deployment_name="papita-email-ingestion-hourly",
    )
    assert request.fetched == 3
    assert request.created == 1
    assert request.updated == 1
    assert request.failed == 1
    assert request.connection_id == conn_id
    assert request.flow_name == "papita-email-ingestion"
    assert request.status == IngestionRunStatus.PARTIAL
