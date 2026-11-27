"""Global66 international wire confirmation email parser (PPT-101 / #262)."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from papita_ingestor_core.errors import IngestorParseError
from papita_ingestor_core.parsers.base import BaseRecordParser
from papita_ingestor_core.types.records import ParsedRecord, RawRecord
from papita_ingestor_email.parsers.amounts import parse_spanish_datetime
from papita_ingestor_email.parsers.mime import extract_email_text, sender_address, subject_line
from papita_ingestor_email.parsers.nu import parse_colombian_cop_amount
from papita_txnsmodel.model.enums import IngestionSource, SettlementStatus, TransactionKind, TransactionStatus

_SENDER_DOMAIN_RE = re.compile(r"@([a-z0-9.-]*global66\.com)\b", re.IGNORECASE)
_IN_PROCESS_IGNORE_RE = re.compile(r"est[aá]\s+en\s+proceso|procesando\s+env[ií]o", re.IGNORECASE)
_CLAIM_MARKERS_RE = re.compile(
    r"\b(transferencia|env[ií]o|wire\s+transfer|international\s+transfer|transacci[oó]n|transaction\s+no"
    r"|recarga|fondeo|abono\s+pse)\b",
    re.IGNORECASE,
)
_FUNDING_MARKERS_RE = re.compile(r"\b(recarga|fondeo|abono|pse)\b", re.IGNORECASE)
_IBKR_MARKERS_RE = re.compile(r"\b(interactive\s+brokers|ibkr|umb\s+national|913010600302|U10600302)\b", re.IGNORECASE)
_SETTLED_MARKERS_RE = re.compile(
    r"\b(acreditad[ao]|settled|arrived\s+and\s+settled|depositad[ao]\s+en\s+destino)\b",
    re.IGNORECASE,
)
_AMOUNT_SUFFIX_CUR_RE = re.compile(
    r"(?:US\$|\$)?\s*([\d.,]+)\s*(USD|COP|EUR|GBP|MXN|CLP|PEN)\b",
    re.IGNORECASE,
)
_AMOUNT_PREFIX_CUR_RE = re.compile(
    r"\b(USD|COP|EUR|GBP|MXN|CLP|PEN)\s*\$?\s*([\d.,]+)",
    re.IGNORECASE,
)
_REF_RE = re.compile(
    r"(?:Transaction\s*No\.?|Transacci[oó]n\s*(?:No\.?|#)|Referencia|Reference)\s*[:#]?\s*([A-Z0-9-]{4,64})",
    re.IGNORECASE,
)
_DEST_RE = re.compile(
    r"(?:destined\s+for|to|para|beneficiario|destino)\s*[:\-]?\s*([A-Za-z0-9 /.&()-]{3,80})",
    re.IGNORECASE,
)
_EN_DATE_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(\d{1,2}),\s*(\d{4})(?:,?\s*(?:at\s+)?(\d{1,2}):(\d{2})\s*(AM|PM)?)?",
    re.IGNORECASE,
)
_ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})(?:[T\s](\d{2}:\d{2}(?::\d{2})?))?")


def _parse_amount_and_currency(text: str) -> tuple[float, str] | None:
    """Extract positive wire/funding amount and 3-letter ISO currency code."""
    match = _AMOUNT_SUFFIX_CUR_RE.search(text)
    if match:
        raw_num, cur = match.group(1), match.group(2).upper()
        val = parse_colombian_cop_amount(raw_num)
        if val is not None and val > 0:
            return val, cur

    match = _AMOUNT_PREFIX_CUR_RE.search(text)
    if match:
        cur, raw_num = match.group(1).upper(), match.group(2)
        val = parse_colombian_cop_amount(raw_num)
        if val is not None and val > 0:
            return val, cur

    return None


def _parse_wire_datetime(text: str) -> datetime | None:
    """Parse English, ISO, or Spanish timestamps from Global66 emails."""
    en_match = _EN_DATE_RE.search(text)
    if en_match:
        month_name, day_s, year_s, hour_s, minute_s, ampm = en_match.groups()
        date_str = f"{month_name} {day_s} {year_s}"
        if hour_s and minute_s:
            if ampm:
                parsed = datetime.strptime(f"{date_str} {hour_s}:{minute_s} {ampm.upper()}", "%B %d %Y %I:%M %p")
            else:
                parsed = datetime.strptime(f"{date_str} {hour_s}:{minute_s}", "%B %d %Y %H:%M")
        else:
            parsed = datetime.strptime(date_str, "%B %d %Y")
        return parsed.replace(tzinfo=timezone.utc)

    iso_match = _ISO_DATE_RE.search(text)
    if iso_match:
        date_part, time_part = iso_match.groups()
        if time_part:
            fmt = "%Y-%m-%d %H:%M:%S" if len(time_part) == 8 else "%Y-%m-%d %H:%M"
            return datetime.strptime(f"{date_part} {time_part}", fmt).replace(tzinfo=timezone.utc)
        return datetime.strptime(date_part, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    return parse_spanish_datetime(text)


class Global66Parser(BaseRecordParser):
    """Parse Global66 international wire emails into in-transit ``TRANSFER`` records."""

    registry_id = "global66-email"

    @property
    def supported_ingestion_sources(self) -> frozenset[IngestionSource]:
        return frozenset({IngestionSource.EMAIL})

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
        if _IN_PROCESS_IGNORE_RE.search(haystack):
            return False
        return bool(_CLAIM_MARKERS_RE.search(haystack))

    def parse(self, record: RawRecord) -> ParsedRecord:
        if not (record.source_ref or "").strip():
            raise IngestorParseError("Global66Parser requires RawRecord.source_ref")

        body = extract_email_text(record.content)
        subject = subject_line(record.metadata.get("subject"), record.content)
        haystack = f"{subject} {body}"

        parsed_amount = _parse_amount_and_currency(haystack)
        if parsed_amount is None:
            raise IngestorParseError("Global66Parser could not extract wire amount and currency")
        amount, currency = parsed_amount

        ref_match = _REF_RE.search(haystack)
        reference_number = ref_match.group(1).strip() if ref_match else None

        dest_match = _DEST_RE.search(haystack)
        destination = dest_match.group(1).strip(" .,;:") if dest_match else None

        is_settled = bool(_SETTLED_MARKERS_RE.search(haystack))
        is_funding = bool(_FUNDING_MARKERS_RE.search(haystack)) and currency == "COP"
        is_ibkr = bool(_IBKR_MARKERS_RE.search(haystack))
        settlement = SettlementStatus.SETTLED if (is_settled or is_funding) else SettlementStatus.IN_TRANSIT

        tags = [
            "global66",
            "funding" if is_funding else "international_wire",
            "settled" if (is_settled or is_funding) else "in_transit",
        ]
        if is_ibkr:
            tags.append("ibkr-wire")
        if reference_number:
            tags.append(f"ref:{reference_number}")

        description_parts = ["Global66 funding" if is_funding else "Global66 wire"]
        if destination:
            description_parts.append(destination)
        if reference_number:
            description_parts.append(f"#{reference_number}")

        return ParsedRecord(
            ingestion_source=record.ingestion_source,
            source_ref=record.source_ref,
            transaction_kind=TransactionKind.TRANSFER,
            amount=amount,
            currency=currency,
            transaction_ts=_parse_wire_datetime(haystack),
            status=TransactionStatus.COMPLETED,
            settlement_status=settlement,
            description=" · ".join(description_parts),
            reference_number=reference_number,
            tags=tags,
        )


__all__ = ["Global66Parser"]
