"""Configuration loaders and packaged data for papita_txnsmodel."""

# pylint: disable=undefined-all-variable

__all__ = [
    "BALANCE_REPORT_FILTERS_CONFIG",
    "get_report_spec",
    "list_report_ids",
    "resolve_report_view",
]


def __getattr__(name: str):
    """Lazy exports to avoid import cycles with access-layer exceptions."""
    if name == "BALANCE_REPORT_FILTERS_CONFIG":
        from papita_txnsmodel.config.constants import BALANCE_REPORT_FILTERS_CONFIG

        return BALANCE_REPORT_FILTERS_CONFIG
    if name in {"get_report_spec", "list_report_ids", "resolve_report_view"}:
        from papita_txnsmodel.config import balance_report_specs

        return getattr(balance_report_specs, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
