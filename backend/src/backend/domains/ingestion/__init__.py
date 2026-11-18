"""Ingestion vertical slice (models, provenance, bridge, status service, router)."""

from papita_txnsapi.routers.v1.ingestion import router
from papita_txnsmodel.model.ingestion import (
    IngestionConnection,
    IngestionDeadLetter,
    IngestionRun,
    TransactionIngestionProvenance,
)
from papita_txnsmodel.services.ingestion import (
    IngestionBridgeService,
    IngestTransactionRequest,
    IngestTransactionResult,
)
from papita_txnsmodel.services.ingestion_status import IngestionConnectionService, IngestionRunService

__all__ = [
    "IngestTransactionRequest",
    "IngestTransactionResult",
    "IngestionBridgeService",
    "IngestionConnection",
    "IngestionConnectionService",
    "IngestionDeadLetter",
    "IngestionRun",
    "IngestionRunService",
    "TransactionIngestionProvenance",
    "router",
]
