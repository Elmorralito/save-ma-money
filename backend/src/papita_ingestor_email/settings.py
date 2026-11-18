"""Gmail plugin settings (PPT-080 / #174).

Uses ``GMAIL_*`` env vars. Runner knobs (``fetch_limit``, ``dry_run``) stay on
``papita_ingestor_core.settings.BaseIngestorSettings`` (``PAPITA_INGESTOR_*``).

Intentionally does **not** subclass ``BaseIngestorSettings``: that base uses
``env_prefix=\"PAPITA_INGESTOR_\"``, while Gmail credentials must use ``GMAIL_*``.
Compose both settings objects at the runner/plugin boundary (R2).
"""

from __future__ import annotations

from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"
_DEFAULT_PROCESSED_LABEL = "PAPITA_PROCESSED"


class GmailSettings(BaseSettings):
    """Headless Gmail OAuth credentials and ack label (R2 default).

    Auth material (either is enough):

    - Env refresh-token path: ``client_id`` + ``client_secret`` + ``refresh_token``
    - Secondary path: ``token_file`` pointing at an authorized-user JSON
    """

    model_config = SettingsConfigDict(extra="ignore", env_prefix="GMAIL_")

    client_id: str | None = Field(default=None, min_length=1)
    client_secret: str | None = Field(default=None, min_length=1)
    refresh_token: str | None = Field(default=None, min_length=1)
    token_uri: str = Field(default=_DEFAULT_TOKEN_URI, min_length=1)
    processed_label: str = Field(default=_DEFAULT_PROCESSED_LABEL, min_length=1)
    token_file: str | None = None

    @model_validator(mode="after")
    def _require_auth_material(self) -> Self:
        has_token_file = bool(self.token_file and self.token_file.strip())
        has_env_triplet = bool(self.client_id and self.client_secret and self.refresh_token)
        if has_token_file or has_env_triplet:
            return self
        raise ValueError(
            "Gmail auth requires GMAIL_TOKEN_FILE or GMAIL_CLIENT_ID + GMAIL_CLIENT_SECRET + GMAIL_REFRESH_TOKEN"
        )


__all__ = ["GmailSettings"]
