"""Hybrid plugin registry for sources, record parsers, and batch importers.

Supports both ``importlib.metadata.entry_points`` discovery (for installed /
packaged plugins) and explicit programmatic registration (for tests and DI).
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable
from importlib import metadata
from typing import Any

from papita_ingestor_core.errors.taxonomy import IngestorPluginError
from papita_ingestor_core.importers.base import BaseBatchImporter
from papita_ingestor_core.parsers.base import BaseRecordParser
from papita_ingestor_core.plugins import PluginKind, PluginManifest
from papita_ingestor_core.sources.base import BaseIngestorSource
from papita_txnsmodel.model.enums import IngestionSource

logger = logging.getLogger(__name__)

SOURCES_EP_GROUP = "papita.ingestor.sources"
PARSERS_EP_GROUP = "papita.ingestor.parsers"
IMPORTERS_EP_GROUP = "papita.ingestor.importers"

SourceFactory = Callable[..., BaseIngestorSource]
ParserFactory = Callable[..., BaseRecordParser]
ImporterFactory = Callable[..., BaseBatchImporter]


def _parse_enabled_allowlist(raw: str | None = None) -> set[str] | None:
    """Parse ``PAPITA_INGESTOR_ENABLED_PLUGINS`` CSV allowlist when set."""
    value = os.environ.get("PAPITA_INGESTOR_ENABLED_PLUGINS") if raw is None else raw
    if not value or not value.strip():
        return None
    items = {part.strip() for part in value.split(",") if part.strip()}
    return items or None


class ConnectorRegistry:
    """Thread-safe, deterministic registry for sources, parsers, and batch importers."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sources: dict[str, SourceFactory] = {}
        self._parsers: dict[str, ParserFactory] = {}
        self._importers: dict[str, ImporterFactory] = {}
        self._manifest_cache: dict[tuple[PluginKind, str], PluginManifest] = {}

    def register_source(
        self,
        plugin_id: str,
        factory: SourceFactory,
        *,
        replace: bool = False,
    ) -> None:
        """Register a pull-source class or zero/kwargs factory under ``plugin_id``."""
        self._register(self._sources, plugin_id, factory, kind="pull_source", replace=replace)

    def register_parser(
        self,
        plugin_id: str,
        factory: ParserFactory,
        *,
        replace: bool = False,
    ) -> None:
        """Register a record-parser class or factory under ``plugin_id``."""
        self._register(self._parsers, plugin_id, factory, kind="record_parser", replace=replace)

    def register_importer(
        self,
        plugin_id: str,
        factory: ImporterFactory,
        *,
        replace: bool = False,
    ) -> None:
        """Register a batch-importer class or factory under ``plugin_id``."""
        self._register(self._importers, plugin_id, factory, kind="batch_importer", replace=replace)

    def _register(
        self,
        bucket: dict[str, Any],
        plugin_id: str,
        factory: Any,
        *,
        kind: PluginKind,
        replace: bool,
    ) -> None:
        key = plugin_id.strip()
        if not key:
            raise IngestorPluginError(f"Empty plugin_id for {kind}")
        with self._lock:
            if key in bucket and not replace:
                raise IngestorPluginError(f"Duplicate {kind} plugin_id={key!r}")
            bucket[key] = factory
            self._manifest_cache.pop((kind, key), None)

    def discover_entry_points(
        self,
        *,
        allowlist: set[str] | None = None,
        replace: bool = False,
    ) -> int:
        """Load plugins declared via Python ``importlib.metadata.entry_points``.

        Args:
            allowlist: Optional set of permitted plugin IDs; falls back to
                ``PAPITA_INGESTOR_ENABLED_PLUGINS`` when ``None``.
            replace: Overwrite already-registered IDs when ``True``.

        Returns:
            Number of entry points registered.
        """
        effective_allowlist = allowlist if allowlist is not None else _parse_enabled_allowlist()
        loaded = 0
        group_map: tuple[tuple[str, Callable[..., None]], ...] = (
            (SOURCES_EP_GROUP, self.register_source),
            (PARSERS_EP_GROUP, self.register_parser),
            (IMPORTERS_EP_GROUP, self.register_importer),
        )
        for group, registrar in group_map:
            for ep in metadata.entry_points(group=group):
                if effective_allowlist is not None and ep.name not in effective_allowlist:
                    continue
                try:
                    factory = ep.load()
                except Exception as exc:  # pylint: disable=broad-except
                    logger.warning("Failed to load entry point %s:%s: %s", group, ep.name, exc)
                    continue
                registrar(ep.name, factory, replace=replace)
                loaded += 1
        return loaded

    def source_ids(self) -> list[str]:
        """Return sorted registered pull-source IDs."""
        return sorted(self._sources)

    def parser_ids(self) -> list[str]:
        """Return sorted registered record-parser IDs."""
        return sorted(self._parsers)

    def importer_ids(self) -> list[str]:
        """Return sorted registered batch-importer IDs."""
        return sorted(self._importers)

    def get_source(self, source_id: str, **kwargs: Any) -> BaseIngestorSource:
        """Instantiate the registered pull source for ``source_id``."""
        factory = self._sources.get(source_id)
        if factory is None:
            raise IngestorPluginError(
                f"Unknown pull_source plugin_id={source_id!r}; available: {sorted(self._sources)}"
            )
        return factory(**kwargs)

    def get_parsers(
        self,
        *,
        source_id: str | None = None,
        ingestion_source: IngestionSource | None = None,
    ) -> list[BaseRecordParser]:
        """Instantiate registered parsers filtered by source scope, sorted by priority."""
        instances: list[BaseRecordParser] = []
        for plugin_id in sorted(self._parsers):
            parser = self._parsers[plugin_id]()
            if (
                source_id is not None
                and parser.supported_source_ids is not None
                and source_id not in parser.supported_source_ids
            ):
                continue
            if (
                ingestion_source is not None
                and parser.supported_ingestion_sources is not None
                and ingestion_source not in parser.supported_ingestion_sources
            ):
                continue
            instances.append(parser)
        return sorted(instances, key=lambda p: (-p.priority, p.parser_id))

    def get_importer(self, importer_id: str, **kwargs: Any) -> BaseBatchImporter:
        """Instantiate the registered batch importer for ``importer_id``."""
        factory = self._importers.get(importer_id)
        if factory is None:
            raise IngestorPluginError(
                f"Unknown batch_importer plugin_id={importer_id!r}; available: {sorted(self._importers)}"
            )
        return factory(**kwargs)

    def resolve_importer(
        self,
        *,
        filename: str | None = None,
        content_type: str | None = None,
        sample: str | bytes = "",
    ) -> BaseBatchImporter:
        """Auto-detect the first registered batch importer matching the payload."""
        for plugin_id in sorted(self._importers):
            importer = self._importers[plugin_id]()
            if importer.can_import(filename=filename, content_type=content_type, sample=sample):
                return importer
        raise IngestorPluginError(f"No batch importer matched filename={filename!r} content_type={content_type!r}")

    def _resolve_manifest(self, kind: PluginKind, plugin_id: str, factory: Any) -> PluginManifest:
        cache_key = (kind, plugin_id)
        with self._lock:
            cached = self._manifest_cache.get(cache_key)
        if cached is not None:
            return cached
        class_manifest = getattr(factory, "PLUGIN_MANIFEST", None)
        manifest = class_manifest if isinstance(class_manifest, PluginManifest) else factory().manifest
        with self._lock:
            self._manifest_cache[cache_key] = manifest
        return manifest

    def list_manifests(self, *, kind: PluginKind | None = None) -> list[PluginManifest]:
        """Return cached non-secret manifests for registered plugins (lazy-safe)."""
        manifests: list[PluginManifest] = []
        if kind in (None, "pull_source"):
            for plugin_id in self.source_ids():
                manifests.append(self._resolve_manifest("pull_source", plugin_id, self._sources[plugin_id]))
        if kind in (None, "record_parser"):
            for plugin_id in self.parser_ids():
                manifests.append(self._resolve_manifest("record_parser", plugin_id, self._parsers[plugin_id]))
        if kind in (None, "batch_importer"):
            for plugin_id in self.importer_ids():
                manifests.append(self._resolve_manifest("batch_importer", plugin_id, self._importers[plugin_id]))
        return manifests


_DEFAULT_REGISTRY_LOCK = threading.Lock()
_DEFAULT_REGISTRY: ConnectorRegistry | None = None


def _register_builtin_plugins(registry: ConnectorRegistry, *, allowlist: set[str] | None) -> None:
    """Register in-repo built-in plugins as fallback when entry points are not installed."""
    from papita_ingestor_core.importers.ibkr import IBKRStatementImporter

    def _allowed(plugin_id: str) -> bool:
        return allowlist is None or plugin_id in allowlist

    if _allowed(IBKRStatementImporter.registry_id) and IBKRStatementImporter.registry_id not in registry.importer_ids():
        registry.register_importer(IBKRStatementImporter.registry_id, IBKRStatementImporter)

    try:
        from papita_ingestor_email.parsers.bancolombia import BancolombiaParser
        from papita_ingestor_email.parsers.fallback import FallbackEmailParser
        from papita_ingestor_email.parsers.global66 import Global66Parser
        from papita_ingestor_email.parsers.nequi import NequiParser
        from papita_ingestor_email.parsers.nu import NuParser
        from papita_ingestor_email.sources.gmail import GmailSource
    except ImportError:
        return

    if _allowed(GmailSource.registry_id) and GmailSource.registry_id not in registry.source_ids():
        registry.register_source(GmailSource.registry_id, GmailSource)

    for parser_cls in (BancolombiaParser, Global66Parser, NequiParser, NuParser, FallbackEmailParser):
        if _allowed(parser_cls.registry_id) and parser_cls.registry_id not in registry.parser_ids():
            registry.register_parser(parser_cls.registry_id, parser_cls)


def get_default_registry() -> ConnectorRegistry:
    """Return the thread-safe process-cached default ``ConnectorRegistry``."""
    global _DEFAULT_REGISTRY  # pylint: disable=global-statement
    with _DEFAULT_REGISTRY_LOCK:
        if _DEFAULT_REGISTRY is None:
            registry = ConnectorRegistry()
            allowlist = _parse_enabled_allowlist()
            registry.discover_entry_points(allowlist=allowlist)
            _register_builtin_plugins(registry, allowlist=allowlist)
            _DEFAULT_REGISTRY = registry
        return _DEFAULT_REGISTRY


def reset_default_registry() -> None:
    """Clear the cached default registry (test isolation helper)."""
    global _DEFAULT_REGISTRY  # pylint: disable=global-statement
    with _DEFAULT_REGISTRY_LOCK:
        _DEFAULT_REGISTRY = None


__all__ = [
    "ConnectorRegistry",
    "IMPORTERS_EP_GROUP",
    "PARSERS_EP_GROUP",
    "SOURCES_EP_GROUP",
    "get_default_registry",
    "reset_default_registry",
]
