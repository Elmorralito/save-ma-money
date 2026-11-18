"""Map ingestor-core ``RunResult`` → model run-status DTOs (PPT-083 / #177).

Lives in the email plugin so ``papita_txnsmodel`` never imports ``RunResult``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from papita_ingestor_core.types.records import RunResult
from papita_txnsmodel.model.enums import IngestionRunStatus
from papita_txnsmodel.services.ingestion_status import RecordIngestionRunRequest

_ERROR_SUMMARY_MAX = 1024
_MAX_FAILURE_LINES = 5


def derive_run_status(result: RunResult) -> IngestionRunStatus:
    """Derive terminal status from aggregate counters.

    - ``SUCCEEDED`` when ``failed == 0``
    - ``PARTIAL`` when some ledger success or handled DLQ exists alongside failures
    - ``FAILED`` when failures dominate with no successful outcomes
    """
    if result.failed <= 0:
        return IngestionRunStatus.SUCCEEDED
    successes = result.created + result.updated + result.reactivated
    if successes > 0 or result.dead_lettered > 0:
        return IngestionRunStatus.PARTIAL
    return IngestionRunStatus.FAILED


def summarize_failures(result: RunResult, *, max_lines: int = _MAX_FAILURE_LINES) -> str | None:
    """Build a short error summary from failure messages (never raw payloads)."""
    if not result.failures:
        return None
    lines: list[str] = []
    for failure in result.failures[:max_lines]:
        ref = failure.source_ref or "?"
        lines.append(f"{failure.error_type}@{ref}: {failure.message}")
    summary = "; ".join(lines)
    if len(result.failures) > max_lines:
        summary = f"{summary}; …(+{len(result.failures) - max_lines} more)"
    if len(summary) > _ERROR_SUMMARY_MAX:
        return summary[: _ERROR_SUMMARY_MAX - 1] + "…"
    return summary


def run_result_to_record_request(
    result: RunResult,
    *,
    status: IngestionRunStatus,
    started_at: datetime,
    finished_at: datetime | None,
    connection_id: uuid.UUID | None,
    flow_name: str | None,
    deployment_name: str | None,
    error_summary: str | None = None,
) -> RecordIngestionRunRequest:
    """Copy counter fields from ``RunResult`` into a model-local write request."""
    summary = error_summary if error_summary is not None else summarize_failures(result)
    return RecordIngestionRunRequest(
        connection_id=connection_id,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        fetched=result.fetched,
        created=result.created,
        updated=result.updated,
        reactivated=result.reactivated,
        failed=result.failed,
        dead_lettered=result.dead_lettered,
        acknowledged=result.acknowledged,
        dry_run_skipped=result.dry_run_skipped,
        error_summary=summary,
        flow_name=flow_name,
        deployment_name=deployment_name,
    )


__all__ = [
    "derive_run_status",
    "run_result_to_record_request",
    "summarize_failures",
]
