"""Tests for BalanceReportsHandler."""

import uuid
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.handlers.balance_reports import BalanceReportsHandler
from papita_txnsmodel.handlers.factory import HandlerFactory
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
        auth_provider="local",
    )


class TestBalanceReportsHandler:
    """Read-only handler for balance reports."""

    def test_labels_registered_in_factory(self):
        """Handler is discoverable via HandlerFactory."""
        HandlerFactory.load("papita_txnsmodel.handlers")
        handler_cls = HandlerFactory.get(("balance_reports",))
        assert handler_cls is BalanceReportsHandler

    def test_load_is_not_supported(self, owner: UsersDTO):
        """Read-only handler rejects load()."""
        handler = BalanceReportsHandler(service=BalanceReportsService())
        with pytest.raises(NotImplementedError, match="read-only"):
            handler.load(data=pd.DataFrame([]), owner=owner)

    def test_dump_requires_report_id_and_owner(self, owner: UsersDTO):
        """dump() validates required export parameters."""
        handler = BalanceReportsHandler(service=BalanceReportsService())
        with pytest.raises(ValueError, match="report_id is required"):
            handler.dump(owner=owner)

    @patch.object(BalanceReportsService, "get_report_data")
    def test_fetch_report_delegates_to_service(self, mock_get_report_data, owner: UsersDTO):
        """fetch_report() uses the bound service."""
        mock_get_report_data.return_value = pd.DataFrame([{"currency": "USD"}])
        handler = BalanceReportsHandler(service=BalanceReportsService())

        result = handler.fetch_report(
            report_id="account_balances",
            owner=owner,
            filters={"currency": "USD"},
        )

        mock_get_report_data.assert_called_once_with(
            report_id="account_balances",
            owner=owner,
            filters={"currency": "USD"},
        )
        assert not result.empty

    @patch.object(BalanceReportsService, "get_report_data")
    def test_dump_stores_fetched_data(self, mock_get_report_data, owner: UsersDTO):
        """dump() stores fetched rows in _loaded_data."""
        expected = pd.DataFrame([{"currency": "EUR"}])
        mock_get_report_data.return_value = expected
        handler = BalanceReportsHandler(service=BalanceReportsService())

        handler.dump(report_id="owner_monthly_balances", owner=owner, filters={"balance_year": 2025})
        assert handler._loaded_data is expected
