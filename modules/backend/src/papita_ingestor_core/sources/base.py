"""Abstract ingestion source (PPT-079 / #173)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Self

from papita_ingestor_core.plugins import PluginManifest
from papita_ingestor_core.types.records import FetchFilter, RawRecord
from papita_txnsmodel.model.enums import IngestionSource


class BaseIngestorSource(ABC):
    """Source-agnostic fetch + acknowledge contract."""

    @property
    @abstractmethod
    def source_id(self) -> str:
        """Stable registry identity for this source implementation."""

    @property
    def manifest(self) -> PluginManifest:
        """Non-secret plugin metadata for discovery and capability inspection."""
        return PluginManifest(
            plugin_id=self.source_id,
            kind="pull_source",
            ingestion_source=IngestionSource.API,
            capabilities=frozenset({"acknowledge", "health_check"}),
        )

    def preflight(self) -> None:
        """Optional fail-fast startup check (e.g. required env credentials)."""

    @abstractmethod
    def connect(self) -> None:
        """Open the underlying connection / session."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close the underlying connection / session."""

    def health_check(self) -> bool:
        """Optional liveness probe; default assumes connected sources are healthy."""
        return True

    @abstractmethod
    def fetch(self, fetch_filter: FetchFilter | None = None) -> Iterable[RawRecord]:
        """Yield opaque records matching ``fetch_filter``."""

    @abstractmethod
    def acknowledge(self, record: RawRecord) -> None:
        """Mark ``record`` as successfully processed at the source."""

    def __enter__(self) -> Self:
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()


__all__ = ["BaseIngestorSource"]
