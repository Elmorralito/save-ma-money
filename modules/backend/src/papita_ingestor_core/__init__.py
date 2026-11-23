"""Source-agnostic ingestion contracts (PPT-098 / #261)."""

from __future__ import annotations

from papita_ingestor_core.__meta__ import __version__
from papita_ingestor_core.errors import (
    IngestorConnectionError,
    IngestorError,
    IngestorFetchError,
    IngestorParseError,
    IngestorPersistError,
    IngestorPluginError,
    IngestorRateLimitError,
    IngestorValidationError,
)
from papita_ingestor_core.importers.base import BaseBatchImporter
from papita_ingestor_core.mapping import encode_raw_payload, to_ingest_transaction_request
from papita_ingestor_core.parsers import BaseRecordParser, select_parser
from papita_ingestor_core.plugins import PluginKind, PluginManifest
from papita_ingestor_core.registry import ConnectorRegistry, get_default_registry, reset_default_registry
from papita_ingestor_core.run_status import execute_with_run_status
from papita_ingestor_core.runner import IngestionRunner
from papita_ingestor_core.settings import BaseIngestorSettings
from papita_ingestor_core.sources import BaseIngestorSource
from papita_ingestor_core.types import FetchFilter, ParsedRecord, RawRecord, RecordFailure, RunResult

__all__ = [
    "__version__",
    "BaseBatchImporter",
    "BaseIngestorSettings",
    "BaseIngestorSource",
    "BaseRecordParser",
    "ConnectorRegistry",
    "FetchFilter",
    "IngestorConnectionError",
    "IngestorError",
    "IngestorFetchError",
    "IngestorParseError",
    "IngestorPersistError",
    "IngestorPluginError",
    "IngestorRateLimitError",
    "IngestorValidationError",
    "IngestionRunner",
    "ParsedRecord",
    "PluginKind",
    "PluginManifest",
    "RawRecord",
    "RecordFailure",
    "RunResult",
    "encode_raw_payload",
    "execute_with_run_status",
    "get_default_registry",
    "reset_default_registry",
    "select_parser",
    "to_ingest_transaction_request",
]
