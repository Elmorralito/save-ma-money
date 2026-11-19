"""Typed ingestion error taxonomy (PPT-079 / #173)."""

from __future__ import annotations


class IngestorError(Exception):
    """Base error for papita_ingestor_core."""


class IngestorConnectionError(IngestorError):
    """Source connect / disconnect / health failures."""


class IngestorFetchError(IngestorError):
    """Failures while fetching records from a source."""


class IngestorParseError(IngestorError):
    """Parser could not turn a RawRecord into a ParsedRecord."""


class IngestorValidationError(IngestorError):
    """Parsed payload failed validation (including bridge shape ValueError)."""


class IngestorPersistError(IngestorError):
    """Persist / dead-letter failures after a validated payload."""


__all__ = [
    "IngestorError",
    "IngestorConnectionError",
    "IngestorFetchError",
    "IngestorParseError",
    "IngestorValidationError",
    "IngestorPersistError",
]
