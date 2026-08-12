"""Bancolombia Alertas y Notificaciones parser (PPT-081 / #175)."""

from __future__ import annotations

import re

from papita_ingestor_core.errors import IngestorParseError
from papita_ingestor_core.parsers.base import BaseRecordParser
from papita_ingestor_core.registry import ParserRegistry
from papita_ingestor_core.types.records import ParsedRecord, RawRecord
from papita_ingestor_email.parsers.amounts import extract_masked_account, parse_cop_amount, parse_spanish_datetime
from papita_ingestor_email.parsers.mime import extract_email_text, sender_address, subject_line
from papita_txnsmodel.model.enums import IngestionSource, TransactionKind

_SENDER_DOMAIN_RE = re.compile(r"@([a-z0-9.-]*notificacionesbancolombia\.com)\b", re.IGNORECASE)
_CLAIM_MARKERS_RE = re.compile(r"\b(Recibiste\s+una\s+transferencia|transferiste|Pagaste)\b", re.IGNORECASE)
_INCOME_RE = re.compile(
    r"Recibiste\s+una\s+transferencia\s+por\s+\$[\d,]+(?:\.\d{1,2})?\s+de\s+(.+?)\s+en\s+tu\s+cuenta",
    re.IGNORECASE,
)
_TRANSFER_RE = re.compile(
    r"transferiste\s+\$[\d,]+(?:\.\d{1,2})?\s+a\s+(?:la\s+llave\s+)?(.+?)\s+desde\s+tu\s+cuenta",
    re.IGNORECASE,
)
_EXPENSE_RE = re.compile(
    r"Pagaste\s+\$[\d,]+(?:\.\d{1,2})?\s+a\s+(.+?)\s+desde\s+tu\s+producto",
    re.IGNORECASE,
)


@ParserRegistry.register
class BancolombiaParser(BaseRecordParser):
    """Parse Bancolombia alert emails into COP ``ParsedRecord`` values."""

    registry_id = "bancolombia-email"

    @property
    def parser_id(self) -> str:
        return self.registry_id

    @property
    def priority(self) -> int:
        return 100

    def can_parse(self, record: RawRecord) -> bool:
        if record.ingestion_source != IngestionSource.EMAIL:
            return False
        sender = sender_address(record.metadata.get("sender"), record.content)
        if not _SENDER_DOMAIN_RE.search(sender):
            return False
        body = extract_email_text(record.content)
        subject = subject_line(record.metadata.get("subject"), record.content)
        haystack = f"{subject} {body}"
        return bool(_CLAIM_MARKERS_RE.search(haystack))

    def parse(self, record: RawRecord) -> ParsedRecord:
        if not (record.source_ref or "").strip():
            raise IngestorParseError("BancolombiaParser requires RawRecord.source_ref")

        body = extract_email_text(record.content)
        subject = subject_line(record.metadata.get("subject"), record.content)
        haystack = f"{subject} {body}"

        kind, merchant = self._classify(haystack)
        amount = parse_cop_amount(haystack)
        if amount is None:
            raise IngestorParseError("BancolombiaParser could not extract amount")

        masked = extract_masked_account(haystack)
        tags = ["bancolombia"]
        if masked:
            tags.append(f"account_last4:{masked}")

        description_parts = [f"Bancolombia {kind.value.lower()}"]
        if merchant:
            description_parts.append(merchant)
        if masked:
            description_parts.append(f"*{masked}")

        return ParsedRecord(
            ingestion_source=record.ingestion_source,
            source_ref=record.source_ref,
            transaction_kind=kind,
            amount=amount,
            currency="COP",
            transaction_ts=parse_spanish_datetime(haystack),
            description=" · ".join(description_parts),
            tags=tags,
        )

    @staticmethod
    def _classify(text: str) -> tuple[TransactionKind, str | None]:
        income = _INCOME_RE.search(text)
        if income:
            return TransactionKind.INCOME, income.group(1).strip(" .,;")

        transfer = _TRANSFER_RE.search(text)
        if transfer:
            return TransactionKind.TRANSFER, transfer.group(1).strip(" .,;")

        expense = _EXPENSE_RE.search(text)
        if expense:
            return TransactionKind.EXPENSE, expense.group(1).strip(" .,;")

        raise IngestorParseError("BancolombiaParser claimed record but no template matched")


__all__ = ["BancolombiaParser"]
