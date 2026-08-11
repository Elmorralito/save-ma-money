"""Parser registry with decorator registration and priority ordering."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from papita_ingestor_core.parsers.base import BaseRecordParser
from papita_ingestor_core.types.records import RawRecord

_P = TypeVar("_P", bound=type[BaseRecordParser])


class ParserRegistry:
    """In-memory registry of ``BaseRecordParser`` implementations."""

    _parsers: dict[str, type[BaseRecordParser]] = {}

    @classmethod
    def register(cls, parser_cls: _P | None = None, *, parser_id: str | None = None) -> Callable[[_P], _P] | _P:
        """Register a parser class via decorator or direct call."""

        def decorator(target: _P) -> _P:
            if not issubclass(target, BaseRecordParser):
                raise TypeError(f"{target!r} must subclass BaseRecordParser")
            identity = parser_id or getattr(target, "registry_id", None)
            if not identity or not isinstance(identity, str):
                raise ValueError(f"{target.__name__}: set class attribute registry_id or pass parser_id= to register()")
            if identity in cls._parsers:
                raise ValueError(f"parser_id already registered: {identity!r}")
            cls._parsers[identity] = target
            return target

        if parser_cls is not None:
            return decorator(parser_cls)
        return decorator

    @classmethod
    def get(cls, parser_id: str) -> type[BaseRecordParser]:
        """Return a registered parser class or raise ``KeyError``."""
        return cls._parsers[parser_id]

    @classmethod
    def all(cls) -> dict[str, type[BaseRecordParser]]:
        """Copy of registered parser classes."""
        return dict(cls._parsers)

    @classmethod
    def clear(cls) -> None:
        """Remove all registrations (tests)."""
        cls._parsers.clear()

    @classmethod
    def create_instances(cls) -> list[BaseRecordParser]:
        """Instantiate all registered parser classes once (for a single run)."""
        return [parser_cls() for parser_cls in cls._parsers.values()]

    @classmethod
    def select_for(cls, record: RawRecord, *, instances: list[BaseRecordParser] | None = None) -> BaseRecordParser:
        """Pick the highest-priority parser that ``can_parse`` ``record``.

        Tie-break: higher ``priority``, then lexicographic ``parser_id``.
        Prefer passing a cached ``instances`` list from ``create_instances()``.
        """
        candidates = instances if instances is not None else cls.create_instances()
        matching = [parser for parser in candidates if parser.can_parse(record)]
        if not matching:
            raise LookupError(f"No parser registered for record source_ref={record.source_ref!r}")
        matching.sort(key=lambda p: (-int(p.priority), p.parser_id))
        return matching[0]


__all__ = ["ParserRegistry"]
