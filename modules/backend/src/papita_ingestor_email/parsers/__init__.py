"""Bank email parsers for email ingestion (PPT-098 / #261)."""

from __future__ import annotations

from papita_ingestor_core.parsers.base import BaseRecordParser
from papita_ingestor_core.registry import ConnectorRegistry, get_default_registry
from papita_ingestor_email.parsers.bancolombia import BancolombiaParser
from papita_ingestor_email.parsers.fallback import FallbackEmailParser
from papita_ingestor_email.parsers.global66 import Global66Parser
from papita_ingestor_email.parsers.nequi import NequiParser
from papita_txnsmodel.model.enums import IngestionSource


def default_email_parsers(registry: ConnectorRegistry | None = None) -> list[BaseRecordParser]:
    """Return instantiated email parsers discovered via ``ConnectorRegistry``."""
    active_registry = registry or get_default_registry()
    return active_registry.get_parsers(ingestion_source=IngestionSource.EMAIL)


__all__ = [
    "BancolombiaParser",
    "FallbackEmailParser",
    "Global66Parser",
    "NequiParser",
    "default_email_parsers",
]
