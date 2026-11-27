"""Bancolombia Alertas y Notificaciones parser (PPT-081 / #175)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from papita_ingestor_core.errors import IngestorParseError
from papita_ingestor_core.parsers.base import BaseRecordParser
from papita_ingestor_core.types.records import ParsedRecord, RawRecord
from papita_ingestor_email.parsers.amounts import extract_masked_account, parse_cop_amount, parse_spanish_datetime
from papita_ingestor_email.parsers.mime import extract_email_text, sender_address, subject_line
from papita_txnsmodel.model.enums import IngestionSource, TransactionKind

_SENDER_DOMAIN_RE = re.compile(r"@([a-z0-9.-]*notificacionesbancolombia\.com)\b", re.IGNORECASE)
_CLAIM_MARKERS_RE = re.compile(
    r"\b(Recibiste\s+una\s+transferencia|Recibiste\s+un\s+pago|transferiste|Pagaste|Retiraste|Compraste"
    r"|Devoluci[oó]n|Inscribiste|Clave\s+Din[aá]mica|registraste\s+tu\s+llave)\b",
    re.IGNORECASE,
)

# Cashflow-only rule: exclude individual Visa credit card purchases/refunds (*3541)
# so variable card spend (Rappi, MELI, Amazon, Mercado Pago) is never double-counted.
_CARD_PURCHASE_EXCLUSION_RE = re.compile(
    r"(?:\b(?:Compraste|Compra\s+aprobada|Devoluci[oó]n|Recibiste\s+la\s+devoluci[oó]n)\b.*?\b(?:T\.?\s*Cred|Tarjeta\s+de\s+Cr[eé]dito|\*3541)\b"
    r"|\b(?:T\.?\s*Cred|Tarjeta\s+de\s+Cr[eé]dito)\s*\*?3541\b.*\b(?:Compraste|Compra|Devoluci[oó]n)\b)",
    re.IGNORECASE,
)
# Non-ledger Bancolombia security/account-maintenance alerts (cleanly ignored without DLQ).
_SECURITY_IGNORE_RE = re.compile(
    r"\b(Inscribiste\s+la\s+cuenta|inscribiste\s+al\s+servicio\s+de\s+Clave\s+Din[aá]mica"
    r"|registraste\s+tu\s+llave|actualizaste\s+tus\s+datos|cambio\s+de\s+clave)\b",
    re.IGNORECASE,
)

# Income patterns
_INCOME_POR_DE_RE = re.compile(
    r"recibiste\s+una\s+transferencia\s+por\s+\$[\d.,]+\s+de\s+(.+?)\s+en\s+tu\s+cuenta",
    re.IGNORECASE,
)
_INCOME_DE_POR_RE = re.compile(
    r"recibiste\s+una\s+transferencia\s+de\s+(.+?)\s+por\s+\$[\d.,]+\s+en\s+tu\s+cuenta",
    re.IGNORECASE,
)
_PAYROLL_INCOME_RE = re.compile(
    r"recibiste\s+un\s+pago\s+por\s+\$[\d.,]+\s+de\s+(.+?)\s+a\s+tu\s+cuenta",
    re.IGNORECASE,
)

# Fiducuenta investment withdrawal (internal transfer *0801 -> *7756)
_FIDUCUENTA_WITHDRAWAL_RE = re.compile(
    r"retiraste\s+\$\s*[\d.,]+\s+de\s+tu\s+cuenta\s+de\s+inversi[oó]n\s+\*?\s*(\d{4})",
    re.IGNORECASE,
)
# ATM cash withdrawal from Debit Card (T.Deb **5444)
_ATM_WITHDRAWAL_RE = re.compile(
    r"retiraste\s+\$\s*[\d.,]+\s+en\s+(.+?)\s+de\s+tu\s+T\.?\s*Deb",
    re.IGNORECASE,
)
# Debit card purchase (real cashflow expense from *7756 via T.Deb *5444)
_DEBIT_CARD_PURCHASE_RE = re.compile(
    r"compraste\s+(?:\$|COP)\s*[\d.,]+\s+en\s+(.+?)\s+con\s+tu\s+T\.?\s*Deb",
    re.IGNORECASE,
)

# Transfer / QR / Boton Bancolombia / Bill Payment patterns
_TRANSFER_LLAVE_RE = re.compile(
    r"transferiste\s+\$[\d.,]+\s+a\s+(?:la\s+llave\s+)?(.+?)\s+desde\s+tu\s+cuenta",
    re.IGNORECASE,
)
_TRANSFER_QR_RE = re.compile(
    r"transferiste\s+\$[\d.,]+\s+por\s+QR\s+desde\s+tu\s+cuenta\s+\*?\d{4}\s+a\s+(?:la\s+cuenta\s+)?(.+?)(?:,\s*el\b|\s+el\b|\.)",
    re.IGNORECASE,
)
_TRANSFER_BOTON_RE = re.compile(
    r"transferiste\s+\$[\d.,]+\s+por\s+Boton\s+Bancolombia\s+a\s+(.+?)\s+desde\s+producto",
    re.IGNORECASE,
)
_PAGASTE_QR_RE = re.compile(
    r"pagaste\s+\$[\d.,]+\s+por\s+c[oó]digo\s+QR\s+desde\s+tu\s+cuenta\s+\*?\d{4}\s+a\s+(?:la\s+llave\s+)?(.+?)(?:\s+el\b|\.)",
    re.IGNORECASE,
)
_EXPENSE_RE = re.compile(
    r"pagaste\s+\$[\d.,]+\s+a\s+(.+?)\s+desde\s+tu\s+(?:producto|cuenta)",
    re.IGNORECASE,
)

# Internal liquidity & principal repayment counterparties (booked as TRANSFER, not income/expense).
_INTERNAL_TRANSFER_COUNTERPARTIES_RE = re.compile(
    r"(?:fiducuenta|\*?\s*0801|3016663962|1017230391|DRH391|agroinversiones\s+rb|diamante\s+del\s+peluquero)",
    re.IGNORECASE,
)
_COUNTERPARTY_TAG_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bsoftserve\b", re.IGNORECASE), "payroll"),
    (re.compile(r"(?:coninsa\s+ramon|sociedad\s+privada\s+del\s+alquiler)", re.IGNORECASE), "rent"),
    (re.compile(r"(?:gou\s+payments|aluna\s+beach)", re.IGNORECASE), "aluna-hoa"),
    (re.compile(r"(?:85032061520|91208782334|10537103431)", re.IGNORECASE), "health"),
    (re.compile(r"(?:\bica\b|instit\s+colombiano\s+agropecuario)", re.IGNORECASE), "ica"),
    (re.compile(r"(?:tarjeta\s+visa|\*3541)", re.IGNORECASE), "visa-payment"),
    (re.compile(r"(?:fiducuenta|\*?\s*0801)", re.IGNORECASE), "fiducuenta"),
    (re.compile(r"(?:3016663962|1017230391|bre-?b|\bllave\b)", re.IGNORECASE), "bre-b"),
    (re.compile(r"(?:agroinversiones\s+rb|diamante\s+del\s+peluquero)", re.IGNORECASE), "loan-repayment"),
    (re.compile(r"\bboton\s+bancolombia\b", re.IGNORECASE), "boton-bancolombia"),
    (re.compile(r"\bc[oó]digo\s+QR\b|\bpor\s+QR\b", re.IGNORECASE), "qr"),
    (re.compile(r"\bT\.?\s*Deb\b", re.IGNORECASE), "debit-card"),
)


class BancolombiaParser(BaseRecordParser):
    """Parse Bancolombia alert emails into COP ``ParsedRecord`` values."""

    registry_id = "bancolombia-email"

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
        if _CARD_PURCHASE_EXCLUSION_RE.search(haystack):
            return False
        return bool(_CLAIM_MARKERS_RE.search(haystack))

    def parse_many(self, record: RawRecord) -> Sequence[ParsedRecord]:
        body = extract_email_text(record.content)
        subject = subject_line(record.metadata.get("subject"), record.content)
        haystack = f"{subject} {body}"
        if _SECURITY_IGNORE_RE.search(haystack) or _CARD_PURCHASE_EXCLUSION_RE.search(haystack):
            return ()
        return (self.parse(record),)

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
        for pattern, tag in _COUNTERPARTY_TAG_RULES:
            if pattern.search(haystack) and tag not in tags:
                tags.append(tag)

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
        # 1. Payroll income ("Recibiste un pago por $X de SOFTSERVE COLOM")
        payroll = _PAYROLL_INCOME_RE.search(text)
        if payroll:
            return TransactionKind.INCOME, payroll.group(1).strip(" .,;")

        # 2. Incoming transfers (both word orders)
        for pat in (_INCOME_POR_DE_RE, _INCOME_DE_POR_RE):
            income = pat.search(text)
            if income:
                counterparty = income.group(1).strip(" .,;")
                if _INTERNAL_TRANSFER_COUNTERPARTIES_RE.search(counterparty):
                    return TransactionKind.TRANSFER, counterparty
                return TransactionKind.INCOME, counterparty

        # 3. Fiducuenta investment withdrawal -> internal TRANSFER (*0801 -> *7756)
        fidu = _FIDUCUENTA_WITHDRAWAL_RE.search(text)
        if fidu:
            return TransactionKind.TRANSFER, f"Fiducuenta *{fidu.group(1)}"

        # 4. ATM cash withdrawal (T.Deb) -> EXPENSE
        atm = _ATM_WITHDRAWAL_RE.search(text)
        if atm:
            return TransactionKind.EXPENSE, f"ATM {atm.group(1).strip(' .,;')}"

        # 5. Debit card purchase (T.Deb) -> EXPENSE
        debit = _DEBIT_CARD_PURCHASE_RE.search(text)
        if debit:
            return TransactionKind.EXPENSE, debit.group(1).strip(" .,;")

        # 6. Boton Bancolombia -> EXPENSE
        boton = _TRANSFER_BOTON_RE.search(text)
        if boton:
            return TransactionKind.EXPENSE, boton.group(1).strip(" .,;")

        # 7. QR transfer ("Transferiste $X por QR ...") -> TRANSFER if internal, else EXPENSE
        qr_xfer = _TRANSFER_QR_RE.search(text)
        if qr_xfer:
            counterparty = qr_xfer.group(1).strip(" .,;")
            if _INTERNAL_TRANSFER_COUNTERPARTIES_RE.search(counterparty):
                return TransactionKind.TRANSFER, counterparty
            return TransactionKind.EXPENSE, f"QR {counterparty}"

        # 8. Llave / account transfer ("transferiste $X a [la llave] Y desde tu cuenta")
        transfer = _TRANSFER_LLAVE_RE.search(text)
        if transfer:
            return TransactionKind.TRANSFER, transfer.group(1).strip(" .,;")

        # 9. QR payment ("pagaste $X por codigo QR ...") -> EXPENSE
        qr_pay = _PAGASTE_QR_RE.search(text)
        if qr_pay:
            return TransactionKind.EXPENSE, f"QR {qr_pay.group(1).strip(' .,;')}"

        # 10. Direct bill/merchant payment ("Pagaste $X a Y desde tu producto") -> EXPENSE
        expense = _EXPENSE_RE.search(text)
        if expense:
            return TransactionKind.EXPENSE, expense.group(1).strip(" .,;")

        raise IngestorParseError("BancolombiaParser claimed record but no template matched")


__all__ = ["BancolombiaParser"]
