"""Abstract batch/statement importer plugin contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from papita_ingestor_core.plugins import PluginManifest
from papita_txnsmodel.model.enums import IngestionSource


class BaseBatchImporter(ABC):
    """Push/upload statement importer contract (e.g. brokerage CSV statements)."""

    @property
    @abstractmethod
    def importer_id(self) -> str:
        """Stable registry identity for this importer implementation."""

    @property
    def manifest(self) -> PluginManifest:
        """Non-secret plugin metadata for discovery and capability inspection."""
        return PluginManifest(
            plugin_id=self.importer_id,
            kind="batch_importer",
            ingestion_source=IngestionSource.CSV,
            supported_media_types=("text/csv",),
            capabilities=frozenset({"batch_import"}),
        )

    @abstractmethod
    def can_import(
        self,
        *,
        filename: str | None = None,
        content_type: str | None = None,
        sample: str | bytes = "",
    ) -> bool:
        """Return whether this importer recognizes the uploaded payload."""

    @abstractmethod
    def parse_statement(self, payload: str | bytes) -> Any:
        """Parse ``payload`` into a provider-agnostic batch DTO."""


__all__ = ["BaseBatchImporter"]
