"""DTOs for ingestion provenance sidecar and dead letters (PPT-078 / #172)."""

from __future__ import annotations

import datetime
import uuid

from pydantic import Field

from papita_txnsmodel.access.users.dto import OwnedTableDTO
from papita_txnsmodel.model.enums import IngestionSource
from papita_txnsmodel.model.ingestion import IngestionDeadLetter, TransactionIngestionProvenance


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
