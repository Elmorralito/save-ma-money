"""Abstract record parser (PPT-079 / #173)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from papita_ingestor_core.plugins import PluginManifest
from papita_ingestor_core.types.records import ParsedRecord, RawRecord
from papita_txnsmodel.model.enums import IngestionSource


class BaseRecordParser(ABC):
    """Parse opaque ``RawRecord`` values into bridge-aligned ``ParsedRecord``."""

    @property
    @abstractmethod
    def parser_id(self) -> str:
        """Stable registry identity for this parser implementation."""

    @property
    def priority(self) -> int:
        """Higher priority wins when multiple parsers ``can_parse`` the same record."""
        return 0

    @property
    def supported_source_ids(self) -> frozenset[str] | None:
        """Optional allowlist of ``RawRecord.source_id`` values; ``None`` accepts any."""
        return None

    @property
    def supported_ingestion_sources(self) -> frozenset[IngestionSource] | None:
        """Optional allowlist of ``RawRecord.ingestion_source`` values; ``None`` accepts any."""
        return None

    @property
    def manifest(self) -> PluginManifest:
        """Non-secret plugin metadata for discovery and capability inspection."""
        primary_source = (
            next(iter(self.supported_ingestion_sources))
            if self.supported_ingestion_sources
            else IngestionSource.EMAIL
        )
        return PluginManifest(
            plugin_id=self.parser_id,
            kind="record_parser",
            ingestion_source=primary_source,
            supported_source_ids=self.supported_source_ids,
            supported_ingestion_sources=self.supported_ingestion_sources,
        )

    @abstractmethod
    def can_parse(self, record: RawRecord) -> bool:
        """Return whether this parser claims ``record``."""

    @abstractmethod
    def parse(self, record: RawRecord) -> ParsedRecord:
        """Convert ``record`` into a ``ParsedRecord`` (may still need FK completeness)."""

    def parse_many(self, record: RawRecord) -> Sequence[ParsedRecord]:
        """Convert ``record`` into one or more ``ParsedRecord`` values.

        Default delegates to ``parse(record)`` for backward compatibility.
        """
        return [self.parse(record)]

    def validate(self, parsed: ParsedRecord) -> ParsedRecord:
        """Optional post-parse validation; default is identity."""
        return parsed


def _parser_supports_record(parser: BaseRecordParser, record: RawRecord) -> bool:
    """Return whether ``parser`` is scoped to handle ``record``'s source metadata."""
    if parser.supported_source_ids is not None and record.source_id not in parser.supported_source_ids:
        return False
    if (
        parser.supported_ingestion_sources is not None
        and record.ingestion_source not in parser.supported_ingestion_sources
    ):
        return False
    return True


def select_parser(record: RawRecord, parsers: Sequence[BaseRecordParser]) -> BaseRecordParser:
    """Return the highest-priority parser that claims ``record`` or raise ``LookupError``."""
    ordered = sorted(parsers, key=lambda p: (-p.priority, p.parser_id))
    for parser in ordered:
        if _parser_supports_record(parser, record) and parser.can_parse(record):
            return parser
    raise LookupError(f"No parser matched record source_id={record.source_id!r} source_ref={record.source_ref!r}")


__all__ = ["BaseRecordParser", "select_parser"]
