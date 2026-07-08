"""Tests for balance report filter validation."""

import uuid

import pytest

from papita_txnsmodel.access.balance_reports.filter_validation import validate_report_filters


class TestValidateReportFilters:
    """Filter validation against YAML specs."""

    def test_rejects_unknown_filter_keys(self):
        """Unknown keys are not accepted."""
        with pytest.raises(ValueError, match="Unknown filter keys"):
            validate_report_filters("account_balances", {"not_a_filter": 1})

    def test_coerces_uuid_filter(self):
        """UUID filters accept string values."""
        account_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        validated = validate_report_filters("account_balances", {"account_id": str(account_id)})
        assert validated["account_id"] == account_id

    def test_rejects_out_of_range_month(self):
        """Monthly period filters enforce min/max bounds."""
        with pytest.raises(ValueError, match="must be <="):
            validate_report_filters("owner_monthly_balances", {"balance_month": 13})

    def test_rejects_invalid_currency_length(self):
        """Currency filters enforce ISO-style length."""
        with pytest.raises(ValueError, match="at least 3 characters"):
            validate_report_filters("owner_yearly_balances", {"currency": "US"})
