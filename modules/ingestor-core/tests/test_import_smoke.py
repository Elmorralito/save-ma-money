"""Smoke tests for papita-ingestor-core package install."""

from __future__ import annotations


def test_import_papita_ingestor_core() -> None:
    """Package root imports and exposes a version stub."""
    import papita_ingestor_core

    assert papita_ingestor_core.__version__
    assert isinstance(papita_ingestor_core.__version__, str)
