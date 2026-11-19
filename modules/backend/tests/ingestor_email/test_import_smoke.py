"""Smoke tests for papita-ingestor-email package install."""

from __future__ import annotations


def test_import_papita_ingestor_email() -> None:
    """Package root imports and exposes a version stub."""
    import papita_ingestor_email

    assert papita_ingestor_email.__version__
    assert isinstance(papita_ingestor_email.__version__, str)


def test_depends_on_ingestor_core() -> None:
    """Email plugin can import the core package (one-way dependency)."""
    import papita_ingestor_core
    import papita_ingestor_email

    assert papita_ingestor_core.__version__
    assert papita_ingestor_email.__version__
