"""Tests for expanded Bancolombia, Nu, Global66 parsers, non-ledger ignores, and EmailFKEnricher."""

from __future__ import annotations

import uuid

import pytest

from papita_ingestor_core.types.records import RawRecord
from papita_ingestor_email.enrichment import EmailFKEnricher
from papita_ingestor_email.parsers.bancolombia import BancolombiaParser
from papita_ingestor_email.parsers.fallback import FallbackEmailParser
from papita_ingestor_email.parsers.global66 import Global66Parser
from papita_ingestor_email.parsers.nu import NuParser
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import TransactionKind


def _mail(sender: str, subject: str, body: str, ref: str = "msg-1") -> RawRecord:
    raw = f"From: {sender}\r\nSubject: {subject}\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n{body}".encode()
    return RawRecord(source_id="gmail", source_ref=ref, content=raw, metadata={"sender": sender, "subject": subject})


def test_bancolombia_qr_boton_payroll_fiducuenta_atm_debit() -> None:
    p = BancolombiaParser()

    qr_pay = p.parse(
        _mail(
            "alertasynotificaciones@ayn.notificacionesbancolombia.com",
            "Alertas y Notificaciones",
            "Bancolombia: DANIEL RESTREPO HINCAPIE pagaste $34,000.00 por codigo QR desde tu cuenta *7756 a la llave 0093331854 el 25/11/2026 a las 18:41.",
        )
    )
    assert qr_pay.transaction_kind == TransactionKind.EXPENSE
    assert qr_pay.amount == pytest.approx(34000.0)

    boton = p.parse(
        _mail(
            "alertasynotificaciones@an.notificacionesbancolombia.com",
            "Alertas y Notificaciones",
            "Notificación Transaccional Bancolombia: Transferiste $72,000.00 por Boton Bancolombia a Wompi SAS desde producto *7756. 25/11/2026 17:05:09",
        )
    )
    assert boton.transaction_kind == TransactionKind.EXPENSE
    assert boton.amount == pytest.approx(72000.0)
    assert "boton-bancolombia" in boton.tags

    payroll = p.parse(
        _mail(
            "alertasynotificaciones@ayn.notificacionesbancolombia.com",
            "Alertas y Notificaciones",
            "Bancolombia: Recibiste un pago por $8,586,753.00 de SOFTSERVE COLOM a tu cuenta AHORROS, el 09:54 a las 13/11/2026.",
        )
    )
    assert payroll.transaction_kind == TransactionKind.INCOME
    assert payroll.amount == pytest.approx(8586753.0)
    assert "payroll" in payroll.tags

    fidu = p.parse(
        _mail(
            "alertasynotificaciones@notificacionesbancolombia.com",
            "Alertas y Notificaciones",
            "Retiraste $ 2,000,000.00 de tu cuenta de inversión * 0801 del fondo de inversión colectiva Fiducuenta el 2025/10/03 a las 11:02:51.",
        )
    )
    assert fidu.transaction_kind == TransactionKind.TRANSFER
    assert fidu.amount == pytest.approx(2000000.0)
    assert "fiducuenta" in fidu.tags

    atm = p.parse(
        _mail(
            "alertasynotificaciones@an.notificacionesbancolombia.com",
            "Alertas y Notificaciones",
            "Bancolombia: Retiraste $400.000,00 en EDSMGROSA1 de tu T.Deb **5444 el 21/11/2026 a las 17:10.",
        )
    )
    assert atm.transaction_kind == TransactionKind.EXPENSE
    assert atm.amount == pytest.approx(400000.0)

    debit = p.parse(
        _mail(
            "alertasynotificaciones@ayn.notificacionesbancolombia.com",
            "Alertas y Notificaciones",
            "Bancolombia: Compraste $93.214,00 en CARULLA SAO PAULO con tu T.Deb *5444, el 17/11/2026 a las 15:14.",
        )
    )
    assert debit.transaction_kind == TransactionKind.EXPENSE
    assert debit.amount == pytest.approx(93214.0)


def test_nu_cdt_yield_and_cuenta_nu_payment_and_ignores() -> None:
    p = NuParser()

    cdt = p.parse(
        _mail(
            "nu@nu.com.co",
            "Ya tienes disponible el dinero de tu CDT Nu.",
            "Estos son los detalles del CDT Nu que abriste en la Cajita Fondo Emergencia : Invertiste en CDT Nu $25.000.000,00 El rendimiento neto fue de $375.336,00",
        )
    )
    assert cdt.transaction_kind == TransactionKind.INCOME
    assert cdt.amount == pytest.approx(375336.0)
    assert "cdt-yield" in cdt.tags
    assert "cajita:emergency" in cdt.tags

    movii = p.parse(
        _mail(
            "nu@nu.com.co",
            "Pagaste en MOVII SA con Cuenta Nu",
            "Pagaste con tu Cuenta de ahorros Nu Pagaste en: MOVII SA La cantidad de: $3.800.000,00 Más el impuesto del 4xmil de: $15.200,00",
        )
    )
    assert movii.transaction_kind == TransactionKind.EXPENSE
    assert movii.amount == pytest.approx(3800000.0)

    # Non-ledger Global66 "en proceso" and Nu extracto are ignored cleanly by FallbackEmailParser
    g66_proc = _mail(
        "no-reply@sender.global66.com", "Pago recibido. Tu envío n.º 5827888 está en proceso", "Procesando envío"
    )
    assert Global66Parser().can_parse(g66_proc) is False
    assert list(FallbackEmailParser().parse_many(g66_proc)) == []


def test_email_fk_enricher_populates_valid_fks() -> None:
    bc_id = uuid.uuid4()
    fidu_id = uuid.uuid4()
    nu_id = uuid.uuid4()
    inc_sal = uuid.uuid4()
    exp_var = uuid.uuid4()
    exp_fix = uuid.uuid4()

    enricher = EmailFKEnricher(
        accounts=[
            {"id": bc_id, "name": "Savings Account Bancolombia"},
            {"id": fidu_id, "name": "Fiduciary Bancolombia"},
            {"id": nu_id, "name": "Cuenta Nu (DRH391)"},
        ],
        categories=[
            {"id": inc_sal, "name": "Salary & Fixed Income", "category_kind": "INCOME"},
            {"id": exp_var, "name": "Variable Spending", "category_kind": "EXPENSE"},
            {"id": exp_fix, "name": "Fixed Bills & Subscriptions", "category_kind": "EXPENSE"},
        ],
    )
    owner = UsersDTO.model_construct(id=uuid.uuid4(), username="tester1", email="t@example.com")

    p = BancolombiaParser()
    payroll = enricher(
        owner,
        p.parse(
            _mail(
                "alertasynotificaciones@ayn.notificacionesbancolombia.com",
                "Alertas y Notificaciones",
                "Bancolombia: Recibiste un pago por $8,586,753.00 de SOFTSERVE COLOM a tu cuenta AHORROS, el 09:54 a las 13/11/2026.",
            )
        ),
    )
    assert payroll.from_account_id is None
    assert payroll.to_account_id == bc_id
    assert payroll.category_id == inc_sal

    fidu = enricher(
        owner,
        p.parse(
            _mail(
                "alertasynotificaciones@notificacionesbancolombia.com",
                "Alertas y Notificaciones",
                "Retiraste $ 2,000,000.00 de tu cuenta de inversión * 0801 del fondo de inversión colectiva Fiducuenta el 2025/10/03 a las 11:02:51.",
            )
        ),
    )
    assert fidu.transaction_kind == TransactionKind.TRANSFER
    assert fidu.from_account_id == fidu_id
    assert fidu.to_account_id == bc_id
    assert fidu.category_id is None
