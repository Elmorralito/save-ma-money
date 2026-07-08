"""Backward-compatible handler label aliases for registrar-era ingest."""

from __future__ import annotations

import warnings
from typing import FrozenSet, Tuple

LEGACY_HANDLER_LABELS: FrozenSet[str] = frozenset(
    {
        "types",
        "types_table",
        "type_table",
        "general_types",
        "identified_transactions",
        "identified_transactions_table",
    }
)

LEGACY_LABEL_TARGETS: dict[str, str] = {
    "types": "categories",
    "types_table": "categories_table",
    "type_table": "category_table",
    "general_types": "categories",
    "identified_transactions": "transaction_templates",
    "identified_transactions_table": "transaction_templates_table",
}


def legacy_labels() -> Tuple[str, ...]:
    """Return all registrar-compat labels that should emit deprecation warnings."""
    return tuple(sorted(LEGACY_HANDLER_LABELS))


def warn_legacy_label(label: str, *, handler_name: str) -> None:
    """Emit DeprecationWarning when a legacy handler label is resolved."""
    if label not in LEGACY_HANDLER_LABELS:
        return

    target = LEGACY_LABEL_TARGETS.get(label, "v3 handler labels")
    warnings.warn(
        f"Handler label '{label}' is deprecated; use '{target}' instead. " f"Resolved handler: {handler_name}.",
        DeprecationWarning,
        stacklevel=3,
    )
