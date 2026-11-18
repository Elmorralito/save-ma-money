"""Ingestion connection and run-status response schemas (PPT-083 / #177).

Allowlisted read models for ``GET /ingestion/connections`` and
``GET /ingestion/runs*``. Intentionally excludes OAuth secrets, Gmail tokens,
raw mailbox payloads, and DLQ ``raw_payload`` — those never appear on these
resources.

Routers own HTTP shape only; persistence stays in ``papita_txnsmodel`` services
(worker writes; API is read-only).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from papita_txnsapi.schemas.converters import enum_to_api_slug
from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.access.ingestion.dto import IngestionConnectionDTO, IngestionRunDTO
from papita_txnsmodel.model.enums import IngestionRunStatus

# Fields that must never appear on public ingestion status responses.
_FORBIDDEN_RESPONSE_FIELDS = frozenset(
    {
        "raw_payload",
        "client_secret",
        "client_id",
        "refresh_token",
        "access_token",
        "password",
        "gmail_token",
        "oauth_token",
        "credentials",
    }
)


def _require_uuid(value: uuid.UUID | None, *, field_name: str) -> uuid.UUID:
    """Return a persisted UUID or raise when the DTO primary key is missing."""
    if value is None:
        raise ValueError(f"{field_name} is required.")
    return value


def _relation_uuid(value: uuid.UUID | Any | None) -> uuid.UUID | None:
    """Extract a UUID from a relation field that may be a nested DTO."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, TableDTO):
        return value.id
    return uuid.UUID(str(value))


def _status_slug(value: IngestionRunStatus | str | Enum) -> str:
    """Normalize run status to the API lowercase slug."""
    if isinstance(value, Enum):
        return enum_to_api_slug(value)
    return str(value).strip().lower()


class IngestionConnectionResponse(BaseModel):
    """Non-secret connection metadata for status APIs.

    Allowlist: identity + provider/flow labels + enabled/lookback only.
    """

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    provider: str
    flow_name: str
    deployment_name: str | None = None
    enabled: bool
    lookback_hours: int = Field(ge=1)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_dto(cls, connection: IngestionConnectionDTO) -> IngestionConnectionResponse:
        """Build an API response from ``IngestionConnectionDTO``.

        Args:
            connection: Owner-scoped connection row from the model service.

        Returns:
            Allowlisted connection resource (no credentials).
        """
        return cls(
            id=_require_uuid(connection.id, field_name="Connection id"),
            provider=connection.provider,
            flow_name=connection.flow_name,
            deployment_name=connection.deployment_name,
            enabled=bool(connection.enabled),
            lookback_hours=int(connection.lookback_hours),
            created_at=connection.created_at,
            updated_at=connection.updated_at,
        )


class IngestionRunResponse(BaseModel):
    """Owner-scoped ingestion run history for status APIs.

    Counters and status only — never per-record failure payloads or DLQ bodies.
    """

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    connection_id: uuid.UUID | None = None
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    fetched: int = Field(ge=0)
    created: int = Field(ge=0)
    updated: int = Field(ge=0)
    reactivated: int = Field(ge=0)
    failed: int = Field(ge=0)
    dead_lettered: int = Field(ge=0)
    acknowledged: int = Field(ge=0)
    dry_run_skipped: int = Field(ge=0)
    error_summary: str | None = None
    flow_name: str | None = None
    deployment_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_dto(cls, run: IngestionRunDTO) -> IngestionRunResponse:
        """Build an API response from ``IngestionRunDTO``.

        Args:
            run: Owner-scoped run row from the model service.

        Returns:
            Allowlisted run resource (no raw payloads).
        """
        return cls(
            id=_require_uuid(run.id, field_name="Run id"),
            connection_id=_relation_uuid(run.connection_id),
            status=_status_slug(run.status),
            started_at=run.started_at,
            finished_at=run.finished_at,
            fetched=int(run.fetched),
            created=int(run.created),
            updated=int(run.updated),
            reactivated=int(run.reactivated),
            failed=int(run.failed),
            dead_lettered=int(run.dead_lettered),
            acknowledged=int(run.acknowledged),
            dry_run_skipped=int(run.dry_run_skipped),
            error_summary=run.error_summary,
            flow_name=run.flow_name,
            deployment_name=run.deployment_name,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )


def assert_ingestion_response_allowlist() -> None:
    """Raise if forbidden secret/raw field names appear on public schemas.

    Intended for unit tests / import-time hygiene — not a runtime router check.
    """
    for schema in (IngestionConnectionResponse, IngestionRunResponse):
        overlap = _FORBIDDEN_RESPONSE_FIELDS.intersection(schema.model_fields)
        if overlap:
            raise AssertionError(f"{schema.__name__} exposes forbidden fields: {sorted(overlap)}")


__all__ = [
    "IngestionConnectionResponse",
    "IngestionRunResponse",
    "assert_ingestion_response_allowlist",
]
