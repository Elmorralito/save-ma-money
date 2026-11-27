"""Nu Colombia (``@nu.com.co``) email notification parser.

Supports:
- Credit card payment confirmations (``¡Ya entró tu pago!``)
- Cuenta Nu direct payments (``Pagaste en <MERCHANT> con Cuenta Nu``)
- Cuenta Nu PSE transactions (``¡Tu transacción por PSE fue exitosa!``)
- Nu CDT maturity net yield (``Ya tienes disponible el dinero de tu CDT Nu`` → ``INCOME``)

Non-ledger notifications (statements, OTPs, login alerts, Google Wallet, CDT open,
surveys, marketing) are cleanly ignored via :meth:`NuParser.parse_many` returning ``()``.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime

from papita_ingestor_core.errors import IngestorParseError
from papita_ingestor_core.parsers.base import BaseRecordParser
from papita_ingestor_core.types.records import ParsedRecord, RawRecord
from papita_ingestor_email.parsers.amounts import extract_masked_account, parse_spanish_datetime
from papita_ingestor_email.parsers.mime import extract_email_text, sender_address, subject_line
from papita_txnsmodel.model.enums import IngestionSource, TransactionKind

_SENDER_DOMAIN_RE = re.compile(r"@([a-z0-9.-]*nu\.com\.co)\b", re.IGNORECASE)

# Statement summaries, individual credit card purchases, OTPs, logins, CDT-open, and marketing
# must not be booked as ledger transactions.
_NON_LEDGER_EXCLUSION_RE = re.compile(
    r"(?:lleg[oó]\s+el\s+extracto|extracto\s+de\s+tu\s+(?:tarjeta|cuenta|moradita)|pago\s+m[ií]nimo"
    r"|as[ií]\s+viviste\s+un\s+nuevo\s+mes|compra\s+aprobada|compraste\s+con\s+tu\s+tarjeta"
    r"|abriste\s+una\s+nueva\s+sesi[oó]n|c[oó]digo\s+de\s+acceso|billetera\s+de\s+google"
    r"|invertiste\s+en\s+un\s+cdt\s+nu|reporte\s+anual|certificado\s+de\s+retenci[oó]n"
    r"|pagar[eé]\s+de\s+tu\s+tarjeta|nu\s+plus|recomendar[ií]as\s+nu|conoce\s+lo\s+[uú]ltimo"
    r"|se\s+transforma\s+en\s+platino|contrase[nñ]a\s+fue\s+actualizada|novedades\s+nu)",
    re.IGNORECASE,
)

# Executed ledger markers from @nu.com.co
_PAYMENT_CLAIM_RE = re.compile(
    r"(?:ya\s+entr[oó]\s+tu\s+pago|recibimos\s+(?:el|tu)\s+pago|tu\s+pago\s+fue\s+de"
    r"|pagaste\s+con\s+tu\s+cuenta\s+de\s+ahorros\s+nu|pagaste\s+en\s+.+?\s+con\s+cuenta\s+nu"
    r"|transacci[oó]n\s+por\s+pse\s+fue\s+exitosa|pago\s+(?:por|con)\s+pse|transferencia\s+pse"
    r"|el\s+rendimiento\s+neto\s+fue\s+de)",
    re.IGNORECASE,
)

_CDT_YIELD_RE = re.compile(r"rendimiento\s+neto\s+fue\s+de\s*:?\s*\$\s*([\d.,]+)", re.IGNORECASE)
_CDT_CAJITA_RE = re.compile(r"Cajita\s+([A-Za-zÁÉÍÓÚáéíóúÑñ0-9 ]{2,40})", re.IGNORECASE)
_CUENTA_NU_MERCHANT_RE = re.compile(r"Pagaste\s+en\s*:\s*([^\n\r]+?)(?:\s+La\s+cantidad|$)", re.IGNORECASE)
_CUENTA_NU_AMOUNT_RE = re.compile(r"La\s+cantidad\s+de\s*:\s*\$\s*([\d.,]+)", re.IGNORECASE)
_LABELED_PAYMENT_AMOUNT_RE = re.compile(r"Tu\s+pago\s+fue\s+de\s*:?\s*\$\s*([\d.,]+)", re.IGNORECASE)
_ANY_COP_AMOUNT_RE = re.compile(r"\$\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)")

_SPANISH_MONTHS: dict[str, int] = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

_SPANISH_WORD_DATE_RE = re.compile(
    r"(?P<d>\d{1,2})\s+(?:de\s+)?(?P<month>[a-záéíóú]+)\s+(?:de\s+)?(?P<y>\d{4})"
    r"(?:\s+(?P<h>\d{1,2}):(?P<min>\d{2})(?::(?P<s>\d{2}))?\s*(?P<ampm>AM|PM|a\.?\s*m\.?|p\.?\s*m\.?)?)?",
    re.IGNORECASE,
)

# Stop before "Producto" in case HTML table cells concatenate without whitespace (e.g. "DRH391Producto")
_ORIGIN_RE = re.compile(
    r"Producto\s+origen\s*:?\s*(Fuente\s+externa|DRH391|[A-Za-z0-9*._-]{3,24}?)(?=\s*Producto|\s|$)",
    re.IGNORECASE,
)
_DEST_RE = re.compile(r"Producto\s+destino\s*:?\s*([*0-9\s]{4,32})", re.IGNORECASE)
_GLOBAL66_DEST_RE = re.compile(r"\bglobal66\b", re.IGNORECASE)
_PSE_MARKER_RE = re.compile(r"\bpse\b", re.IGNORECASE)
_TXN_ID_RE = re.compile(
    r"ID\s+transacci[oó]n\s*:?\s*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[A-Za-z0-9_-]{8,64})",
    re.IGNORECASE,
)


def parse_colombian_cop_amount(raw: str) -> float | None:
    """Parse Colombian (``1.975.723,00``) or US (``1,975,723.00``) COP amount strings."""
    cleaned = raw.strip().replace(" ", "")
    if not cleaned:
        return None
    if "." in cleaned and "," in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts[-1]) == 2:
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        else:
            cleaned = cleaned.replace(",", "")
    elif "." in cleaned:
        parts = cleaned.split(".")
        if len(parts[-1]) == 3 and all(len(p) == 3 for p in parts[1:]):
            cleaned = "".join(parts)
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return value if value > 0 else None


def parse_nu_spanish_datetime(text: str) -> datetime | None:
    """Parse Nu Colombia Spanish month-name timestamps such as ``06 noviembre 2026 4:24:05 PM``."""
    match = _SPANISH_WORD_DATE_RE.search(text)
    if match is None:
        return parse_spanish_datetime(text)
    month_key = match.group("month").strip().lower()
    month = _SPANISH_MONTHS.get(month_key)
    if month is None:
        return parse_spanish_datetime(text)
    day = int(match.group("d"))
    year = int(match.group("y"))
    hour = int(match.group("h") or 0)
    minute = int(match.group("min") or 0)
    second = int(match.group("s") or 0)
    ampm_raw = (match.group("ampm") or "").lower().replace(".", "").replace(" ", "")
    if ampm_raw == "pm" and hour < 12:
        hour += 12
    elif ampm_raw == "am" and hour == 12:
        hour = 0
    try:
        return datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None


class NuParser(BaseRecordParser):
    """Parse Nu Colombia payment, PSE, and CDT yield emails into COP ``ParsedRecord`` values."""

    registry_id = "nu-email"

    @property
    def supported_ingestion_sources(self) -> frozenset[IngestionSource]:
        return frozenset({IngestionSource.EMAIL})

    @property
    def parser_id(self) -> str:
        return self.registry_id

    @property
    def priority(self) -> int:
        return 95

    def can_parse(self, record: RawRecord) -> bool:
        if record.ingestion_source != IngestionSource.EMAIL:
            return False
        sender = sender_address(record.metadata.get("sender"), record.content)
        if not _SENDER_DOMAIN_RE.search(sender):
            return False
        body = extract_email_text(record.content)
        subject = subject_line(record.metadata.get("subject"), record.content)
        haystack = f"{subject} {body}"
        if _NON_LEDGER_EXCLUSION_RE.search(haystack):
            return False
        return bool(_PAYMENT_CLAIM_RE.search(haystack))

    def parse_many(self, record: RawRecord) -> Sequence[ParsedRecord]:
        body = extract_email_text(record.content)
        subject = subject_line(record.metadata.get("subject"), record.content)
        haystack = f"{subject} {body}"
        if _NON_LEDGER_EXCLUSION_RE.search(haystack):
            return ()
        return (self.parse(record),)

    def parse(self, record: RawRecord) -> ParsedRecord:
        if not (record.source_ref or "").strip():
            raise IngestorParseError("NuParser requires RawRecord.source_ref")

        body = extract_email_text(record.content)
        subject = subject_line(record.metadata.get("subject"), record.content)
        haystack = f"{subject}\n{body}"

        # 1. Nu CDT Maturity Net Yield -> INCOME
        cdt_match = _CDT_YIELD_RE.search(haystack)
        if cdt_match:
            yield_amt = parse_colombian_cop_amount(cdt_match.group(1))
            if yield_amt is None:
                raise IngestorParseError("NuParser could not parse CDT yield amount")
            cajita_match = _CDT_CAJITA_RE.search(haystack)
            cajita = cajita_match.group(1).strip(" :.,;") if cajita_match else "Cuenta Nu"
            tags = ["nu", "cdt-yield", "interest"]
            if "emergencia" in cajita.lower():
                tags.append("cajita:emergency")
            elif "viaje" in cajita.lower():
                tags.append("cajita:travel")
            return ParsedRecord(
                ingestion_source=record.ingestion_source,
                source_ref=record.source_ref,
                transaction_kind=TransactionKind.INCOME,
                amount=yield_amt,
                currency="COP",
                transaction_ts=parse_nu_spanish_datetime(haystack),
                description=f"Nu CDT yield · {cajita}",
                tags=tags,
            )

        # 2. Direct Cuenta Nu merchant payment ("Pagaste en: MOVII SA La cantidad de: $...")
        merchant_match = _CUENTA_NU_MERCHANT_RE.search(haystack)
        if merchant_match:
            amt_match = _CUENTA_NU_AMOUNT_RE.search(haystack)
            amount = parse_colombian_cop_amount(amt_match.group(1)) if amt_match else self._extract_amount(haystack)
            if amount is None:
                raise IngestorParseError("NuParser could not extract Cuenta Nu payment amount")
            merchant = merchant_match.group(1).strip(" .,;")
            return ParsedRecord(
                ingestion_source=record.ingestion_source,
                source_ref=record.source_ref,
                transaction_kind=TransactionKind.EXPENSE,
                amount=amount,
                currency="COP",
                transaction_ts=parse_nu_spanish_datetime(haystack),
                description=f"Cuenta Nu payment · {merchant}",
                tags=["nu", "cuenta-nu", "origin:drh391"],
            )

        # 3. Credit card payment confirmation or PSE transfer
        amount = self._extract_amount(haystack)
        if amount is None:
            raise IngestorParseError("NuParser could not extract payment amount")

        origin_match = _ORIGIN_RE.search(haystack)
        origin = origin_match.group(1).strip() if origin_match else None

        dest_match = _DEST_RE.search(haystack)
        dest_last4 = extract_masked_account(dest_match.group(1)) if dest_match else extract_masked_account(haystack)

        ref_match = _TXN_ID_RE.search(haystack)
        reference_number = ref_match.group(1).strip()[:64] if ref_match else None

        is_pse_global66 = bool(_PSE_MARKER_RE.search(haystack) and _GLOBAL66_DEST_RE.search(haystack))
        kind = TransactionKind.TRANSFER if is_pse_global66 else TransactionKind.EXPENSE

        tags = ["nu"]
        if is_pse_global66:
            tags.extend(["pse", "global66-funding"])
        elif _PSE_MARKER_RE.search(haystack):
            tags.append("pse")
        if origin:
            if origin.lower() == "fuente externa":
                tags.append("origin:external")
            else:
                tags.append(f"origin:{origin.lower()}")
        if dest_last4:
            tags.append(f"card_last4:{dest_last4}")

        if is_pse_global66:
            description_parts = ["Nu PSE transfer · Global66"]
        elif _PSE_MARKER_RE.search(haystack):
            description_parts = ["Nu PSE payment"]
        else:
            description_parts = ["Nu credit card payment"]
            if origin and dest_last4:
                description_parts.append(f"{origin} → *{dest_last4}")
            elif origin:
                description_parts.append(origin)
            elif dest_last4:
                description_parts.append(f"*{dest_last4}")

        return ParsedRecord(
            ingestion_source=record.ingestion_source,
            source_ref=record.source_ref,
            transaction_kind=kind,
            amount=amount,
            currency="COP",
            transaction_ts=parse_nu_spanish_datetime(haystack),
            description=" · ".join(description_parts),
            reference_number=reference_number,
            tags=tags,
        )

    @staticmethod
    def _extract_amount(text: str) -> float | None:
        labeled = _LABELED_PAYMENT_AMOUNT_RE.search(text)
        if labeled:
            parsed = parse_colombian_cop_amount(labeled.group(1))
            if parsed is not None:
                return parsed
        for match in _ANY_COP_AMOUNT_RE.finditer(text):
            parsed = parse_colombian_cop_amount(match.group(1))
            if parsed is not None:
                return parsed
        return None


__all__ = ["NuParser", "parse_colombian_cop_amount", "parse_nu_spanish_datetime"]
