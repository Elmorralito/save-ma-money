"""Connection metadata and run-status services for ingestion (PPT-083 / #177).

Worker-facing writes upsert non-secret connection rows and append run history.
API-facing reads are owner-scoped list/get helpers. Does not import
``papita_ingestor_core.RunResult`` — callers map counters into
``RecordIngestionRunRequest`` before calling.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from papita_txnsmodel.access.ingestion.dto import IngestionConnectionDTO, IngestionRunDTO
from papita_txnsmodel.access.ingestion.repository import IngestionConnectionRepository, IngestionRunRepository
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.model.enums import IngestionRunStatus
from papita_txnsmodel.services.base import BaseService

logger = logging.getLogger(__name__)


class UpsertIngestionConnectionRequest(BaseModel):
    """Non-secret connection fields the worker may persist from settings + flow id."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(default="email", min_length=1, max_length=64)
    flow_name: str = Field(min_length=1, max_length=128)
    deployment_name: str | None = Field(default=None, max_length=128)
    enabled: bool = True
    lookback_hours: int = Field(default=24, ge=1)


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
        **kwargs,
    ) -> IngestionConnectionDTO:
        """Insert or update the connection for ``(owner, provider, flow_name)``.

        Preserves the existing row id on natural-key match so run FKs stay stable.
        Soft-deleted natural-key matches are reactivated in place (unique index is
        not partial, matching provenance sidecar semantics).
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
            if not getattr(existing, "active", True):
                reactivate = True
                payload["active"] = True
                payload["deleted_at"] = None
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
