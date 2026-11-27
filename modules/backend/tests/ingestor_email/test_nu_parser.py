"""Unit tests for ``NuParser`` using real Nu Colombia Gmail alert formats."""

from __future__ import annotations

from datetime import datetime

import pytest

from papita_ingestor_core.errors import IngestorParseError
from papita_ingestor_core.types.records import RawRecord
from papita_ingestor_email.parsers.nu import NuParser, parse_colombian_cop_amount
from papita_txnsmodel.model.enums import IngestionSource, TransactionKind

_NU_PAYMENT_NOV_06 = """\
¡Recibimos tu pago! Ya puedes estar relax.

Hola, David

Recibimos el pago que hiciste de tu Tarjeta de crédito Nu.

Tu pago fue de
$1.975.723,00

Lo has realizado el
06 noviembre 2026 4:24:05 PM

Tipo de transacción
Pago en linea

Costo de transacción
$0

Producto origen
DRH391

Producto destino
**** **** **** 3250

ID transacción
ab2e1376-eae2-3169-85a6-ceba1221efad

Tu próxima fecha de corte es
27 noviembre 2026
"""

_NU_PAYMENT_NOV_18 = """\
¡Recibimos tu pago! Ya puedes estar relax.

Hola, David

Recibimos el pago que hiciste de tu Tarjeta de crédito Nu.

Tu pago fue de
$1.915.580,00

Lo has realizado el
18 noviembre 2026 12:26:25 PM

Tipo de transacción
Pago en linea

Costo de transacción
$0

Producto origen
DRH391

Producto destino
**** **** **** 3250

ID transacción
b5cf1972-1aab-31df-855b-7eccaa48e2f6

Tu próxima fecha de corte es
27 noviembre 2026
"""

_NU_STATEMENT_SUMMARY = """\
Así viviste un NUevo mes con tu Tarjeta Nu

Hola, David
Te invitamos a explorar tu extracto de la Tarjeta de crédito Nu y descubrir el detalle de cada movimiento.

Pago mínimo
$194.446,00

Período facturado
27 septiembre - 28 octubre

Fecha de corte
28 octubre

Fecha límite de pago
17 noviembre
"""


def _raw(
    body: str, *, sender: str = "Nu <nu@nu.com.co>", subject: str = "¡Ya entró tu pago!", ref: str = "msg-1"
) -> RawRecord:
    return RawRecord(
        source_id="gmail",
        ingestion_source=IngestionSource.EMAIL,
        source_ref=ref,
        content=body.encode("utf-8"),
        metadata={"sender": sender, "subject": subject},
    )


def test_nu_parser_parses_nov_06_payment_confirmation() -> None:
    parser = NuParser()
    record = _raw(_NU_PAYMENT_NOV_06, ref="nu-pay-1")

    assert parser.can_parse(record) is True
    parsed = parser.parse(record)

    assert parsed.transaction_kind == TransactionKind.EXPENSE
    assert parsed.amount == 1_975_723.0
    assert parsed.currency == "COP"
    assert parsed.transaction_ts == datetime(2026, 11, 6, 16, 24, 5)
    assert parsed.reference_number == "ab2e1376-eae2-3169-85a6-ceba1221efad"
    assert parsed.description == "Nu credit card payment · DRH391 → *3250"
    assert parsed.tags == ["nu", "origin:drh391", "card_last4:3250"]


def test_nu_parser_parses_nov_18_noon_payment_confirmation() -> None:
    parser = NuParser()
    record = _raw(_NU_PAYMENT_NOV_18, ref="nu-pay-2")

    assert parser.can_parse(record) is True
    parsed = parser.parse(record)

    assert parsed.transaction_kind == TransactionKind.EXPENSE
    assert parsed.amount == 1_915_580.0
    assert parsed.currency == "COP"
    assert parsed.transaction_ts == datetime(2026, 11, 18, 12, 26, 25)
    assert parsed.reference_number == "b5cf1972-1aab-31df-855b-7eccaa48e2f6"
    assert parsed.description == "Nu credit card payment · DRH391 → *3250"


def test_nu_parser_ignores_monthly_statement_summary() -> None:
    parser = NuParser()
    record = _raw(
        _NU_STATEMENT_SUMMARY,
        subject="Llegó el extracto de tu tarjeta de crédito Nu",
        ref="nu-stmt-1",
    )

    assert parser.can_parse(record) is False


def test_nu_parser_rejects_other_bank_senders() -> None:
    parser = NuParser()
    record = _raw(_NU_PAYMENT_NOV_06, sender="alertas@notificacionesbancolombia.com")

    assert parser.can_parse(record) is False


def test_nu_parser_requires_source_ref() -> None:
    parser = NuParser()
    record = _raw(_NU_PAYMENT_NOV_06, ref="")

    with pytest.raises(IngestorParseError, match="source_ref"):
        parser.parse(record)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.975.723,00", 1_975_723.0),
        ("1.915.580,50", 1_915_580.5),
        ("1,975,723.00", 1_975_723.0),
        ("0", None),
        ("0,00", None),
    ],
)
def test_parse_colombian_cop_amount(raw: str, expected: float | None) -> None:
    assert parse_colombian_cop_amount(raw) == expected
