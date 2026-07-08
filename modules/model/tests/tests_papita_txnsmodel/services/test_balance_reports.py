"""Tests for BalanceReportsService."""

import uuid
from unittest.mock import MagicMock

import pandas as pd
import pytest

from papita_txnsmodel.access.balance_reports.exceptions import UnregisteredBalanceReportError
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.balance_reports import BalanceReportsService

_VALID_PASSWORD = "Password1!"


@pytest.fixture
def owner() -> UsersDTO:
    """Tenant user for owned-table service calls."""
    return UsersDTO(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        username="user_a_test",
        email="user_a@example.local",
        password=_VALID_PASSWORD,
    )


class TestBalanceReportsService:
    """Generic balance report read service."""

    def test_list_reports_returns_five_ids(self):
        """Service exposes all YAML-defined report ids."""
        service = BalanceReportsService()
        assert len(service.list_reports()) == 5
        assert "owner_quarterly_balances" in service.list_reports()

    def test_get_report_data_requires_owner(self):
        """Guard clause when owner is missing."""
        service = BalanceReportsService()
        with pytest.raises(ValueError, match="owner=UsersDTO is required"):
            service.get_report_data(report_id="account_balances", owner=None)  # type: ignore[arg-type]

    def test_get_report_data_rejects_unregistered_report(self, owner: UsersDTO):
        """Reports absent from YAML cannot be executed."""
        service = BalanceReportsService()
        with pytest.raises(UnregisteredBalanceReportError, match="cannot be executed"):
            service.get_report_data(report_id="ghost_report", owner=owner)

    def test_get_report_data_rejects_unknown_filter(self, owner: UsersDTO):
        """Invalid filter keys are rejected before repository access."""
        service = BalanceReportsService()
        with pytest.raises(ValueError, match="Unknown filter keys"):
            service.get_report_data(
                report_id="account_balances",
                owner=owner,
                filters={"bad_key": "x"},
            )

    def test_get_report_data_delegates_to_repository(self, owner: UsersDTO):
        """Validated filters are passed to the unified repository."""
        service = BalanceReportsService()
        repo = MagicMock()
        repo.query.return_value = pd.DataFrame([{"currency": "USD"}])
        service._repository = repo

        result = service.get_report_data(
            report_id="owner_yearly_balances",
            owner=owner,
            filters={"balance_year": 2025, "currency": "USD"},
        )

        repo.query.assert_called_once_with(
            report_id="owner_yearly_balances",
            owner=owner,
            filters={"balance_year": 2025, "currency": "USD"},
        )
        assert not result.empty
