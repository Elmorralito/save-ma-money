"""Access layer for ingestion provenance and dead-letter rows (PPT-078)."""

from papita_txnsmodel.access.ingestion.dto import IngestionDeadLetterDTO, TransactionIngestionProvenanceDTO
from papita_txnsmodel.access.ingestion.repository import (
    IngestionDeadLetterRepository,
    TransactionIngestionProvenanceRepository,
)

__all__ = [
    "IngestionDeadLetterDTO",
    "IngestionDeadLetterRepository",
    "TransactionIngestionProvenanceDTO",
    "TransactionIngestionProvenanceRepository",
]
