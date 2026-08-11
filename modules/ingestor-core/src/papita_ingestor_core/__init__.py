"""papita-ingestor-core — source-agnostic ingestion contracts (PPT-079 / #173).

Business rules stay in ``papita_txnsmodel``. Concrete sources (email, bank-api)
live in plugin packages under ``modules/ingestors/`` and must not be imported
here.
"""

from __future__ import annotations

from papita_ingestor_core.__meta__ import __version__
from papita_ingestor_core.errors import (
    IngestorConnectionError,
    IngestorError,
    IngestorFetchError,
    IngestorParseError,
    IngestorPersistError,
    IngestorValidationError,
)
from papita_ingestor_core.flows import build_base_ingestion_flow
from papita_ingestor_core.mapping import encode_raw_payload, to_ingest_transaction_request
from papita_ingestor_core.parsers import BaseRecordParser
from papita_ingestor_core.registry import ParserRegistry, SourceRegistry
from papita_ingestor_core.runner import IngestionRunner
from papita_ingestor_core.settings import BaseIngestorSettings
from papita_ingestor_core.sources import BaseIngestorSource
from papita_ingestor_core.types import FetchFilter, ParsedRecord, RawRecord, RecordFailure, RunResult

__all__ = [
    "__version__",
    "BaseIngestorSettings",
    "BaseIngestorSource",
    "BaseRecordParser",
    "FetchFilter",
    "IngestorConnectionError",
    "IngestorError",
    "IngestorFetchError",
    "IngestorParseError",
    "IngestorPersistError",
    "IngestorValidationError",
    "IngestionRunner",
    "ParsedRecord",
    "ParserRegistry",
    "RawRecord",
    "RecordFailure",
    "RunResult",
    "SourceRegistry",
    "build_base_ingestion_flow",
    "encode_raw_payload",
    "to_ingest_transaction_request",
]
