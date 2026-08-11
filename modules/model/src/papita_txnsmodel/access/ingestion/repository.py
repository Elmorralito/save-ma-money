"""Repositories for ingestion provenance and dead letters (PPT-078 / #172)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from papita_txnsmodel.access.base.repository import OwnedTableRepository
from papita_txnsmodel.access.ingestion.dto import IngestionDeadLetterDTO, TransactionIngestionProvenanceDTO
from papita_txnsmodel.model.enums import IngestionSource
from papita_txnsmodel.model.ingestion import TransactionIngestionProvenance
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
