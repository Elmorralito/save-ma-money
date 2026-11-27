"""Hybrid unrecognized-email parser (PPT-081 / #175 Soft Fallback).

Bank parsers win on priority. This class claims leftover email-shaped records
and raises ``IngestorParseError`` so the runner DLQs without inventing amounts.
When Fallback is omitted from ``instances``, unmatched records still raise
registry ``LookupError`` (same DLQ outcome).
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from papita_ingestor_core.errors import IngestorParseError
from papita_ingestor_core.parsers.base import BaseRecordParser
from papita_ingestor_core.types.records import ParsedRecord, RawRecord
from papita_ingestor_email.parsers.mime import extract_email_text, sender_address, subject_line
from papita_txnsmodel.model.enums import IngestionSource

# Known non-ledger notifications from tracked bank domains that should be cleanly
# acknowledged without polluting the dead-letter queue.
_KNOWN_NON_LEDGER_RE = re.compile(
    r"(?:lleg[oó]\s+el\s+extracto|extracto\s+de\s+tu\s+(?:tarjeta|cuenta|moradita)|el\s+extracto\s+de\s+tu\s+cuenta"
    r"|ya\s+tienes\s+tu\s+extracto|extractos\s+de\s+tus\s+cr[eé]ditos|certificado\s+tributario|certificado\s+de\s+retenci[oó]n"
    r"|reporte\s+anual\s+de\s+costos|abriste\s+una\s+nueva\s+sesi[oó]n|c[oó]digo\s+de\s+acceso|billetera\s+de\s+google"
    r"|invertiste\s+en\s+un\s+cdt\s+nu|nu\s+plus|recomendar[ií]as\s+nu|conoce\s+lo\s+[uú]ltimo|se\s+transforma\s+en\s+platino"
    r"|contrase[nñ]a\s+fue\s+actualizada|novedades\s+nu|pagar[eé]\s+de\s+tu\s+tarjeta"
    r"|est[aá]\s+en\s+proceso|procesando\s+env[ií]o"
    r"|clave\s+din[aá]mica|inscribiste\s+la\s+cuenta|registraste\s+tu\s+llave"
    r"|compraste\b.*?\b(?:T\.?\s*Cred|Tarjeta\s+de\s+Cr[eé]dito|\*3541)\b"
    r"|devoluci[oó]n\b.*?\b(?:T\.?\s*Cred|Tarjeta\s+de\s+Cr[eé]dito|\*3541)\b)",
    re.IGNORECASE | re.DOTALL,
)


class FallbackEmailParser(BaseRecordParser):
    """Lowest-priority email leftover parser — never invents ``ParsedRecord`` amounts."""

    registry_id = "fallback-email"

    @property
    def supported_ingestion_sources(self) -> frozenset[IngestionSource]:
        return frozenset({IngestionSource.EMAIL})

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

    def parse_many(self, record: RawRecord) -> Sequence[ParsedRecord]:
        body = extract_email_text(record.content)
        subject = subject_line(record.metadata.get("subject"), record.content)
        if _KNOWN_NON_LEDGER_RE.search(f"{subject} {body}"):
            return ()
        return (self.parse(record),)

    def parse(self, record: RawRecord) -> ParsedRecord:
        raise IngestorParseError("unrecognized email")


__all__ = ["FallbackEmailParser"]
