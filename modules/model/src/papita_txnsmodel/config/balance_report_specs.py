"""Load balance report filter specifications from packaged YAML."""

from __future__ import annotations

import importlib.resources as importlib_resources
from functools import lru_cache
from typing import Any

import yaml

from papita_txnsmodel import LIB_NAME
from papita_txnsmodel.access.balance_reports.exceptions import UnregisteredBalanceReportError
from papita_txnsmodel.config.constants import BALANCE_REPORT_FILTERS_CONFIG, BALANCE_REPORT_FILTERS_FILENAME

DEFAULT_ENCODING = "utf-8"


@lru_cache(maxsize=1)
def _load_reports() -> dict[str, dict[str, Any]]:
    """Parse and cache the reports map from the YAML config file."""
    config_path = importlib_resources.files(f"{LIB_NAME}.config.data").joinpath(BALANCE_REPORT_FILTERS_FILENAME)
    with config_path.open("r", encoding=DEFAULT_ENCODING) as reader:
        payload = yaml.load(reader, Loader=yaml.SafeLoader)

    if not isinstance(payload, dict):
        raise ValueError(f"{BALANCE_REPORT_FILTERS_FILENAME} must contain a mapping at the root.")

    reports = payload.get("reports")
    if not isinstance(reports, dict) or not reports:
        raise ValueError(f"{BALANCE_REPORT_FILTERS_FILENAME} must define a non-empty 'reports' mapping.")

    return reports


def list_report_ids() -> list[str]:
    """Return sorted report identifiers defined in the YAML registry."""
    return sorted(_load_reports().keys())


def get_report_spec(report_id: str) -> dict[str, Any]:
    """Return the specification dict for a single report.

    Args:
        report_id: Report key from the YAML `reports` map.

    Returns:
        dict: Report metadata including label, description, view, and filters.

    Raises:
        UnregisteredBalanceReportError: If the report_id is not defined in the YAML registry.
        ValueError: If the report spec entry is not a mapping.
    """
    reports = _load_reports()
    if report_id not in reports:
        raise UnregisteredBalanceReportError(report_id, known_reports=sorted(reports))

    spec = reports[report_id]
    if not isinstance(spec, dict):
        raise ValueError(f"Report spec for '{report_id}' must be a mapping.")

    return spec


def resolve_report_view(report_id: str) -> str:
    """Return the materialized view name for an executable balance report.

    Args:
        report_id: Report key from the YAML ``reports`` map.

    Returns:
        str: View name to query in schema ``papita_transactions``.

    Raises:
        UnregisteredBalanceReportError: If the report is not registered in YAML.
        ValueError: If the registered report spec omits a valid ``view`` field.
    """
    spec = get_report_spec(report_id)
    view_name = spec.get("view")
    if not isinstance(view_name, str) or not view_name.strip():
        raise ValueError(f"Report '{report_id}' in {BALANCE_REPORT_FILTERS_CONFIG} must define a non-empty 'view'.")

    return view_name.strip()
