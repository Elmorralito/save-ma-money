"""DTOs for ingestion provenance, DLQ, connections, and runs."""

from __future__ import annotations

import datetime
import uuid

from pydantic import Field

from papita_txnsmodel.access.users.dto import OwnedTableDTO
from papita_txnsmodel.model.enums import IngestionRunStatus, IngestionSource
from papita_txnsmodel.model.ingestion import (
    IngestionConnection,
    IngestionDeadLetter,
    IngestionRun,
    TransactionIngestionProvenance,
)


class TransactionIngestionProvenanceDTO(OwnedTableDTO):
    """DTO for the non-partitioned ingestion idempotency registry."""

    __dao_type__ = TransactionIngestionProvenance

    transaction_id: uuid.UUID
    transaction_ts: datetime.datetime
    ingestion_source: IngestionSource
    source_ref: str | None = Field(default=None, max_length=255)


class IngestionDeadLetterDTO(OwnedTableDTO):
    """DTO for thin ingest failure / dead-letter storage."""

    __dao_type__ = IngestionDeadLetter

    ingestion_source: IngestionSource
    raw_payload: str = ""
    error_message: str = ""
    source_ref: str | None = Field(default=None, max_length=255)


class IngestionConnectionDTO(OwnedTableDTO):
    """Non-secret connection metadata for status APIs (PPT-083 / #177)."""

    __dao_type__ = IngestionConnection

    provider: str = Field(default="email", min_length=1, max_length=64)
    flow_name: str = Field(min_length=1, max_length=128)
    deployment_name: str | None = Field(default=None, max_length=128)
    enabled: bool = True
    lookback_hours: int = Field(default=24, ge=1)


class IngestionRunDTO(OwnedTableDTO):
    """Owner-scoped ingestion run row for status APIs (PPT-083 / #177)."""

    __dao_type__ = IngestionRun

    connection_id: uuid.UUID | None = None
    status: IngestionRunStatus
    started_at: datetime.datetime
    finished_at: datetime.datetime | None = None
    fetched: int = Field(default=0, ge=0)
    created: int = Field(default=0, ge=0)
    updated: int = Field(default=0, ge=0)
    reactivated: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    dead_lettered: int = Field(default=0, ge=0)
    acknowledged: int = Field(default=0, ge=0)
    dry_run_skipped: int = Field(default=0, ge=0)
    error_summary: str | None = None
    flow_name: str | None = Field(default=None, max_length=128)
    deployment_name: str | None = Field(default=None, max_length=128)
