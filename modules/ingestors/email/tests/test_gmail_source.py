"""Mocked unit tests for GmailSource (no live Google network)."""

from __future__ import annotations

import base64
from email.message import EmailMessage
from typing import Any
from unittest.mock import MagicMock

import pytest

from papita_ingestor_core.errors import IngestorConnectionError, IngestorFetchError
from papita_ingestor_core.registry import SourceRegistry
from papita_ingestor_core.types.records import FetchFilter, RawRecord
from papita_ingestor_email.settings import GmailSettings
from papita_ingestor_email.sources.gmail import GmailSource, create_gmail_source, ensure_registered
from papita_txnsmodel.model.enums import IngestionSource


def _settings() -> GmailSettings:
    return GmailSettings(
        client_id="client.apps.googleusercontent.com",
        client_secret="secret",
        refresh_token="refresh",
        processed_label="PAPITA_PROCESSED",
    )


def _raw_message_bytes(*, subject: str = "Txn alert", sender: str = "bank@example.com") -> bytes:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = "me@example.com"
    message.set_content("opaque body")
    return message.as_bytes()


def _gmail_api_message(message_id: str = "msg-1", **overrides: Any) -> dict[str, Any]:
    raw = base64.urlsafe_b64encode(_raw_message_bytes()).decode("ascii").rstrip("=")
    payload = {
        "id": message_id,
        "threadId": "thread-1",
        "labelIds": ["INBOX"],
        "snippet": "opaque body",
        "internalDate": "1700000000000",
        "historyId": "99",
        "raw": raw,
    }
    payload.update(overrides)
    return payload


def _mock_service(
    *,
    labels: list[dict[str, str]] | None = None,
    list_pages: list[dict[str, Any]] | None = None,
    messages: dict[str, dict[str, Any]] | None = None,
) -> MagicMock:
    service = MagicMock()
    users = service.users.return_value

    users.labels.return_value.list.return_value.execute.return_value = {"labels": labels or []}
    users.labels.return_value.create.return_value.execute.return_value = {
        "id": "Label_created",
        "name": "PAPITA_PROCESSED",
    }

    pages = list(list_pages if list_pages is not None else [{"messages": [{"id": "msg-1"}]}])
    users.messages.return_value.list.return_value.execute.side_effect = pages

    by_id = messages or {"msg-1": _gmail_api_message("msg-1")}

    def _get(**kwargs: Any) -> MagicMock:
        handle = MagicMock()
        handle.execute.return_value = by_id[kwargs["id"]]
        return handle

    users.messages.return_value.get.side_effect = _get
    users.messages.return_value.modify.return_value.execute.return_value = {}
    users.getProfile.return_value.execute.return_value = {"emailAddress": "me@example.com"}
    return service


def test_source_registry_get_gmail() -> None:
    ensure_registered()
    assert SourceRegistry.get("gmail") is GmailSource


def test_create_gmail_source_factory() -> None:
    source = create_gmail_source(settings=_settings())
    assert isinstance(source, GmailSource)
    assert source.source_id == "gmail"


def test_connect_creates_processed_label_when_missing() -> None:
    service = _mock_service(labels=[])
    source = GmailSource(settings=_settings(), service=service)

    source.connect()

    service.users.return_value.labels.return_value.create.assert_called_once()
    assert source.health_check() is True
    source.disconnect()
    assert source.health_check() is False


def test_connect_reuses_existing_label() -> None:
    service = _mock_service(labels=[{"id": "Label_9", "name": "PAPITA_PROCESSED"}])
    source = GmailSource(settings=_settings(), service=service)

    source.connect()

    service.users.return_value.labels.return_value.create.assert_not_called()
    assert source._label_id == "Label_9"  # noqa: SLF001 — intentional state check


def test_fetch_requires_connect() -> None:
    source = GmailSource(settings=_settings(), service=_mock_service())
    with pytest.raises(IngestorFetchError, match="not connected"):
        list(source.fetch())


def test_fetch_yields_raw_records_with_metadata() -> None:
    service = _mock_service()
    source = GmailSource(settings=_settings(), service=service)
    source.connect()

    records = list(source.fetch(FetchFilter(limit=1)))

    assert len(records) == 1
    record = records[0]
    assert record.source_id == "gmail"
    assert record.source_ref == "msg-1"
    assert record.ingestion_source == IngestionSource.EMAIL
    assert isinstance(record.content, (bytes, bytearray))
    assert record.metadata["subject"] == "Txn alert"
    assert record.metadata["sender"] == "bank@example.com"
    assert "Subject" in record.metadata["headers"]

    list_kwargs = service.users.return_value.messages.return_value.list.call_args.kwargs
    assert "-label:PAPITA_PROCESSED" in list_kwargs["q"]
    assert list_kwargs["maxResults"] == 1


def test_acknowledge_adds_processed_label() -> None:
    service = _mock_service(labels=[{"id": "Label_9", "name": "PAPITA_PROCESSED"}])
    source = GmailSource(settings=_settings(), service=service)
    source.connect()

    record = RawRecord(
        source_id="gmail",
        source_ref="msg-1",
        content=b"x",
        ingestion_source=IngestionSource.EMAIL,
    )
    source.acknowledge(record)

    modify_kwargs = service.users.return_value.messages.return_value.modify.call_args.kwargs
    assert modify_kwargs["id"] == "msg-1"
    assert modify_kwargs["body"] == {"addLabelIds": ["Label_9"]}


def test_acknowledge_requires_source_ref() -> None:
    service = _mock_service(labels=[{"id": "Label_9", "name": "PAPITA_PROCESSED"}])
    source = GmailSource(settings=_settings(), service=service)
    source.connect()
    record = RawRecord(source_id="gmail", content=b"x", ingestion_source=IngestionSource.EMAIL)

    with pytest.raises(IngestorFetchError, match="source_ref"):
        source.acknowledge(record)


def test_context_manager_connect_disconnect() -> None:
    service = _mock_service(labels=[{"id": "Label_9", "name": "PAPITA_PROCESSED"}])
    source = GmailSource(settings=_settings(), service=service)

    with source:
        assert source.health_check() is True
    assert source.health_check() is False


def test_connect_wraps_service_errors() -> None:
    service = MagicMock()
    service.users.return_value.labels.return_value.list.return_value.execute.side_effect = RuntimeError("boom")
    source = GmailSource(settings=_settings(), service=service)

    with pytest.raises(IngestorConnectionError, match="Gmail connect failed"):
        source.connect()


def test_connect_failure_clears_owned_service(monkeypatch: pytest.MonkeyPatch) -> None:
    """Failed label ensure must not leave a owned live client attached."""
    fake_service = _mock_service(labels=[])
    fake_service.users.return_value.labels.return_value.list.return_value.execute.side_effect = RuntimeError(
        "label boom"
    )

    source = GmailSource(settings=_settings())
    monkeypatch.setattr(source, "_build_service", lambda: fake_service)

    with pytest.raises(IngestorConnectionError, match="Gmail connect failed"):
        source.connect()

    assert source._service is None  # noqa: SLF001
    assert source._connected is False  # noqa: SLF001


def test_fetch_stops_on_empty_messages_page() -> None:
    """Empty list page terminates even if Google returns a nextPageToken."""
    service = _mock_service(list_pages=[{"messages": [], "nextPageToken": "ghost"}])
    source = GmailSource(settings=_settings(), service=service)
    source.connect()

    assert list(source.fetch()) == []
    service.users.return_value.messages.return_value.list.assert_called_once()


def test_build_credentials_prefers_token_file(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Secondary path: readable GMAIL_TOKEN_FILE loads authorized-user JSON."""
    token_path = tmp_path / "token.json"
    token_path.write_text(
        '{"token": "ya29.access", "refresh_token": "refresh", '
        '"token_uri": "https://oauth2.googleapis.com/token", '
        '"client_id": "id", "client_secret": "secret", '
        '"scopes": ["https://www.googleapis.com/auth/gmail.modify"]}',
        encoding="utf-8",
    )
    settings = GmailSettings(token_file=str(token_path))
    source = GmailSource(settings=settings)

    loaded: dict[str, object] = {}

    def _fake_from_file(path: str, scopes: list[str] | None = None) -> MagicMock:
        loaded["path"] = path
        loaded["scopes"] = scopes
        creds = MagicMock()
        creds.valid = True
        creds.refresh_token = "refresh"
        return creds

    monkeypatch.setattr(
        "papita_ingestor_email.sources.gmail.Credentials.from_authorized_user_file",
        _fake_from_file,
    )
    monkeypatch.setattr(
        "papita_ingestor_email.sources.gmail.build",
        lambda *args, **kwargs: _mock_service(labels=[{"id": "Label_9", "name": "PAPITA_PROCESSED"}]),
    )

    source.connect()

    assert loaded["path"] == str(token_path)
    assert source.health_check() is True
