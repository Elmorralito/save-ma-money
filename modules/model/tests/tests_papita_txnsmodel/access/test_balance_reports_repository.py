"""Tests for BalanceReportsRepository registry enforcement."""

import uuid

import pytest

from papita_txnsmodel.access.balance_reports.exceptions import UnregisteredBalanceReportError
from papita_txnsmodel.access.balance_reports.repository import BalanceReportsRepository
from papita_txnsmodel.access.users.dto import UsersDTO

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


class TestBalanceReportsRepository:
    """Unified repository must honor the YAML registry."""

    def test_query_rejects_unregistered_report(self, owner: UsersDTO):
        """Repository refuses to execute views not listed in balance_report_filters.yaml."""
        repository = BalanceReportsRepository()
        with pytest.raises(UnregisteredBalanceReportError, match="cannot be executed"):
            repository.query(report_id="ghost_report", owner=owner)
