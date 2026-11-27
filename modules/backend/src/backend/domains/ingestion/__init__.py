"""Ingestion vertical slice (models, provenance, bridge, runner, email parsers/source, CLI, router)."""

from papita_ingestor_core.importers.base import BaseBatchImporter
from papita_ingestor_core.importers.ibkr import IBKRStatementImporter
from papita_ingestor_core.parsers.base import BaseRecordParser, select_parser
from papita_ingestor_core.plugins import PluginKind, PluginManifest
from papita_ingestor_core.registry import ConnectorRegistry, get_default_registry
from papita_ingestor_core.runner.ingestion_runner import IngestionRunner
from papita_ingestor_core.sources.base import BaseIngestorSource
from papita_ingestor_core.types.records import FetchFilter, ParsedRecord, RawRecord, RunResult
from papita_ingestor_email.flows.email_flow import build_email_ingestion_flow, build_email_runner
from papita_ingestor_email.parsers import (
    BancolombiaParser,
    FallbackEmailParser,
    Global66Parser,
    NequiParser,
    NuParser,
    default_email_parsers,
)
from papita_ingestor_email.sources.gmail import GmailSource, create_gmail_source
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
from papita_txnsmodel.services.portfolio_import import NormalizedPortfolioBatch, PortfolioImportService

__all__ = [
    "BancolombiaParser",
    "BaseBatchImporter",
    "BaseIngestorSource",
    "BaseRecordParser",
    "ConnectorRegistry",
    "FallbackEmailParser",
    "FetchFilter",
    "Global66Parser",
    "GmailSource",
    "IBKRStatementImporter",
    "IngestTransactionRequest",
    "IngestTransactionResult",
    "IngestionBridgeService",
    "IngestionConnection",
    "IngestionConnectionService",
    "IngestionDeadLetter",
    "IngestionRun",
    "IngestionRunService",
    "IngestionRunner",
    "NequiParser",
    "NuParser",
    "NormalizedPortfolioBatch",
    "ParsedRecord",
    "PluginKind",
    "PluginManifest",
    "PortfolioImportService",
    "RawRecord",
    "RunResult",
    "TransactionIngestionProvenance",
    "build_email_ingestion_flow",
    "build_email_runner",
    "create_gmail_source",
    "default_email_parsers",
    "get_default_registry",
    "router",
    "select_parser",
]
