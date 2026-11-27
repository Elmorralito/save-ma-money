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
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from papita_txnsapi.schemas.converters import enum_to_api_slug
from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.access.ingestion.dto import IngestionConnectionDTO, IngestionRunDTO
from papita_txnsmodel.model.enums import IngestionRunStatus
from papita_txnsmodel.services.ingestion_status import (
    _MAX_LABEL_LEN,
    _MAX_LOOKBACK_HOURS,
    _validate_email_senders,
    _validate_email_subjects,
    _validate_parsing_rules,
    _validate_source_label,
)

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


class EmailParsingRuleSchema(BaseModel):
    """Per-user structured email parsing rule and account/category target mapping."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    enabled: bool = True
    parser_mode: Literal[
        "auto",
        "bancolombia-email",
        "global66-email",
        "nequi-email",
        "nu-email",
        "custom_regex",
    ] = "auto"
    sender_match: str = Field(default="", max_length=255)
    subject_match: str = Field(default="", max_length=120)
    amount_regex: str = Field(default="", max_length=256)
    transaction_type: Literal["auto", "income", "expense", "transfer"] = "auto"
    currency: str = Field(default="COP", min_length=3, max_length=3)
    default_account_id: uuid.UUID | None = None
    default_category_id: uuid.UUID | None = None
    description_template: str = Field(default="", max_length=160)


class EmailParseTestRequest(BaseModel):
    """Dry-run sample email payload for testing parsing rules."""

    model_config = ConfigDict(extra="forbid")

    sender: str = Field(min_length=1, max_length=255)
    subject: str = Field(default="", max_length=255)
    body: str = Field(min_length=1, max_length=16_000)
    rules: list[EmailParsingRuleSchema] | None = None

    @field_validator("rules")
    @classmethod
    def _clean_test_rules(cls, value: list[EmailParsingRuleSchema] | None) -> list[EmailParsingRuleSchema] | None:
        if value is None:
            return None
        cleaned = _validate_parsing_rules([item.model_dump(mode="json") for item in value])
        return [EmailParsingRuleSchema.model_validate(item) for item in cleaned]


class EmailParseTestResponse(BaseModel):
    """Dry-run parse preview result."""

    matched: bool
    matched_rule_name: str | None = None
    parser_used: str | None = None
    transaction_type: str | None = None
    amount: float | None = None
    currency: str | None = None
    description: str | None = None
    default_account_id: uuid.UUID | None = None
    default_category_id: uuid.UUID | None = None
    error: str | None = None


class IngestionConnectionResponse(BaseModel):
    """Non-secret connection metadata and per-user channel filter configuration.

    Allowlist: identity + provider/flow labels + schedule/filter knobs only.
    """

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    provider: str
    flow_name: str
    deployment_name: str | None = None
    enabled: bool
    lookback_hours: int = Field(ge=1)
    email_senders: list[str] = Field(default_factory=list)
    email_subjects: list[str] = Field(default_factory=list)
    email_source_label: str | None = None
    email_query: str | None = None
    gmail_access_enabled: bool = False
    gmail_connected: bool = False
    gmail_connected_email: str | None = None
    parsing_rules: list[EmailParsingRuleSchema] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_dto(cls, connection: IngestionConnectionDTO) -> IngestionConnectionResponse:
        """Build an API response from ``IngestionConnectionDTO``."""
        raw_rules = list(getattr(connection, "parsing_rules", None) or [])
        parsed_rules = [EmailParsingRuleSchema.model_validate(item) for item in raw_rules]
        return cls(
            id=_require_uuid(connection.id, field_name="Connection id"),
            provider=connection.provider,
            flow_name=connection.flow_name,
            deployment_name=connection.deployment_name,
            enabled=bool(connection.enabled),
            lookback_hours=int(connection.lookback_hours),
            email_senders=list(connection.email_senders),
            email_subjects=list(connection.email_subjects),
            email_source_label=connection.email_source_label,
            email_query=connection.email_query,
            gmail_access_enabled=bool(getattr(connection, "gmail_access_enabled", False)),
            gmail_connected=bool(getattr(connection, "gmail_refresh_token_enc", None)),
            gmail_connected_email=getattr(connection, "gmail_connected_email", None),
            parsing_rules=parsed_rules,
            created_at=connection.created_at,
            updated_at=connection.updated_at,
        )


class IngestionConnectionUpsertRequest(BaseModel):
    """Idempotent upsert payload for ``PUT /ingestion/connections``.

    Only structured, validated channel filters are accepted (no raw Gmail ``q``).
    """

    model_config = ConfigDict(extra="forbid")

    provider: Literal["email"] = "email"
    flow_name: Literal["papita-email-ingestion"] = "papita-email-ingestion"
    deployment_name: str | None = Field(default=None, max_length=128)
    enabled: bool = True
    lookback_hours: int = Field(default=24, ge=1, le=_MAX_LOOKBACK_HOURS)
    email_senders: list[str] = Field(default_factory=list)
    email_subjects: list[str] = Field(default_factory=list)
    email_source_label: str | None = Field(default=None, max_length=_MAX_LABEL_LEN)
    gmail_access_enabled: bool | None = None
    parsing_rules: list[EmailParsingRuleSchema] | None = None

    @field_validator("email_senders")
    @classmethod
    def _clean_senders(cls, value: list[str]) -> list[str]:
        return _validate_email_senders(value)

    @field_validator("email_subjects")
    @classmethod
    def _clean_subjects(cls, value: list[str]) -> list[str]:
        return _validate_email_subjects(value)

    @field_validator("email_source_label")
    @classmethod
    def _clean_source_label(cls, value: str | None) -> str | None:
        return _validate_source_label(value)

    @field_validator("parsing_rules")
    @classmethod
    def _clean_rules(cls, value: list[EmailParsingRuleSchema] | None) -> list[EmailParsingRuleSchema] | None:
        if value is None:
            return None
        cleaned = _validate_parsing_rules([item.model_dump(mode="json") for item in value])
        return [EmailParsingRuleSchema.model_validate(item) for item in cleaned]


class IngestionConnectionUpdateRequest(BaseModel):
    """Partial update payload for ``PATCH /ingestion/connections/{connection_id}``."""

    model_config = ConfigDict(extra="forbid")

    deployment_name: str | None = Field(default=None, max_length=128)
    enabled: bool | None = None
    lookback_hours: int | None = Field(default=None, ge=1, le=_MAX_LOOKBACK_HOURS)
    email_senders: list[str] | None = None
    email_subjects: list[str] | None = None
    email_source_label: str | None = Field(default=None, max_length=_MAX_LABEL_LEN)
    gmail_access_enabled: bool | None = None
    parsing_rules: list[EmailParsingRuleSchema] | None = None

    @field_validator("email_senders")
    @classmethod
    def _clean_optional_senders(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _validate_email_senders(value)

    @field_validator("email_subjects")
    @classmethod
    def _clean_optional_subjects(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _validate_email_subjects(value)

    @field_validator("email_source_label")
    @classmethod
    def _clean_optional_label(cls, value: str | None) -> str | None:
        return _validate_source_label(value)

    @field_validator("parsing_rules")
    @classmethod
    def _clean_optional_rules(cls, value: list[EmailParsingRuleSchema] | None) -> list[EmailParsingRuleSchema] | None:
        if value is None:
            return None
        cleaned = _validate_parsing_rules([item.model_dump(mode="json") for item in value])
        return [EmailParsingRuleSchema.model_validate(item) for item in cleaned]


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


class IBKRImportRequest(BaseModel):
    """Request body for ``POST /ingestion/ibkr/activity-statement`` (PPT-101 / #262)."""

    model_config = ConfigDict(extra="forbid")

    csv_content: str = Field(min_length=1, max_length=5_000_000)
    fx_rate: float = Field(default=1.0, gt=0)
    base_currency: str = Field(default="COP", min_length=3, max_length=3)
    cash_account_id: uuid.UUID | None = None
    margin_account_id: uuid.UUID | None = None
    source_account_id: uuid.UUID | None = None
    create_missing_accounts: bool = True


class IBKRPositionImportResponse(BaseModel):
    """Imported IBKR position valuation summary."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    account_id: uuid.UUID
    action: str
    units: float
    unit_price: float
    fx_rate: float
    valued_amount: float
    unrealized_pnl: float | None = None


class IBKRImportResponse(BaseModel):
    """Response body for ``POST /ingestion/ibkr/activity-statement`` (PPT-101 / #262)."""

    model_config = ConfigDict(extra="forbid")

    account_code: str | None = None
    period: str | None = None
    as_of: datetime | None = None
    fx_rate: float
    base_currency: str
    positions: list[IBKRPositionImportResponse] = Field(default_factory=list)
    total_portfolio_value: float = 0.0
    settled_cash_value: float = 0.0
    margin_loan_value: float = 0.0
    margin_ltv_pct: float | None = None
    deposits_created: int = 0
    deposits_updated: int = 0


class ConnectorManifestResponse(BaseModel):
    """Non-secret metadata for a registered ingestion connector/parser/importer plugin."""

    model_config = ConfigDict(extra="forbid")

    plugin_id: str
    kind: str
    version: str
    ingestion_source: str
    supported_media_types: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    description: str = ""


def assert_ingestion_response_allowlist() -> None:
    """Raise if forbidden secret/raw field names appear on public schemas.

    Intended for unit tests / import-time hygiene — not a runtime router check.
    """
    for schema in (
        IngestionConnectionResponse,
        IngestionRunResponse,
        IBKRImportResponse,
        ConnectorManifestResponse,
    ):
        overlap = _FORBIDDEN_RESPONSE_FIELDS.intersection(schema.model_fields)
        if overlap:
            raise AssertionError(f"{schema.__name__} exposes forbidden fields: {sorted(overlap)}")


__all__ = [
    "ConnectorManifestResponse",
    "IBKRImportRequest",
    "IBKRImportResponse",
    "IBKRPositionImportResponse",
    "IngestionConnectionResponse",
    "IngestionConnectionUpdateRequest",
    "IngestionConnectionUpsertRequest",
    "IngestionRunResponse",
    "assert_ingestion_response_allowlist",
]
