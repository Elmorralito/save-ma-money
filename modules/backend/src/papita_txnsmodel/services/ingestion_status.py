"""Connection metadata and run-status services for ingestion (PPT-083 / #177).

Worker-facing writes upsert non-secret connection rows and append run history.
API-facing reads are owner-scoped list/get helpers. Does not import
``papita_ingestor_core.RunResult`` — callers map counters into
``RecordIngestionRunRequest`` before calling.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from papita_txnsmodel.access.ingestion.dto import IngestionConnectionDTO, IngestionRunDTO
from papita_txnsmodel.access.ingestion.repository import IngestionConnectionRepository, IngestionRunRepository
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.model.enums import IngestionRunStatus
from papita_txnsmodel.services.base import BaseService

logger = logging.getLogger(__name__)

_MAX_FILTER_TERMS = 20
_MAX_PARSING_RULES = 25
_MAX_REGEX_LEN = 256
_MAX_SENDER_LEN = 255
_MAX_SUBJECT_LEN = 120
_MAX_LABEL_LEN = 128
_MAX_LOOKBACK_HOURS = 720
# Reject nested quantifiers, backreferences, and lookbehinds that can trigger ReDoS.
_UNSAFE_REGEX_RE = re.compile(r"(?:\([^)]*(?:[+*]|\{\d+,\d*\})[^)]*\)\s*(?:[+*?]|\{\d+,\d*\})|\\[1-9]|\(\?<[=!])")


def _validate_parsing_rules(rules: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Validate structured per-user email parsing rules and regex syntax."""
    if not rules:
        return []
    if len(rules) > _MAX_PARSING_RULES:
        raise ValueError(f"parsing_rules cannot contain more than {_MAX_PARSING_RULES} entries.")
    validated: list[dict[str, Any]] = []
    allowed_modes = {"auto", "bancolombia-email", "global66-email", "nequi-email", "nu-email", "custom_regex"}
    allowed_types = {"auto", "income", "expense", "transfer"}
    for idx, raw in enumerate(rules):
        if not isinstance(raw, dict):
            raise ValueError(f"parsing_rules[{idx}] must be an object.")
        name = str(raw.get("name") or "").strip()
        if not name or len(name) > 120:
            raise ValueError(f"parsing_rules[{idx}].name must be 1–120 characters.")
        mode = str(raw.get("parser_mode") or "auto").strip().lower()
        if mode not in allowed_modes:
            raise ValueError(f"parsing_rules[{idx}].parser_mode {mode!r} is not supported.")
        txn_type = str(raw.get("transaction_type") or "auto").strip().lower()
        if txn_type not in allowed_types:
            raise ValueError(f"parsing_rules[{idx}].transaction_type {txn_type!r} is not supported.")
        amount_regex = str(raw.get("amount_regex") or "").strip()
        if len(amount_regex) > _MAX_REGEX_LEN:
            raise ValueError(f"parsing_rules[{idx}].amount_regex exceeds {_MAX_REGEX_LEN} characters.")
        if amount_regex:
            if _UNSAFE_REGEX_RE.search(amount_regex):
                raise ValueError(
                    f"parsing_rules[{idx}].amount_regex uses nested quantifiers, backreferences, or lookbehinds."
                )
            try:
                re.compile(amount_regex)
            except re.error as exc:
                raise ValueError(f"parsing_rules[{idx}].amount_regex is invalid regex: {exc}") from exc
        currency = str(raw.get("currency") or "COP").strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError(f"parsing_rules[{idx}].currency must be a 3-letter ISO code.")
        validated.append(
            {
                "id": str(raw.get("id") or uuid.uuid4()),
                "name": name,
                "enabled": bool(raw.get("enabled", True)),
                "parser_mode": mode,
                "sender_match": str(raw.get("sender_match") or "").strip()[:255],
                "subject_match": str(raw.get("subject_match") or "").strip()[:120],
                "amount_regex": amount_regex,
                "transaction_type": txn_type,
                "currency": currency,
                "default_account_id": str(raw["default_account_id"]) if raw.get("default_account_id") else None,
                "default_category_id": str(raw["default_category_id"]) if raw.get("default_category_id") else None,
                "description_template": str(raw.get("description_template") or "").strip()[:160],
            }
        )
    return validated


_SENDER_TERM_RE = re.compile(
    r"^(?:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+|[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)$"
)
_UNSAFE_QUERY_CHARS_RE = re.compile(r'[\x00-\x1f\x7f"()]')


def _normalize_filter_terms(values: list[str] | None, *, field_name: str, max_len: int) -> list[str]:
    """Trim, drop empty strings, enforce bounds, and deduplicate filter terms."""
    if not values:
        return []
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in values:
        term = str(item).strip()
        if not term or term in seen:
            continue
        if len(term) > max_len:
            raise ValueError(f"{field_name} item exceeds maximum length of {max_len} characters.")
        seen.add(term)
        cleaned.append(term)
    if len(cleaned) > _MAX_FILTER_TERMS:
        raise ValueError(f"{field_name} cannot contain more than {_MAX_FILTER_TERMS} entries.")
    return cleaned


def _validate_email_senders(values: list[str] | None) -> list[str]:
    """Validate sender addresses/domains to prevent Gmail query injection."""
    cleaned = _normalize_filter_terms(values, field_name="email_senders", max_len=_MAX_SENDER_LEN)
    for term in cleaned:
        if not _SENDER_TERM_RE.match(term):
            raise ValueError(f"Invalid email sender {term!r}: expected an email address or domain (e.g. bank.com).")
    return cleaned


def _validate_email_subjects(values: list[str] | None) -> list[str]:
    """Validate subject filter phrases against control chars and Gmail grouping characters."""
    cleaned = _normalize_filter_terms(values, field_name="email_subjects", max_len=_MAX_SUBJECT_LEN)
    for term in cleaned:
        if _UNSAFE_QUERY_CHARS_RE.search(term):
            raise ValueError("email_subjects entries must not contain quotes, parentheses, or control characters.")
    return cleaned


def _validate_source_label(value: str | None) -> str | None:
    """Trim and validate Gmail source label name."""
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if len(stripped) > _MAX_LABEL_LEN:
        raise ValueError(f"email_source_label exceeds maximum length of {_MAX_LABEL_LEN} characters.")
    if _UNSAFE_QUERY_CHARS_RE.search(stripped):
        raise ValueError("email_source_label must not contain quotes, parentheses, or control characters.")
    return stripped


def _normalize_optional_text(value: str | None) -> str | None:
    """Trim optional text fields and normalize blank strings to ``None``."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class UpsertIngestionConnectionRequest(BaseModel):
    """Non-secret connection + email channel filter fields."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(default="email", min_length=1, max_length=64)
    flow_name: str = Field(default="papita-email-ingestion", min_length=1, max_length=128)
    deployment_name: str | None = Field(default=None, max_length=128)
    enabled: bool = True
    lookback_hours: int = Field(default=24, ge=1, le=_MAX_LOOKBACK_HOURS)
    email_senders: list[str] = Field(default_factory=list)
    email_subjects: list[str] = Field(default_factory=list)
    email_source_label: str | None = Field(default=None, max_length=_MAX_LABEL_LEN)
    email_query: str | None = None
    gmail_access_enabled: bool | None = None
    parsing_rules: list[dict[str, Any]] | None = None

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

    @field_validator("email_query")
    @classmethod
    def _clean_optional_fields(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("parsing_rules")
    @classmethod
    def _clean_parsing_rules(cls, value: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        if value is None:
            return None
        return _validate_parsing_rules(value)


class UpdateIngestionConnectionRequest(BaseModel):
    """Partial update payload for an existing owner-scoped connection."""

    model_config = ConfigDict(extra="forbid")

    deployment_name: str | None = Field(default=None, max_length=128)
    enabled: bool | None = None
    lookback_hours: int | None = Field(default=None, ge=1, le=_MAX_LOOKBACK_HOURS)
    email_senders: list[str] | None = None
    email_subjects: list[str] | None = None
    email_source_label: str | None = Field(default=None, max_length=_MAX_LABEL_LEN)
    email_query: str | None = None
    gmail_access_enabled: bool | None = None
    parsing_rules: list[dict[str, Any]] | None = None

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

    @field_validator("email_query")
    @classmethod
    def _clean_optional_fields(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("parsing_rules")
    @classmethod
    def _clean_optional_parsing_rules(cls, value: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        if value is None:
            return None
        return _validate_parsing_rules(value)


class RecordIngestionRunRequest(BaseModel):
    """Model-local run payload (not an API schema). Trusted caller supplies ``owner``."""

    model_config = ConfigDict(extra="forbid")

    connection_id: uuid.UUID | None = None
    status: IngestionRunStatus
    started_at: datetime
    finished_at: datetime | None = None
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


class IngestionConnectionService(BaseService):
    """Owner-scoped connection metadata for status APIs and worker upserts."""

    dto_type: type[IngestionConnectionDTO] = IngestionConnectionDTO
    repository_type: type[IngestionConnectionRepository] = IngestionConnectionRepository
    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE

    _connection_repository: IngestionConnectionRepository | None = None

    @model_validator(mode="after")
    def _init_connection_repo(self) -> Self:
        """Expose typed repository after BaseService wires ``_repository``."""
        self._connection_repository = self.repository_type()
        return self

    def _owned(self, owner: UsersDTO | None) -> UsersDTO:
        """Return a non-optional owner after BaseService tenant checks."""
        ensured = self._ensure_owner(owner)
        if ensured is None:
            raise ValueError(f"{self.dto_type.__name__} requires owner=UsersDTO for tenant-scoped operations.")
        return ensured

    def upsert_connection(
        self,
        *,
        owner: UsersDTO,
        request: UpsertIngestionConnectionRequest,
        preserve_existing_config: bool = False,
        **kwargs,
    ) -> IngestionConnectionDTO:
        """Insert or update the connection for ``(owner, provider, flow_name)``.

        Preserves the existing row id on natural-key match so run FKs stay stable.
        Soft-deleted natural-key matches are reactivated in place (unique index is
        not partial, matching provenance sidecar semantics). When
        ``preserve_existing_config`` is True (worker runs), existing active user
        configuration fields are kept intact rather than overwritten by env defaults.
        """
        owner = self._owned(owner)
        existing = self._connection_repository.get_by_natural_key(
            owner=owner,
            provider=request.provider,
            flow_name=request.flow_name,
            include_deleted=True,
            **kwargs,
        )
        payload = request.model_dump()
        reactivate = False
        if existing is not None and existing.id is not None:
            payload["id"] = existing.id
            payload["created_at"] = existing.created_at
            # Always preserve server-managed encrypted OAuth token & connected email on config upsert.
            payload["gmail_refresh_token_enc"] = existing.gmail_refresh_token_enc
            payload["gmail_connected_email"] = existing.gmail_connected_email
            if payload.get("gmail_access_enabled") is None:
                payload["gmail_access_enabled"] = existing.gmail_access_enabled
            if payload.get("parsing_rules") is None:
                payload["parsing_rules"] = list(existing.parsing_rules)
            is_active = bool(getattr(existing, "active", True))
            if not is_active:
                reactivate = True
                payload["active"] = True
                payload["deleted_at"] = None
            elif preserve_existing_config:
                payload["enabled"] = existing.enabled
                payload["lookback_hours"] = existing.lookback_hours
                payload["email_senders"] = list(existing.email_senders)
                payload["email_subjects"] = list(existing.email_subjects)
                payload["email_source_label"] = existing.email_source_label
                payload["email_query"] = existing.email_query
                payload["gmail_access_enabled"] = existing.gmail_access_enabled
                payload["parsing_rules"] = list(existing.parsing_rules)
        else:
            if payload.get("gmail_access_enabled") is None:
                payload["gmail_access_enabled"] = False
            if payload.get("parsing_rules") is None:
                payload["parsing_rules"] = []
        dto = IngestionConnectionDTO.model_validate({**payload, "owner_id": owner.id})
        upserted = self._connection_repository.upsert_record(
            dto,
            owner=owner,
            reactivate=reactivate,
            **kwargs,
        )
        if not isinstance(upserted, IngestionConnectionDTO):
            raise RuntimeError(
                "Failed to upsert ingestion connection "
                f"(owner_id={owner.id}, provider={request.provider!r}, flow_name={request.flow_name!r})."
            )
        logger.debug(
            "Upserted ingestion connection owner_id=%s provider=%s flow_name=%s id=%s reactivate=%s",
            owner.id,
            request.provider,
            request.flow_name,
            upserted.id,
            reactivate,
        )
        return upserted

    def get_connection_by_natural_key(
        self,
        *,
        owner: UsersDTO,
        provider: str = "email",
        flow_name: str = "papita-email-ingestion",
        **kwargs,
    ) -> IngestionConnectionDTO | None:
        """Return active connection for ``(owner, provider, flow_name)``, or ``None``."""
        owner = self._owned(owner)
        return self._connection_repository.get_by_natural_key(
            owner=owner,
            provider=provider,
            flow_name=flow_name,
            include_deleted=False,
            **kwargs,
        )

    def update_connection(
        self,
        *,
        owner: UsersDTO,
        connection_id: uuid.UUID,
        request: UpdateIngestionConnectionRequest,
        **kwargs,
    ) -> IngestionConnectionDTO | None:
        """Apply partial channel/schedule updates to an owner-scoped connection."""
        owner = self._owned(owner)
        existing = self.get_connection(owner=owner, connection_id=connection_id, **kwargs)
        if existing is None:
            return None
        updates = request.model_dump(exclude_unset=True)
        merged = existing.model_copy(update=updates)
        updated = self._connection_repository.upsert_record(
            merged,
            owner=owner,
            **kwargs,
        )
        if not isinstance(updated, IngestionConnectionDTO):
            raise RuntimeError(f"Failed to update ingestion connection id={connection_id} for owner_id={owner.id}.")
        return updated

    def delete_connection(
        self,
        *,
        owner: UsersDTO,
        connection_id: uuid.UUID,
        **kwargs,
    ) -> bool:
        """Disable and soft-delete an owner-scoped connection; returns False if not found."""
        owner = self._owned(owner)
        existing = self.get_connection(owner=owner, connection_id=connection_id, **kwargs)
        if existing is None:
            return False
        disabled = existing.model_copy(update={"enabled": False})
        self._connection_repository.upsert_record(disabled, owner=owner, **kwargs)
        self.delete(obj=disabled, owner=owner, hard=False, **kwargs)
        return True

    def list_connections(self, *, owner: UsersDTO, **kwargs) -> list[IngestionConnectionDTO]:
        """Return active connections for the owner, newest first."""
        owner = self._owned(owner)
        dao = IngestionConnectionDTO.__dao_type__
        frame = self._connection_repository.get_records(
            owner=owner,
            dto_type=IngestionConnectionDTO,
            order_by=[dao.updated_at.desc()],
            **kwargs,
        )
        if getattr(frame, "empty", True):
            return []
        if len(frame.columns) == 1 and isinstance(frame.iloc[0, 0], dao):
            return [IngestionConnectionDTO.from_dao(cell) for cell in frame.iloc[:, 0]]
        return [IngestionConnectionDTO.model_validate(row) for row in frame.to_dict(orient="records")]

    def set_gmail_credentials(
        self,
        *,
        owner: UsersDTO,
        connected_email: str | None,
        encrypted_refresh_token: str | None,
        access_enabled: bool,
        provider: str = "email",
        flow_name: str = "papita-email-ingestion",
        **kwargs,
    ) -> IngestionConnectionDTO:
        """Persist or clear per-user encrypted Gmail refresh token and access toggle."""
        owner = self._owned(owner)
        existing = self._connection_repository.get_by_natural_key(
            owner=owner,
            provider=provider,
            flow_name=flow_name,
            include_deleted=True,
            **kwargs,
        )
        if existing is None:
            dto = IngestionConnectionDTO(
                owner_id=owner.id,
                provider=provider,
                flow_name=flow_name,
                enabled=True,
                lookback_hours=24,
                gmail_access_enabled=access_enabled,
                gmail_connected_email=connected_email,
                gmail_refresh_token_enc=encrypted_refresh_token,
            )
            return self._connection_repository.upsert_record(
                dto,
                owner=owner,
                on_conflict_do=self.on_conflict_do,
                **kwargs,
            )
        updated = existing.model_copy(
            update={
                "active": True,
                "deleted_at": None,
                "gmail_access_enabled": access_enabled,
                "gmail_connected_email": connected_email,
                "gmail_refresh_token_enc": encrypted_refresh_token,
            }
        )
        return self._connection_repository.upsert_record(
            updated,
            owner=owner,
            on_conflict_do=OnUpsertConflictDo.UPDATE,
            **kwargs,
        )

    def get_connection(
        self,
        *,
        owner: UsersDTO,
        connection_id: uuid.UUID,
        **kwargs,
    ) -> IngestionConnectionDTO | None:
        """Return one connection by id when owned by ``owner``; else ``None`` (API → 404)."""
        dto = self.get(obj=connection_id, owner=owner, **kwargs)
        return dto if isinstance(dto, IngestionConnectionDTO) else None


class IngestionRunService(BaseService):
    """Owner-scoped run history writes (worker) and reads (API)."""

    dto_type: type[IngestionRunDTO] = IngestionRunDTO
    repository_type: type[IngestionRunRepository] = IngestionRunRepository
    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE

    _run_repository: IngestionRunRepository | None = None

    @model_validator(mode="after")
    def _init_run_repo(self) -> Self:
        """Expose typed repository after BaseService wires ``_repository``."""
        self._run_repository = self.repository_type()
        return self

    def _owned(self, owner: UsersDTO | None) -> UsersDTO:
        """Return a non-optional owner after BaseService tenant checks."""
        ensured = self._ensure_owner(owner)
        if ensured is None:
            raise ValueError(f"{self.dto_type.__name__} requires owner=UsersDTO for tenant-scoped operations.")
        return ensured

    def start_run(
        self,
        *,
        owner: UsersDTO,
        connection_id: uuid.UUID | None = None,
        started_at: datetime | None = None,
        flow_name: str | None = None,
        deployment_name: str | None = None,
        **kwargs,
    ) -> IngestionRunDTO:
        """Append a ``STARTED`` run row at flow begin."""
        started = started_at or datetime.now(timezone.utc)
        return self.record_run(
            owner=owner,
            request=RecordIngestionRunRequest(
                connection_id=connection_id,
                status=IngestionRunStatus.STARTED,
                started_at=started,
                flow_name=flow_name,
                deployment_name=deployment_name,
            ),
            **kwargs,
        )

    def finish_run(
        self,
        *,
        owner: UsersDTO,
        run_id: uuid.UUID,
        request: RecordIngestionRunRequest,
        **kwargs,
    ) -> IngestionRunDTO:
        """Update an existing run with terminal status and counters."""
        owner = self._owned(owner)
        existing = self.get(obj=run_id, owner=owner, **kwargs)
        if existing is None:
            raise ValueError(f"Ingestion run {run_id} not found for owner.")
        payload = request.model_dump()
        payload["id"] = run_id
        payload["created_at"] = existing.created_at
        if payload.get("started_at") is None:
            payload["started_at"] = existing.started_at
        dto = IngestionRunDTO.model_validate({**payload, "owner_id": owner.id})
        upserted = self._run_repository.upsert_record(dto, owner=owner, **kwargs)
        if not isinstance(upserted, IngestionRunDTO):
            raise RuntimeError(f"Failed to finish ingestion run {run_id} for owner_id={owner.id}.")
        logger.debug(
            "Finished ingestion run owner_id=%s run_id=%s status=%s",
            owner.id,
            run_id,
            upserted.status,
        )
        return upserted

    def record_run(
        self,
        *,
        owner: UsersDTO,
        request: RecordIngestionRunRequest,
        **kwargs,
    ) -> IngestionRunDTO:
        """Insert a new run row (start or one-shot terminal write)."""
        owner = self._owned(owner)
        dto = IngestionRunDTO.model_validate({**request.model_dump(), "owner_id": owner.id})
        upserted = self._run_repository.upsert_record(dto, owner=owner, **kwargs)
        if not isinstance(upserted, IngestionRunDTO):
            raise RuntimeError(f"Failed to record ingestion run status={request.status!r} for owner_id={owner.id}.")
        logger.debug(
            "Recorded ingestion run owner_id=%s status=%s id=%s",
            owner.id,
            upserted.status,
            upserted.id,
        )
        return upserted

    def get_latest_run(
        self,
        *,
        owner: UsersDTO,
        connection_id: uuid.UUID | None = None,
        **kwargs,
    ) -> IngestionRunDTO | None:
        """Return the most recently started run for the owner."""
        owner = self._owned(owner)
        return self._run_repository.get_latest(owner=owner, connection_id=connection_id, **kwargs)

    def list_runs(
        self,
        *,
        owner: UsersDTO,
        connection_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 50,
        **kwargs,
    ) -> list[IngestionRunDTO]:
        """Return recent runs for the owner, newest first."""
        owner = self._owned(owner)
        dao = IngestionRunDTO.__dao_type__
        filters = []
        if connection_id is not None:
            filters.append(dao.connection_id == connection_id)
        frame = self._run_repository.get_records(
            *filters,
            owner=owner,
            dto_type=IngestionRunDTO,
            order_by=[dao.started_at.desc()],
            skip=skip,
            limit=limit,
            **kwargs,
        )
        if getattr(frame, "empty", True):
            return []
        if len(frame.columns) == 1 and isinstance(frame.iloc[0, 0], dao):
            return [IngestionRunDTO.from_dao(cell) for cell in frame.iloc[:, 0]]
        return [IngestionRunDTO.model_validate(row) for row in frame.to_dict(orient="records")]
