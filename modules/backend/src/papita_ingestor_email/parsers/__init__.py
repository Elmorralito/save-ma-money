"""Bank email parsers for email ingestion (PPT-098 / #261)."""

from __future__ import annotations

from papita_ingestor_core.parsers.base import BaseRecordParser
from papita_ingestor_email.parsers.bancolombia import BancolombiaParser
from papita_ingestor_email.parsers.fallback import FallbackEmailParser
from papita_ingestor_email.parsers.nequi import NequiParser


def default_email_parsers() -> list[BaseRecordParser]:
    """Return instantiated default email parsers (Bancolombia, Nequi, Fallback)."""
    return [
        BancolombiaParser(),
        NequiParser(),
        FallbackEmailParser(),
    ]


__all__ = [
    "BancolombiaParser",
    "FallbackEmailParser",
    "NequiParser",
    "default_email_parsers",
]
