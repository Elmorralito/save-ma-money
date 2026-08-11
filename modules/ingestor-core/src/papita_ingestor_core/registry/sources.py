"""Source registry with decorator registration."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from papita_ingestor_core.sources.base import BaseIngestorSource

_S = TypeVar("_S", bound=type[BaseIngestorSource])


class SourceRegistry:
    """In-memory registry of ``BaseIngestorSource`` implementations."""

    _sources: dict[str, type[BaseIngestorSource]] = {}

    @classmethod
    def register(cls, source_cls: _S | None = None, *, source_id: str | None = None) -> Callable[[_S], _S] | _S:
        """Register a source class.

        Prefer ``@SourceRegistry.register`` when the class defines ``registry_id``,
        or ``@SourceRegistry.register(source_id=\"…\")``.
        """

        def decorator(target: _S) -> _S:
            if not issubclass(target, BaseIngestorSource):
                raise TypeError(f"{target!r} must subclass BaseIngestorSource")
            identity = source_id or getattr(target, "registry_id", None)
            if not identity or not isinstance(identity, str):
                raise ValueError(f"{target.__name__}: set class attribute registry_id or pass source_id= to register()")
            if identity in cls._sources:
                raise ValueError(f"source_id already registered: {identity!r}")
            cls._sources[identity] = target
            return target

        if source_cls is not None:
            return decorator(source_cls)
        return decorator

    @classmethod
    def get(cls, source_id: str) -> type[BaseIngestorSource]:
        """Return a registered source class or raise ``KeyError``."""
        return cls._sources[source_id]

    @classmethod
    def all(cls) -> dict[str, type[BaseIngestorSource]]:
        """Copy of registered source classes."""
        return dict(cls._sources)

    @classmethod
    def clear(cls) -> None:
        """Remove all registrations (tests)."""
        cls._sources.clear()


__all__ = ["SourceRegistry"]
