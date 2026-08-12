"""Hybrid unrecognized-email parser (PPT-081 / #175 Soft Fallback).

Bank parsers win on priority. This class claims leftover email-shaped records
and raises ``IngestorParseError`` so the runner DLQs without inventing amounts.
When Fallback is omitted from ``instances``, unmatched records still raise
registry ``LookupError`` (same DLQ outcome).
"""

from __future__ import annotations

from papita_ingestor_core.errors import IngestorParseError
from papita_ingestor_core.parsers.base import BaseRecordParser
from papita_ingestor_core.registry import ParserRegistry
from papita_ingestor_core.types.records import ParsedRecord, RawRecord
from papita_ingestor_email.parsers.mime import sender_address
from papita_txnsmodel.model.enums import IngestionSource


@ParserRegistry.register
class FallbackEmailParser(BaseRecordParser):
    """Lowest-priority email leftover parser — never invents ``ParsedRecord`` amounts."""

    registry_id = "fallback-email"

    @property
    def parser_id(self) -> str:
        return self.registry_id

    @property
    def priority(self) -> int:
        return -100

    def can_parse(self, record: RawRecord) -> bool:
        """Claim email-shaped leftovers only (banks must outrank via priority)."""
        if record.ingestion_source != IngestionSource.EMAIL:
            return False
        sender = sender_address(record.metadata.get("sender"), record.content)
        # Require a From signal so non-email opaque payloads stay on LookupError.
        return bool(sender)

    def parse(self, record: RawRecord) -> ParsedRecord:
        raise IngestorParseError("unrecognized email")


__all__ = ["FallbackEmailParser"]
