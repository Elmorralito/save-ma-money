"""Guard: core must not import Gmail / IMAP / HTML / email plugin packages."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_MODULES = {
    "google",
    "googleapiclient",
    "google_auth_oauthlib",
    "imaplib",
    "bs4",
    "beautifulsoup4",
    "papita_ingestor_email",
}


def _iter_python_files() -> list[Path]:
    root = Path(__file__).resolve().parents[1] / "src" / "papita_ingestor_core"
    return sorted(root.rglob("*.py"))


def _imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def test_core_has_no_plugin_or_provider_imports() -> None:
    offenders: list[str] = []
    for path in _iter_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        hits = _imported_roots(tree) & FORBIDDEN_MODULES
        if hits:
            offenders.append(f"{path.relative_to(path.parents[2])}: {sorted(hits)}")
    assert not offenders, "Forbidden imports in papita_ingestor_core:\n" + "\n".join(offenders)
