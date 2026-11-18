"""Source-agnostic ingestion contracts (PPT-098 / #261)."""

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
from papita_ingestor_core.mapping import encode_raw_payload, to_ingest_transaction_request
from papita_ingestor_core.parsers import BaseRecordParser, select_parser
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
    "RawRecord",
    "RecordFailure",
    "RunResult",
    "encode_raw_payload",
    "select_parser",
    "to_ingest_transaction_request",
]
