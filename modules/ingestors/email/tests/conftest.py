"""Email plugin test fixtures."""

from __future__ import annotations

import pytest

from papita_ingestor_email.sources.gmail import ensure_registered


@pytest.fixture(autouse=True)
def _ensure_gmail_registered() -> None:
    """Re-register after core suite ``SourceRegistry.clear()`` in shared pytest runs."""
    ensure_registered()
