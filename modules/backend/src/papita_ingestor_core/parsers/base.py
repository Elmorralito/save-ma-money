"""Abstract record parser (PPT-079 / #173)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from papita_ingestor_core.types.records import ParsedRecord, RawRecord


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

    @abstractmethod
    def can_parse(self, record: RawRecord) -> bool:
        """Return whether this parser claims ``record``."""

    @abstractmethod
    def parse(self, record: RawRecord) -> ParsedRecord:
        """Convert ``record`` into a ``ParsedRecord`` (may still need FK completeness)."""

    def validate(self, parsed: ParsedRecord) -> ParsedRecord:
        """Optional post-parse validation; default is identity."""
        return parsed


def select_parser(record: RawRecord, parsers: Sequence[BaseRecordParser]) -> BaseRecordParser:
    """Return the highest-priority parser that claims ``record`` or raise ``LookupError``."""
    ordered = sorted(parsers, key=lambda p: p.priority, reverse=True)
    for parser in ordered:
        if parser.can_parse(record):
            return parser
    raise LookupError(f"No parser matched record source_id={record.source_id!r} source_ref={record.source_ref!r}")


__all__ = ["BaseRecordParser", "select_parser"]
