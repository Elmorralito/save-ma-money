"""Tests for Gmail query builder."""

from __future__ import annotations

from datetime import datetime, timezone

from papita_ingestor_core.types.records import FetchFilter
from papita_ingestor_email.sources.query import build_gmail_query


def test_query_excludes_processed_label_by_default() -> None:
    assert build_gmail_query(None, processed_label="PAPITA_PROCESSED") == "-label:PAPITA_PROCESSED"


def test_query_quotes_label_with_spaces() -> None:
    query = build_gmail_query(None, processed_label="PAPITA PROCESSED")
    assert query == '-label:"PAPITA PROCESSED"'


def test_query_includes_since_until_and_extra_filters() -> None:
    since = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)
    until = datetime(2024, 2, 1, 0, 0, tzinfo=timezone.utc)
    fetch_filter = FetchFilter(
        since=since,
        until=until,
        extra={"sender": "bank@example.com", "subject": "Alert", "q": "has:attachment"},
    )

    query = build_gmail_query(fetch_filter, processed_label="PAPITA_PROCESSED")

    assert "-label:PAPITA_PROCESSED" in query
    assert f"after:{int(since.timestamp())}" in query
    assert f"before:{int(until.timestamp())}" in query
    assert "from:bank@example.com" in query
    assert "subject:(Alert)" in query
    assert "has:attachment" in query


def test_query_supports_multiple_senders_subjects_and_source_label() -> None:
    fetch_filter = FetchFilter(
        extra={
            "source_label": "Finanzas/Bancos",
            "senders": ["notificacionesbancolombia.com", "nequi.com.co", "notificacionesbancolombia.com"],
            "subjects": ["Alertas y Notificaciones", "Transferencia"],
        }
    )

    query = build_gmail_query(fetch_filter, processed_label="PAPITA_PROCESSED")

    assert query == (
        "-label:PAPITA_PROCESSED "
        "label:Finanzas/Bancos "
        "from:(notificacionesbancolombia.com OR nequi.com.co) "
        'subject:("Alertas y Notificaciones" OR Transferencia)'
    )


def test_query_quotes_source_label_with_spaces_and_single_bancolombia_sender() -> None:
    fetch_filter = FetchFilter(
        extra={
            "source_label": "Bank Alerts",
            "senders": ["notificacionesbancolombia.com"],
            "subjects": ["Alertas y Notificaciones"],
        }
    )

    query = build_gmail_query(fetch_filter, processed_label="PAPITA_PROCESSED")

    assert query == (
        '-label:PAPITA_PROCESSED label:"Bank Alerts" '
        'from:notificacionesbancolombia.com subject:("Alertas y Notificaciones")'
    )


def test_query_merges_legacy_sender_with_senders_list_and_ignores_blank_terms() -> None:
    fetch_filter = FetchFilter(
        extra={
            "sender": "alertasynotificaciones@notificacionesbancolombia.com",
            "senders": [" ", "global66.com"],
            "subject": " ",
            "q": "  in:inbox  ",
        }
    )

    query = build_gmail_query(fetch_filter, processed_label="PAPITA_PROCESSED")

    assert query == (
        "-label:PAPITA_PROCESSED "
        "from:(alertasynotificaciones@notificacionesbancolombia.com OR global66.com) "
        "in:inbox"
    )


def test_query_parenthesizes_multi_token_raw_q_to_prevent_precedence_breakout() -> None:
    fetch_filter = FetchFilter(
        extra={
            "senders": ["notificacionesbancolombia.com"],
            "q": "in:inbox OR in:sent",
        }
    )
    query = build_gmail_query(fetch_filter, processed_label="PAPITA_PROCESSED")
    assert query == "-label:PAPITA_PROCESSED from:notificacionesbancolombia.com (in:inbox OR in:sent)"
