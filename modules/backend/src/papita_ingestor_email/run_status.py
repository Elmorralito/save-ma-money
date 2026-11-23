"""Email-scoped compatibility wrapper over ``papita_ingestor_core.run_status``."""

from __future__ import annotations

from typing import Any

from papita_ingestor_core.run_status import execute_with_run_status as _core_execute_with_run_status
from papita_ingestor_core.runner.ingestion_runner import IngestionRunner
from papita_ingestor_core.types.records import FetchFilter, RunResult
from papita_ingestor_email.flow_settings import EmailFlowSettings
from papita_txnsmodel.services.ingestion_status import IngestionConnectionService, IngestionRunService

_PROVIDER = "email"


def execute_with_run_status(
    runner: IngestionRunner,
    fetch_filter: FetchFilter | None,
    *,
    settings: EmailFlowSettings,
    flow_name: str,
    deployment_name: str | None,
    connection_service: IngestionConnectionService | Any | None = None,
    run_service: IngestionRunService | Any | None = None,
    persist_status: bool = True,
    provider: str = _PROVIDER,
) -> RunResult:
    """Persist connection + run status around ``runner.run``."""
    return _core_execute_with_run_status(
        runner,
        fetch_filter,
        provider=provider,
        lookback_hours=settings.lookback_hours,
        flow_name=flow_name,
        deployment_name=deployment_name,
        connection_service=connection_service,
        run_service=run_service,
        persist_status=persist_status,
    )


__all__ = ["execute_with_run_status"]
