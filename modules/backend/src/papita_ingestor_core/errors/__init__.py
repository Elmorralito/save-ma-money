"""Error taxonomy exports for papita_ingestor_core."""

from __future__ import annotations

from papita_ingestor_core.errors.taxonomy import (
    IngestorConnectionError,
    IngestorError,
    IngestorFetchError,
    IngestorParseError,
    IngestorPersistError,
    IngestorPluginError,
    IngestorRateLimitError,
    IngestorValidationError,
)

__all__ = [
    "IngestorConnectionError",
    "IngestorError",
    "IngestorFetchError",
    "IngestorParseError",
    "IngestorPersistError",
    "IngestorPluginError",
    "IngestorRateLimitError",
    "IngestorValidationError",
]
