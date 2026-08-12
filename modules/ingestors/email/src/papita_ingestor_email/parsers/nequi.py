"""Synthetic Nequi notification parser (PPT-081 / #175, R1=B).

Fixtures use public-shaped ``@nequi.com.co`` senders. This is **not** a Nu
parser — do not map ``nu@nu.com.co`` samples here.
"""

from __future__ import annotations

import re

from papita_ingestor_core.errors import IngestorParseError
from papita_ingestor_core.parsers.base import BaseRecordParser
from papita_ingestor_core.registry import ParserRegistry
from papita_ingestor_core.types.records import ParsedRecord, RawRecord
from papita_ingestor_email.parsers.amounts import parse_cop_amount, parse_spanish_datetime
from papita_ingestor_email.parsers.mime import extract_email_text, sender_address, subject_line
from papita_txnsmodel.model.enums import IngestionSource, TransactionKind

_SENDER_DOMAIN_RE = re.compile(r"@([a-z0-9.-]*nequi\.com\.co)\b", re.IGNORECASE)
_CLAIM_MARKERS_RE = re.compile(r"\b(Recibiste|Enviaste)\b", re.IGNORECASE)
_INCOME_RE = re.compile(
    r"Recibiste\s+\$[\d,]+(?:\.\d{1,2})?\s+de\s+(.+?)(?:\s+en\s+tu\s+Nequi|\s+el\s+|\.|$)",
    re.IGNORECASE,
)
_EXPENSE_RE = re.compile(
    r"Enviaste\s+\$[\d,]+(?:\.\d{1,2})?\s+a\s+(.+?)(?:\s+desde\s+tu\s+Nequi|\s+el\s+|\.|$)",
    re.IGNORECASE,
)


@ParserRegistry.register
class NequiParser(BaseRecordParser):
    """Parse synthetic Nequi alert emails into COP ``ParsedRecord`` values."""

    registry_id = "nequi-email"

    @property
    def parser_id(self) -> str:
        return self.registry_id

    @property
    def priority(self) -> int:
        return 90

    def can_parse(self, record: RawRecord) -> bool:
        if record.ingestion_source != IngestionSource.EMAIL:
            return False
        sender = sender_address(record.metadata.get("sender"), record.content)
        if not _SENDER_DOMAIN_RE.search(sender):
            return False
        # Explicitly reject Nu brand addresses even if somehow mixed in metadata.
        if re.search(r"@nu\.com\.co\b", sender, re.IGNORECASE):
            return False
        body = extract_email_text(record.content)
        subject = subject_line(record.metadata.get("subject"), record.content)
        haystack = f"{subject} {body}"
        return bool(_CLAIM_MARKERS_RE.search(haystack))

    def parse(self, record: RawRecord) -> ParsedRecord:
        if not (record.source_ref or "").strip():
            raise IngestorParseError("NequiParser requires RawRecord.source_ref")

        body = extract_email_text(record.content)
        subject = subject_line(record.metadata.get("subject"), record.content)
        haystack = f"{subject} {body}"

        kind, merchant = self._classify(haystack)
        amount = parse_cop_amount(haystack)
        if amount is None:
            raise IngestorParseError("NequiParser could not extract amount")

        description_parts = [f"Nequi {kind.value.lower()}"]
        if merchant:
            description_parts.append(merchant)

        return ParsedRecord(
            ingestion_source=record.ingestion_source,
            source_ref=record.source_ref,
            transaction_kind=kind,
            amount=amount,
            currency="COP",
            transaction_ts=parse_spanish_datetime(haystack),
            description=" · ".join(description_parts),
            tags=["nequi"],
        )

    @staticmethod
    def _classify(text: str) -> tuple[TransactionKind, str | None]:
        income = _INCOME_RE.search(text)
        if income:
            return TransactionKind.INCOME, income.group(1).strip(" .,;")

        expense = _EXPENSE_RE.search(text)
        if expense:
            return TransactionKind.EXPENSE, expense.group(1).strip(" .,;")

        raise IngestorParseError("NequiParser claimed record but no template matched")


__all__ = ["NequiParser"]
