"""Gmail OAuth2 ``BaseIngestorSource`` plugin (PPT-080 / #174)."""

from __future__ import annotations

import base64
import logging
from collections.abc import Iterable
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build

from papita_ingestor_core.errors import IngestorConnectionError, IngestorFetchError
from papita_ingestor_core.registry import SourceRegistry
from papita_ingestor_core.sources import BaseIngestorSource
from papita_ingestor_core.types.records import FetchFilter, RawRecord
from papita_ingestor_email.settings import GmailSettings
from papita_ingestor_email.sources.query import build_gmail_query
from papita_txnsmodel.model.enums import IngestionSource

logger = logging.getLogger(__name__)

_GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.modify"
_LIST_PAGE_SIZE = 100


@SourceRegistry.register
class GmailSource(BaseIngestorSource):
    """Headless Gmail source using refresh-token credentials (R2)."""

    registry_id = "gmail"

    def __init__(
        self,
        settings: GmailSettings | None = None,
        *,
        service: Resource | None = None,
    ) -> None:
        """Create a Gmail source.

        Args:
            settings: Gmail env settings. Loaded from ``GMAIL_*`` when omitted.
            service: Optional pre-built Gmail API resource (unit tests / DI).
        """
        self._settings = settings
        self._service = service
        self._owns_service = service is None
        self._label_id: str | None = None
        self._connected = False

    @property
    def source_id(self) -> str:
        return self.registry_id

    @property
    def settings(self) -> GmailSettings:
        """Lazy settings load so registry import does not require env secrets."""
        if self._settings is None:
            self._settings = GmailSettings()
        return self._settings

    def connect(self) -> None:
        created_service = False
        try:
            if self._service is None:
                self._service = self._build_service()
                self._owns_service = True
                created_service = True
            self._label_id = self._ensure_processed_label()
        except Exception as exc:
            if created_service:
                self._service = None
            self._label_id = None
            self._connected = False
            if isinstance(exc, IngestorConnectionError):
                raise
            raise IngestorConnectionError(f"Gmail connect failed: {exc}") from exc
        self._connected = True
        logger.info("Connected Gmail source (processed_label=%s)", self.settings.processed_label)

    def disconnect(self) -> None:
        if self._owns_service:
            self._service = None
        self._label_id = None
        self._connected = False

    def health_check(self) -> bool:
        if not self._connected or self._service is None:
            return False
        try:
            self._service.users().getProfile(userId="me").execute()
            return True
        except Exception as exc:
            logger.warning("Gmail health_check failed: %s", exc)
            return False

    def fetch(self, fetch_filter: FetchFilter | None = None) -> Iterable[RawRecord]:
        if not self._connected or self._service is None:
            raise IngestorFetchError("Gmail source is not connected")

        query = build_gmail_query(fetch_filter, processed_label=self.settings.processed_label)
        remaining = fetch_filter.limit if fetch_filter is not None else None
        page_token = fetch_filter.cursor if fetch_filter is not None else None

        try:
            yield from self._iter_messages(query=query, remaining=remaining, page_token=page_token)
        except IngestorFetchError:
            raise
        except Exception as exc:
            raise IngestorFetchError(f"Gmail fetch failed: {exc}") from exc

    def acknowledge(self, record: RawRecord) -> None:
        if not self._connected or self._service is None or self._label_id is None:
            raise IngestorConnectionError("Gmail source is not connected")
        if not record.source_ref:
            raise IngestorFetchError("acknowledge requires RawRecord.source_ref (Gmail message id)")

        try:
            self._service.users().messages().modify(
                userId="me",
                id=record.source_ref,
                body={"addLabelIds": [self._label_id]},
            ).execute()
        except Exception as exc:
            raise IngestorFetchError(f"Gmail acknowledge failed for {record.source_ref}: {exc}") from exc
        logger.debug("Acknowledged Gmail message %s with label %s", record.source_ref, self.settings.processed_label)

    def _build_service(self) -> Resource:
        credentials = self._build_credentials()
        if not credentials.valid:
            if not credentials.refresh_token:
                raise IngestorConnectionError("Gmail refresh token missing")
            credentials.refresh(Request())
        return build("gmail", "v1", credentials=credentials, cache_discovery=False)

    def _build_credentials(self) -> Credentials:
        """Load credentials from ``token_file`` when present, else env refresh-token (R2)."""
        settings = self.settings
        token_path = Path(settings.token_file).expanduser() if settings.token_file else None
        if token_path is not None and token_path.is_file():
            logger.debug("Loading Gmail credentials from token_file=%s", token_path)
            return Credentials.from_authorized_user_file(str(token_path), [_GMAIL_SCOPE])

        if not (settings.client_id and settings.client_secret and settings.refresh_token):
            raise IngestorConnectionError(
                "Gmail env credentials incomplete; set GMAIL_CLIENT_ID/SECRET/REFRESH_TOKEN "
                "or a readable GMAIL_TOKEN_FILE"
            )
        return Credentials(
            token=None,
            refresh_token=settings.refresh_token,
            token_uri=settings.token_uri,
            client_id=settings.client_id,
            client_secret=settings.client_secret,
            scopes=[_GMAIL_SCOPE],
        )

    def _ensure_processed_label(self) -> str:
        assert self._service is not None
        label_name = self.settings.processed_label
        listed = self._service.users().labels().list(userId="me").execute()
        for label in listed.get("labels", []):
            if label.get("name") == label_name:
                return str(label["id"])

        created = (
            self._service.users()
            .labels()
            .create(
                userId="me",
                body={
                    "name": label_name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                },
            )
            .execute()
        )
        label_id = created.get("id")
        if not label_id:
            raise IngestorConnectionError(f"Gmail label create returned no id for {label_name!r}")
        logger.info("Created Gmail label %s (%s)", label_name, label_id)
        return str(label_id)

    def _iter_messages(
        self,
        *,
        query: str,
        remaining: int | None,
        page_token: str | None,
    ) -> Iterable[RawRecord]:
        assert self._service is not None
        token = page_token
        left = remaining

        while True:
            page_size = _LIST_PAGE_SIZE if left is None else min(_LIST_PAGE_SIZE, left)
            response = (
                self._service.users()
                .messages()
                .list(userId="me", q=query, maxResults=page_size, pageToken=token)
                .execute()
            )
            messages = response.get("messages") or []
            if not messages:
                # Empty page: stop even if a nextPageToken is present (avoid hang).
                return

            for item in messages:
                message_id = item.get("id")
                if not message_id:
                    continue
                message = self._service.users().messages().get(userId="me", id=message_id, format="raw").execute()
                yield self._to_raw_record(message)
                if left is not None:
                    left -= 1
                    if left <= 0:
                        return

            token = response.get("nextPageToken")
            if not token:
                return

    def _to_raw_record(self, message: dict[str, Any]) -> RawRecord:
        message_id = str(message["id"])
        raw_b64 = message.get("raw") or ""
        content = base64.urlsafe_b64decode(raw_b64 + "=" * (-len(raw_b64) % 4))
        subject, sender, headers = _parse_mime_headers(content)
        metadata: dict[str, Any] = {
            "subject": subject,
            "sender": sender,
            "headers": headers,
            "thread_id": message.get("threadId"),
            "label_ids": message.get("labelIds") or [],
            "snippet": message.get("snippet"),
            "internal_date": message.get("internalDate"),
            "history_id": message.get("historyId"),
        }
        return RawRecord(
            source_id=self.source_id,
            source_ref=message_id,
            content=content,
            metadata=metadata,
            ingestion_source=IngestionSource.EMAIL,
        )


def create_gmail_source(settings: GmailSettings | None = None) -> GmailSource:
    """Factory for runners / Prefect wiring (PPT-082)."""
    ensure_registered()
    return GmailSource(settings=settings)


def ensure_registered() -> type[GmailSource]:
    """Idempotent registry ensure (core tests may ``SourceRegistry.clear()``)."""
    if "gmail" not in SourceRegistry.all():
        SourceRegistry.register(GmailSource)
    return GmailSource


def _parse_mime_headers(content: bytes) -> tuple[str | None, str | None, dict[str, str]]:
    if not content:
        return None, None, {}
    parsed = BytesParser(policy=policy.default).parsebytes(content)
    headers = {str(key): str(value) for key, value in parsed.items()}
    return parsed.get("Subject"), parsed.get("From"), headers


__all__ = ["GmailSource", "create_gmail_source", "ensure_registered"]
