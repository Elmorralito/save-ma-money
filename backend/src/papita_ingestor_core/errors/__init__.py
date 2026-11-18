"""Ingestor error types."""

from __future__ import annotations

from papita_ingestor_core.errors.taxonomy import (
    IngestorConnectionError,
    IngestorError,
    IngestorFetchError,
    IngestorParseError,
    IngestorPersistError,
    IngestorValidationError,
)

__all__ = [
    "IngestorConnectionError",
    "IngestorError",
    "IngestorFetchError",
    "IngestorParseError",
    "IngestorPersistError",
    "IngestorValidationError",
]
