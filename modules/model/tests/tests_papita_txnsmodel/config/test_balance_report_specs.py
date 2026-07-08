"""Tests for balance report YAML specs."""

import pytest

from papita_txnsmodel.access.balance_reports.exceptions import UnregisteredBalanceReportError
from papita_txnsmodel.config.balance_report_specs import get_report_spec, list_report_ids, resolve_report_view

EXPECTED_REPORT_IDS = (
    "account_balances",
    "owner_biannual_balances",
    "owner_monthly_balances",
    "owner_quarterly_balances",
    "owner_yearly_balances",
)


class TestBalanceReportSpecs:
    """YAML registry loader for balance reports."""

    def test_list_report_ids_contains_all_reports(self):
        """All five balance reports are registered."""
        assert list_report_ids() == list(EXPECTED_REPORT_IDS)

    def test_get_report_spec_returns_filters(self):
        """Each report exposes label, view, and filter metadata."""
        spec = get_report_spec("owner_monthly_balances")
        assert spec["view"] == "owner_monthly_balances"
        assert "balance_month" in spec["filters"]
        assert spec["filters"]["balance_month"]["max"] == 12

    def test_get_report_spec_unknown_report_raises(self):
        """Unregistered report_id cannot be resolved."""
        with pytest.raises(UnregisteredBalanceReportError, match="cannot be executed"):
            get_report_spec("not_a_report")

    def test_resolve_report_view_returns_yaml_view_name(self):
        """Executable views are resolved from the YAML registry."""
        assert resolve_report_view("account_balances") == "account_balances"

    def test_resolve_report_view_unregistered_report_raises(self):
        """Unregistered views cannot be executed."""
        with pytest.raises(UnregisteredBalanceReportError, match="balance_report_filters.yaml"):
            resolve_report_view("ghost_report")
