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
