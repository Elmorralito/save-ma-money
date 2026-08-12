"""Bank email parsers for ``papita_ingestor_email`` (PPT-081 / #175)."""

from __future__ import annotations

from papita_ingestor_core.registry import ParserRegistry
from papita_ingestor_email.parsers.bancolombia import BancolombiaParser
from papita_ingestor_email.parsers.fallback import FallbackEmailParser
from papita_ingestor_email.parsers.nequi import NequiParser

_PARSER_CLASSES = (
    BancolombiaParser,
    NequiParser,
    FallbackEmailParser,
)


def ensure_parsers_registered() -> dict[str, type]:
    """Idempotent ``ParserRegistry`` ensure (core tests may ``ParserRegistry.clear()``)."""
    registered = ParserRegistry.all()
    for parser_cls in _PARSER_CLASSES:
        identity = parser_cls.registry_id
        if identity not in registered:
            ParserRegistry.register(parser_cls)
    return {cls.registry_id: cls for cls in _PARSER_CLASSES}


ensure_parsers_registered()

__all__ = [
    "BancolombiaParser",
    "FallbackEmailParser",
    "NequiParser",
    "ensure_parsers_registered",
]
