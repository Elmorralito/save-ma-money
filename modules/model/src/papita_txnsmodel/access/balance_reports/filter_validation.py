"""Validate balance report query filters against the YAML registry."""

from __future__ import annotations

import uuid
from typing import Any

from papita_txnsmodel.config.balance_report_specs import get_report_spec


def validate_report_filters(report_id: str, filters: dict[str, Any] | None) -> dict[str, Any]:
    """Validate and coerce filter values for a balance report query.

    Args:
        report_id: Report identifier from the YAML registry.
        filters: Optional caller-supplied filter mapping.

    Returns:
        dict: Coerced filters ready for repository query parameters.

    Raises:
        UnregisteredBalanceReportError: If report_id is not registered in YAML.
        ValueError: If keys are invalid or values fail validation.
        TypeError: If a filter value has an unsupported type.
    """
    spec = get_report_spec(report_id)
    filter_specs: dict[str, Any] = spec.get("filters") or {}
    if not isinstance(filter_specs, dict):
        raise ValueError(f"Report '{report_id}' has an invalid filters definition.")

    incoming = filters or {}
    if not isinstance(incoming, dict):
        raise TypeError("filters must be a mapping when provided.")

    unknown_keys = set(incoming) - set(filter_specs)
    if unknown_keys:
        unknown = ", ".join(sorted(unknown_keys))
        raise ValueError(f"Unknown filter keys for report '{report_id}': {unknown}")

    validated: dict[str, Any] = {}
    for key, raw_value in incoming.items():
        if raw_value is None:
            continue

        field_spec = filter_specs[key]
        validated[key] = _coerce_filter_value(key=key, raw_value=raw_value, field_spec=field_spec)

    for key, field_spec in filter_specs.items():
        if field_spec.get("required") and key not in validated:
            raise ValueError(f"Filter '{key}' is required for report '{report_id}'.")

    return validated


def _coerce_filter_value(*, key: str, raw_value: Any, field_spec: dict[str, Any]) -> Any:
    """Coerce and range-check a single filter value."""
    field_type = field_spec.get("type")
    if field_type == "uuid":
        if isinstance(raw_value, uuid.UUID):
            return raw_value
        try:
            return uuid.UUID(str(raw_value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Filter '{key}' must be a valid UUID.") from exc

    if field_type == "integer":
        try:
            int_value = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Filter '{key}' must be an integer.") from exc

        minimum = field_spec.get("min")
        maximum = field_spec.get("max")
        if minimum is not None and int_value < minimum:
            raise ValueError(f"Filter '{key}' must be >= {minimum}.")
        if maximum is not None and int_value > maximum:
            raise ValueError(f"Filter '{key}' must be <= {maximum}.")
        return int_value

    if field_type == "string":
        if not isinstance(raw_value, str):
            raise TypeError(f"Filter '{key}' must be a string.")
        str_value = raw_value.strip()
        min_length = field_spec.get("min_length")
        max_length = field_spec.get("max_length")
        if min_length is not None and len(str_value) < min_length:
            raise ValueError(f"Filter '{key}' must be at least {min_length} characters.")
        if max_length is not None and len(str_value) > max_length:
            raise ValueError(f"Filter '{key}' must be at most {max_length} characters.")
        return str_value

    raise ValueError(f"Unsupported filter type '{field_type}' for key '{key}'.")
