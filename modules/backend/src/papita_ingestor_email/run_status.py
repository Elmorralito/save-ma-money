"""Persist non-secret connection + run status around one runner invocation (PPT-083)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from papita_ingestor_core.runner.ingestion_runner import IngestionRunner
from papita_ingestor_core.types.records import FetchFilter, RunResult
from papita_ingestor_email.flow_settings import EmailFlowSettings
from papita_ingestor_email.status_mapping import derive_run_status, run_result_to_record_request
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import IngestionRunStatus
from papita_txnsmodel.services.ingestion_status import (
    IngestionConnectionService,
    IngestionRunService,
    RecordIngestionRunRequest,
    UpsertIngestionConnectionRequest,
)

logger = logging.getLogger(__name__)

_PROVIDER = "email"


def _resolve_owner(runner: IngestionRunner) -> UsersDTO:
    """Resolve the runner owner (callable or DTO)."""
    return runner._resolve_owner()  # pylint: disable=protected-access  # intentional plugin seam


def execute_with_run_status(  # pylint: disable=too-many-locals
    runner: IngestionRunner,
    fetch_filter: FetchFilter | None,
    *,
    settings: EmailFlowSettings,
    flow_name: str,
    deployment_name: str | None,
    connection_service: IngestionConnectionService | Any | None = None,
    run_service: IngestionRunService | Any | None = None,
    persist_status: bool = True,
) -> RunResult:
    """Upsert connection → start run → ``runner.run`` → finish run (or FAILED on abort).

    Skips all status writes when ``persist_status`` is false (e.g. dry-run). Status
    persistence errors are logged and do not replace runner exceptions.
    """
    if not persist_status:
        return runner.run(fetch_filter)

    conn_svc = connection_service or IngestionConnectionService()
    run_svc = run_service or IngestionRunService()
    owner = _resolve_owner(runner)
    started_at = datetime.now(timezone.utc)
    connection_id: uuid.UUID | None = None
    run_id: uuid.UUID | None = None

    try:
        connection = conn_svc.upsert_connection(
            owner=owner,
            request=UpsertIngestionConnectionRequest(
                provider=_PROVIDER,
                flow_name=flow_name,
                deployment_name=deployment_name,
                enabled=True,
                lookback_hours=settings.lookback_hours,
            ),
        )
        connection_id = connection.id
        started = run_svc.start_run(
            owner=owner,
            connection_id=connection_id,
            started_at=started_at,
            flow_name=flow_name,
            deployment_name=deployment_name,
        )
        run_id = started.id
    except Exception:  # pylint: disable=broad-except
        logger.exception(
            "Failed to start ingestion status persistence owner_id=%s flow_name=%s",
            owner.id,
            flow_name,
        )

    try:
        result = runner.run(fetch_filter)
    except Exception as exc:
        _safe_finish_failed(
            run_svc=run_svc,
            owner=owner,
            run_id=run_id,
            connection_id=connection_id,
            started_at=started_at,
            flow_name=flow_name,
            deployment_name=deployment_name,
            error_summary=str(exc),
        )
        raise

    _safe_finish_result(
        run_svc=run_svc,
        owner=owner,
        run_id=run_id,
        connection_id=connection_id,
        started_at=started_at,
        flow_name=flow_name,
        deployment_name=deployment_name,
        result=result,
    )
    return result


def _safe_finish_result(
    *,
    run_svc: IngestionRunService | Any,
    owner: UsersDTO,
    run_id: uuid.UUID | None,
    connection_id: uuid.UUID | None,
    started_at: datetime,
    flow_name: str,
    deployment_name: str | None,
    result: RunResult,
) -> None:
    if run_id is None:
        return
    finished_at = datetime.now(timezone.utc)
    status = derive_run_status(result)
    request = run_result_to_record_request(
        result,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        connection_id=connection_id,
        flow_name=flow_name,
        deployment_name=deployment_name,
    )
    try:
        run_svc.finish_run(owner=owner, run_id=run_id, request=request)
    except Exception:  # pylint: disable=broad-except
        logger.exception("Failed to finish ingestion run status run_id=%s", run_id)


def _safe_finish_failed(
    *,
    run_svc: IngestionRunService | Any,
    owner: UsersDTO,
    run_id: uuid.UUID | None,
    connection_id: uuid.UUID | None,
    started_at: datetime,
    flow_name: str,
    deployment_name: str | None,
    error_summary: str,
) -> None:
    if run_id is None:
        return
    request = RecordIngestionRunRequest(
        connection_id=connection_id,
        status=IngestionRunStatus.FAILED,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
        error_summary=error_summary[:1024] if error_summary else None,
        flow_name=flow_name,
        deployment_name=deployment_name,
    )
    try:
        run_svc.finish_run(owner=owner, run_id=run_id, request=request)
    except Exception:  # pylint: disable=broad-except
        logger.exception("Failed to mark ingestion run FAILED run_id=%s", run_id)


__all__ = ["execute_with_run_status"]
