"""Registry registration and parser priority selection."""

from __future__ import annotations

import pytest
from fakes import FakeParser, FakeSource, make_raw

from papita_ingestor_core.registry.parsers import ParserRegistry
from papita_ingestor_core.registry.sources import SourceRegistry


def test_source_registry_decorator() -> None:
    @SourceRegistry.register
    class Registered(FakeSource):
        registry_id = "registered-source"

    assert SourceRegistry.get("registered-source") is Registered


def test_parser_priority_selects_highest() -> None:
    class Low(FakeParser):
        registry_id = "aaa"

        def __init__(self) -> None:
            super().__init__(priority_value=1)

        @property
        def parser_id(self) -> str:
            return "aaa"

    class High(FakeParser):
        registry_id = "zzz"

        def __init__(self) -> None:
            super().__init__(priority_value=50)

        @property
        def parser_id(self) -> str:
            return "zzz"

    ParserRegistry.register(Low)
    ParserRegistry.register(High)
    selected = ParserRegistry.select_for(make_raw())
    assert selected.parser_id == "zzz"


def test_parser_select_raises_when_none_match() -> None:
    class Never(FakeParser):
        registry_id = "never"

        def can_parse(self, record) -> bool:  # type: ignore[override]
            return False

    with pytest.raises(LookupError):
        ParserRegistry.select_for(make_raw(), instances=[Never()])


def test_parser_registry_rejects_duplicate_id() -> None:
    @ParserRegistry.register
    class First(FakeParser):
        registry_id = "dup-parser"

    with pytest.raises(ValueError, match="already registered"):

        @ParserRegistry.register
        class Second(FakeParser):
            registry_id = "dup-parser"


def test_source_registry_rejects_duplicate_id() -> None:
    @SourceRegistry.register
    class First(FakeSource):
        registry_id = "dup-source"

    with pytest.raises(ValueError, match="already registered"):

        @SourceRegistry.register
        class Second(FakeSource):
            registry_id = "dup-source"
