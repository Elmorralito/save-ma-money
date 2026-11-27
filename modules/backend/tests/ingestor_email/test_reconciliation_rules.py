"""Unit tests for Bancolombia, Nu, and Global66 financial reconciliation rules."""

from __future__ import annotations

from papita_ingestor_core.types.records import RawRecord
from papita_ingestor_email.parsers.bancolombia import BancolombiaParser
from papita_ingestor_email.parsers.global66 import Global66Parser
from papita_ingestor_email.parsers.nu import NuParser
from papita_txnsmodel.model.enums import IngestionSource, SettlementStatus, TransactionKind


def _raw(sender: str, subject: str, body: str, ref: str = "msg-1") -> RawRecord:
    return RawRecord(
        source_id="gmail",
        ingestion_source=IngestionSource.EMAIL,
        source_ref=ref,
        content=body.encode("utf-8"),
        metadata={"sender": sender, "subject": subject},
    )


def test_bancolombia_excludes_individual_visa_3541_purchases() -> None:
    parser = BancolombiaParser()
    record = _raw(
        "alertasynotificaciones@notificacionesbancolombia.com",
        "Alerta Bancolombia",
        "Bancolombia le informa que Compraste $317,398.00 en MERCADO PAGO con tu T.Cred *3541 el 14/11/2026 10:15.",
    )
    assert parser.can_parse(record) is False


def test_bancolombia_accepts_lump_sum_visa_payment_from_savings_7756() -> None:
    parser = BancolombiaParser()
    record = _raw(
        "alertasynotificaciones@notificacionesbancolombia.com",
        "Alerta Bancolombia",
        "Bancolombia le informa que Pagaste $2,207,730.00 a TARJETA VISA desde tu producto *7756 el 15/11/2026 11:00.",
    )
    assert parser.can_parse(record) is True
    parsed = parser.parse(record)
    assert parsed.transaction_kind == TransactionKind.EXPENSE
    assert parsed.amount == 2_207_730.0
    assert "visa-payment" in parsed.tags
    assert "account_last4:7756" in parsed.tags


def test_bancolombia_classifies_fiducuenta_and_loan_repayments_as_transfers() -> None:
    parser = BancolombiaParser()
    fidu = _raw(
        "alertasynotificaciones@notificacionesbancolombia.com",
        "Alerta Bancolombia",
        "Recibiste una transferencia por $5,000,000.00 de FIDUCUENTA *0801 en tu cuenta *7756 el 10/11/2026 09:00.",
    )
    parsed_fidu = parser.parse(fidu)
    assert parsed_fidu.transaction_kind == TransactionKind.TRANSFER
    assert "fiducuenta" in parsed_fidu.tags

    agro = _raw(
        "alertasynotificaciones@notificacionesbancolombia.com",
        "Alerta Bancolombia",
        "Recibiste una transferencia por $1,500,000.00 de AGROINVERSIONES RB SAS en tu cuenta *7756 el 29/10/2026 14:00.",
    )
    parsed_agro = parser.parse(agro)
    assert parsed_agro.transaction_kind == TransactionKind.TRANSFER
    assert "loan-repayment" in parsed_agro.tags


def test_bancolombia_tags_payroll_rent_and_aluna_hoa() -> None:
    parser = BancolombiaParser()
    payroll = parser.parse(
        _raw(
            "alertasynotificaciones@notificacionesbancolombia.com",
            "Alerta",
            "Recibiste una transferencia por $8,586,753.00 de SOFTSERVE COLOMBIA en tu cuenta *7756 el 13/11/2026 08:00.",
        )
    )
    assert payroll.transaction_kind == TransactionKind.INCOME
    assert "payroll" in payroll.tags

    rent = parser.parse(
        _raw(
            "alertasynotificaciones@notificacionesbancolombia.com",
            "Alerta",
            "Pagaste $3,511,100.00 a SOCIEDAD PRIVADA DEL ALQUILER desde tu producto *7756 el 15/11/2026 09:00.",
        )
    )
    assert rent.transaction_kind == TransactionKind.EXPENSE
    assert "rent" in rent.tags


def test_nu_handles_fuente_externa_card_4796_and_pse_global66() -> None:
    parser = NuParser()
    ext = _raw(
        "Nu <nu@nu.com.co>",
        "¡Ya entró tu pago!",
        "Recibimos el pago que hiciste de tu Tarjeta de crédito Nu.\n"
        "Tu pago fue de\n$1.200.000,00\n"
        "Lo has realizado el\n19 noviembre 2026 10:00:00 AM\n"
        "Producto origen\nFuente externa\n"
        "Producto destino\n**** **** **** 4796\n",
    )
    assert parser.can_parse(ext) is True
    parsed_ext = parser.parse(ext)
    assert parsed_ext.amount == 1_200_000.0
    assert "origin:external" in parsed_ext.tags
    assert "card_last4:4796" in parsed_ext.tags

    pse = _raw(
        "Nu <nu@nu.com.co>",
        "Pago por PSE confirmado",
        "Tu pago por PSE a Global66 fue de $2.000.000,00 el 14 noviembre 2026 2:15:00 PM.",
    )
    assert parser.can_parse(pse) is True
    parsed_pse = parser.parse(pse)
    assert parsed_pse.transaction_kind == TransactionKind.TRANSFER
    assert parsed_pse.amount == 2_000_000.0
    assert "global66-funding" in parsed_pse.tags

    # Individual card purchase is excluded (cashflow-only rule)
    card_buy = _raw(
        "Nu <nu@nu.com.co>",
        "Compra aprobada",
        "Compraste con tu tarjeta Nu $45.000,00 en RAPPI.",
    )
    assert parser.can_parse(card_buy) is False


def test_global66_parses_ibkr_usd_wire_and_cop_funding() -> None:
    parser = Global66Parser()
    wire = _raw(
        "notificaciones@global66.com",
        "Tu transferencia internacional está en camino",
        "Transaction No. 17020398 — $590.40 USD sent to Interactive Brokers (UMB National Association 913010600302) on November 14, 2026.",
    )
    parsed_wire = parser.parse(wire)
    assert parsed_wire.transaction_kind == TransactionKind.TRANSFER
    assert parsed_wire.amount == 590.40
    assert parsed_wire.currency == "USD"
    assert parsed_wire.reference_number == "17020398"
    assert "ibkr-wire" in parsed_wire.tags

    funding = _raw(
        "notificaciones@global66.com",
        "Recarga PSE acreditada",
        "Tu recarga por PSE de $2.000.000,00 COP fue acreditada en tu cuenta Global66.",
    )
    parsed_funding = parser.parse(funding)
    assert parsed_funding.transaction_kind == TransactionKind.TRANSFER
    assert parsed_funding.amount == 2_000_000.0
    assert parsed_funding.currency == "COP"
    assert parsed_funding.settlement_status == SettlementStatus.SETTLED
    assert "funding" in parsed_funding.tags


def test_match_template_for_payload_wires_by_parser_markers() -> None:
    import uuid
    from types import SimpleNamespace

    from papita_txnsmodel.services.ingestion import match_template_for_payload

    nu_id = uuid.uuid4()
    rent_id = uuid.uuid4()
    templates = [
        SimpleNamespace(
            id=nu_id,
            name="MC Nu - Monthly allowance",
            tags=["nu", "origin:drh391", "card_last4:3250"],
            planned_amount=1_975_723.0,
            active=True,
        ),
        SimpleNamespace(
            id=rent_id,
            name="Rent",
            tags=["bancolombia", "rent"],
            planned_amount=3_511_100.0,
            active=True,
        ),
    ]

    matched_nu = match_template_for_payload(
        templates=templates,
        description="Nu credit card payment · DRH391 → *3250",
        tags=["nu", "origin:drh391", "card_last4:3250"],
        transaction_kind=TransactionKind.EXPENSE,
        amount=1_915_580.0,
    )
    assert matched_nu is not None
    assert matched_nu.id == nu_id

    matched_rent = match_template_for_payload(
        templates=templates,
        description="Bancolombia expense · SOCIEDAD PRIVADA DEL ALQUILER · *7756",
        tags=["bancolombia", "account_last4:7756", "rent"],
        transaction_kind=TransactionKind.EXPENSE,
        amount=3_511_100.0,
    )
    assert matched_rent is not None
    assert matched_rent.id == rent_id
