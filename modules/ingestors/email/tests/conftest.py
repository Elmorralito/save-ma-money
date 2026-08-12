"""Email plugin test fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from papita_ingestor_email.parsers import ensure_parsers_registered
from papita_ingestor_email.sources.gmail import ensure_registered

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))


@pytest.fixture(autouse=True)
def _ensure_gmail_registered() -> None:
    """Re-register after core suite ``SourceRegistry.clear()`` in shared pytest runs."""
    ensure_registered()
    ensure_parsers_registered()
