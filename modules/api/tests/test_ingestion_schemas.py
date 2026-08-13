"""Allowlist tests for ingestion status API schemas (PPT-083 / #177 T6)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from papita_txnsapi.schemas.converters import parse_ingestion_run_status
from papita_txnsapi.schemas.ingestion import (
    IngestionConnectionResponse,
    IngestionRunResponse,
    assert_ingestion_response_allowlist,
)
from papita_txnsmodel.access.ingestion.dto import IngestionConnectionDTO, IngestionRunDTO
from papita_txnsmodel.model.enums import IngestionRunStatus


def test_assert_ingestion_response_allowlist() -> None:
    assert_ingestion_response_allowlist()


def test_connection_response_from_dto_allowlisted_only() -> None:
    owner_id = uuid.uuid4()
    conn_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    dto = IngestionConnectionDTO(
        id=conn_id,
        owner_id=owner_id,
        provider="email",
        flow_name="papita-email-ingestion",
        deployment_name="papita-email-ingestion-hourly",
        enabled=True,
        lookback_hours=24,
        created_at=now,
        updated_at=now,
    )
    response = IngestionConnectionResponse.from_dto(dto)
    payload = response.model_dump()
    assert payload["id"] == conn_id
    assert payload["provider"] == "email"
    assert payload["flow_name"] == "papita-email-ingestion"
    assert "owner_id" not in payload
    assert "raw_payload" not in payload
    assert "refresh_token" not in payload
    assert set(IngestionConnectionResponse.model_fields) == {
        "id",
        "provider",
        "flow_name",
        "deployment_name",
        "enabled",
        "lookback_hours",
        "created_at",
        "updated_at",
    }


def test_run_response_from_dto_uses_status_slug() -> None:
    owner_id = uuid.uuid4()
    run_id = uuid.uuid4()
    started = datetime(2026, 8, 12, tzinfo=timezone.utc)
    dto = IngestionRunDTO(
        id=run_id,
        owner_id=owner_id,
        status=IngestionRunStatus.PARTIAL,
        started_at=started,
        finished_at=started,
        fetched=3,
        created=1,
        failed=1,
        dead_lettered=1,
        error_summary="IngestorValidationError@msg-1: missing FK",
        flow_name="papita-email-ingestion",
    )
    response = IngestionRunResponse.from_dto(dto)
    assert response.status == "partial"
    assert response.fetched == 3
    assert response.error_summary is not None
    assert "raw_payload" not in response.model_fields
    assert "failures" not in response.model_fields


def test_parse_ingestion_run_status_slug() -> None:
    assert parse_ingestion_run_status("succeeded") == IngestionRunStatus.SUCCEEDED
    assert parse_ingestion_run_status("FAILED") == IngestionRunStatus.FAILED
