"""Tests for MIME / HTML extraction helpers."""

from __future__ import annotations

from helpers_records import load_eml

from papita_ingestor_email.parsers.mime import extract_email_text, html_to_text


def test_html_to_text_strips_tags() -> None:
    assert html_to_text("<p>Hello <b>world</b></p>") == "Hello world"


def test_extract_email_text_prefers_html_part() -> None:
    text = extract_email_text(load_eml("bancolombia_income.eml"))
    assert "Recibiste una transferencia" in text
    assert "$20,000" in text
    assert "<html>" not in text.lower()
