"""Shared fixtures and registry cleanup for papita_ingestor_core tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Allow `import fakes` from sibling modules (path has a hyphen; not a Python package).
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from papita_ingestor_core.registry.parsers import ParserRegistry
from papita_ingestor_core.registry.sources import SourceRegistry


@pytest.fixture(autouse=True)
def _clear_registries() -> None:
    """Isolate decorator registrations across tests."""
    SourceRegistry.clear()
    ParserRegistry.clear()
    yield
    SourceRegistry.clear()
    ParserRegistry.clear()
