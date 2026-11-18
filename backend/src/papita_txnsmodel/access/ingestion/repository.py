"""Repositories for ingestion provenance, DLQ, connections, and runs."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from papita_txnsmodel.access.base.repository import OwnedTableRepository
from papita_txnsmodel.access.ingestion.dto import (
    IngestionConnectionDTO,
    IngestionDeadLetterDTO,
    IngestionRunDTO,
    TransactionIngestionProvenanceDTO,
)
from papita_txnsmodel.model.enums import IngestionSource
from papita_txnsmodel.model.ingestion import IngestionConnection, IngestionRun, TransactionIngestionProvenance
from papita_txnsmodel.utils.classutils import MetaSingleton

if TYPE_CHECKING:
    from papita_txnsmodel.access.users.dto import UsersDTO


class TransactionIngestionProvenanceRepository(OwnedTableRepository, metaclass=MetaSingleton):
    """Owner-scoped access to ``transaction_ingestion_provenance``."""

    __expected_dto__ = TransactionIngestionProvenanceDTO

    def get_by_source_ref(
        self,
        *,
        owner: UsersDTO,
        ingestion_source: IngestionSource,
        source_ref: str,
        include_deleted: bool = True,
        **kwargs,
    ) -> TransactionIngestionProvenanceDTO | None:
        """Return the provenance row for an idempotency key, including soft-deleted rows."""
        if not source_ref:
            return None
        dao = TransactionIngestionProvenance
        frame = self.get_records(
            dao.owner_id == owner.id,
            dao.ingestion_source == ingestion_source,
            dao.source_ref == source_ref,
            owner=owner,
            dto_type=TransactionIngestionProvenanceDTO,
            include_deleted=include_deleted,
            limit=1,
            **kwargs,
        )
        return self._dataframe_row_to_dto(frame, TransactionIngestionProvenanceDTO, **kwargs)


class IngestionDeadLetterRepository(OwnedTableRepository, metaclass=MetaSingleton):
    """Owner-scoped access to ``ingestion_dead_letters``."""

    __expected_dto__ = IngestionDeadLetterDTO


class IngestionConnectionRepository(OwnedTableRepository, metaclass=MetaSingleton):
    """Owner-scoped access to ``ingestion_connections`` (PPT-083 / #177)."""

    __expected_dto__ = IngestionConnectionDTO

    def get_by_natural_key(
        self,
        *,
        owner: UsersDTO,
        provider: str,
        flow_name: str,
        include_deleted: bool = False,
        **kwargs,
    ) -> IngestionConnectionDTO | None:
        """Return the connection for ``(owner, provider, flow_name)`` if present."""
        if not provider or not flow_name:
            return None
        dao = IngestionConnection
        frame = self.get_records(
            dao.owner_id == owner.id,
            dao.provider == provider,
            dao.flow_name == flow_name,
            owner=owner,
            dto_type=IngestionConnectionDTO,
            include_deleted=include_deleted,
            limit=1,
            **kwargs,
        )
        return self._dataframe_row_to_dto(frame, IngestionConnectionDTO, **kwargs)


class IngestionRunRepository(OwnedTableRepository, metaclass=MetaSingleton):
    """Owner-scoped access to ``ingestion_runs`` (PPT-083 / #177)."""

    __expected_dto__ = IngestionRunDTO

    def get_latest(
        self,
        *,
        owner: UsersDTO,
        connection_id: UUID | None = None,
        **kwargs,
    ) -> IngestionRunDTO | None:
        """Return the most recently started run for the owner (optionally per connection)."""
        dao = IngestionRun
        filters = [dao.owner_id == owner.id]
        if connection_id is not None:
            filters.append(dao.connection_id == connection_id)
        frame = self.get_records(
            *filters,
            owner=owner,
            dto_type=IngestionRunDTO,
            order_by=[dao.started_at.desc()],
            limit=1,
            **kwargs,
        )
        return self._dataframe_row_to_dto(frame, IngestionRunDTO, **kwargs)
