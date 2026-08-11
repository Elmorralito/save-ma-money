"""Source-agnostic ingestion DTOs (PPT-079 / #173)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from papita_txnsmodel.model.enums import IngestionSource, TransactionKind, TransactionStatus

BridgeOutcome = Literal["created", "updated", "reactivated"]


class RawRecord(BaseModel):
    """Opaque source payload — core must not inspect ``content`` shapes."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    source_id: str = Field(min_length=1)
    source_ref: str | None = Field(default=None, max_length=255)
    content: bytes | str
    metadata: dict[str, Any] = Field(default_factory=dict)
    ingestion_source: IngestionSource = IngestionSource.EMAIL


class ParsedRecord(BaseModel):
    """Normalized record field-aligned with ``IngestTransactionRequest``."""

    model_config = ConfigDict(extra="forbid")

    ingestion_source: IngestionSource
    source_ref: str | None = Field(default=None, max_length=255)
    transaction_kind: TransactionKind
    amount: float = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    transaction_ts: datetime | None = None
    from_account_id: uuid.UUID | None = None
    to_account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    template_id: uuid.UUID | None = None
    status: TransactionStatus = TransactionStatus.COMPLETED
    description: str = ""
    reference_number: str | None = Field(default=None, max_length=64)
    tags: list[str] = Field(default_factory=list)


class FetchFilter(BaseModel):
    """Optional fetch window / cursor constraints for sources."""

    model_config = ConfigDict(extra="forbid")

    since: datetime | None = None
    until: datetime | None = None
    limit: int | None = Field(default=None, ge=1)
    cursor: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class RecordFailure(BaseModel):
    """Per-record failure captured in a run result."""

    model_config = ConfigDict(extra="forbid")

    source_ref: str | None = None
    error_type: str
    message: str
    dead_lettered: bool = False


class RunResult(BaseModel):
    """Aggregate outcome of one ``IngestionRunner`` invocation."""

    model_config = ConfigDict(extra="forbid")

    fetched: int = 0
    created: int = 0
    updated: int = 0
    reactivated: int = 0
    failed: int = 0
    dead_lettered: int = 0
    acknowledged: int = 0
    dry_run_skipped: int = 0
    failures: list[RecordFailure] = Field(default_factory=list)


__all__ = [
    "BridgeOutcome",
    "FetchFilter",
    "ParsedRecord",
    "RawRecord",
    "RecordFailure",
    "RunResult",
]
