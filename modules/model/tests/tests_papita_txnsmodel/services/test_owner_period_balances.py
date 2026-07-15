"""Tests for OwnerPeriodBalancesService."""

import uuid
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.owner_period_balances import OwnerPeriodBalancesService

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


class TestOwnerPeriodBalancesService:
    """Read service for monthly, quarterly, and biannual owner balances."""

    def test_get_monthly_balances_requires_owner(self):
        """Guard clause when owner is missing."""
        service = OwnerPeriodBalancesService()
        with pytest.raises(ValueError, match="owner=UsersDTO is required"):
            service.get_monthly_balances(owner=None)  # type: ignore[arg-type]

    def test_get_quarterly_balances_requires_owner(self):
        """Guard clause when owner is missing."""
        service = OwnerPeriodBalancesService()
        with pytest.raises(ValueError, match="owner=UsersDTO is required"):
            service.get_quarterly_balances(owner=None)  # type: ignore[arg-type]

    def test_get_biannual_balances_requires_owner(self):
        """Guard clause when owner is missing."""
        service = OwnerPeriodBalancesService()
        with pytest.raises(ValueError, match="owner=UsersDTO is required"):
            service.get_biannual_balances(owner=None)  # type: ignore[arg-type]

    def test_refresh_delegates_to_repository(self):
        """Refresh delegates to repository for all period views."""
        service = OwnerPeriodBalancesService()
        repo = MagicMock()
        service._repository = repo
        service.refresh(concurrently=True)
        repo.refresh_materialized_views.assert_called_once_with(concurrently=True)

    @patch("papita_txnsmodel.access.balance_reports.repository.BalanceReportsRepository")
    def test_get_monthly_balances_delegates_filters(self, mock_repo_cls, owner: UsersDTO):
        """Unified repository receives owner and optional monthly filters."""
        service = OwnerPeriodBalancesService()
        repo = MagicMock()
        repo.query.return_value = pd.DataFrame([])
        mock_repo_cls.return_value = repo

        service.get_monthly_balances(owner=owner, balance_year=2025, balance_month=6, currency="USD")
        repo.query.assert_called_once_with(
            report_id="owner_monthly_balances",
            owner=owner,
            filters={"balance_year": 2025, "balance_month": 6, "currency": "USD"},
        )
