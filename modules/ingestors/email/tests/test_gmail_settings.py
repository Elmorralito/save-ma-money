"""Unit tests for GmailSettings (R2 headless env + optional token_file)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from papita_ingestor_email.settings import GmailSettings


def test_gmail_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Loads GMAIL_* without requiring PAPITA_INGESTOR_* runner knobs."""
    monkeypatch.setenv("GMAIL_CLIENT_ID", "client.apps.googleusercontent.com")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "secret-value")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "refresh-token-value")
    monkeypatch.delenv("GMAIL_TOKEN_URI", raising=False)
    monkeypatch.delenv("GMAIL_PROCESSED_LABEL", raising=False)
    monkeypatch.delenv("GMAIL_TOKEN_FILE", raising=False)

    settings = GmailSettings()

    assert settings.client_id == "client.apps.googleusercontent.com"
    assert settings.client_secret == "secret-value"
    assert settings.refresh_token == "refresh-token-value"
    assert settings.token_uri == "https://oauth2.googleapis.com/token"
    assert settings.processed_label == "PAPITA_PROCESSED"
    assert settings.token_file is None


def test_gmail_settings_optional_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Optional token_file / label / token_uri override via env."""
    monkeypatch.setenv("GMAIL_CLIENT_ID", "id")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "refresh")
    monkeypatch.setenv("GMAIL_TOKEN_URI", "https://example.test/token")
    monkeypatch.setenv("GMAIL_PROCESSED_LABEL", "CUSTOM_LABEL")
    monkeypatch.setenv("GMAIL_TOKEN_FILE", "/tmp/gmail-token.json")

    settings = GmailSettings()

    assert settings.token_uri == "https://example.test/token"
    assert settings.processed_label == "CUSTOM_LABEL"
    assert settings.token_file == "/tmp/gmail-token.json"


def test_gmail_settings_token_file_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Secondary path: token_file alone satisfies auth material."""
    monkeypatch.delenv("GMAIL_CLIENT_ID", raising=False)
    monkeypatch.delenv("GMAIL_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GMAIL_REFRESH_TOKEN", raising=False)
    monkeypatch.setenv("GMAIL_TOKEN_FILE", "/tmp/gmail-token.json")

    settings = GmailSettings()

    assert settings.token_file == "/tmp/gmail-token.json"
    assert settings.refresh_token is None


def test_gmail_settings_requires_auth_material(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing both env triplet and token_file fails fast."""
    monkeypatch.delenv("GMAIL_CLIENT_ID", raising=False)
    monkeypatch.delenv("GMAIL_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GMAIL_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("GMAIL_TOKEN_FILE", raising=False)

    with pytest.raises(ValidationError):
        GmailSettings()
