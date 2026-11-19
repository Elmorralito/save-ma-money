"""Tests for OwnerYearlyBalancesService."""

import uuid
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.owner_yearly_balances import OwnerYearlyBalancesService

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


class TestOwnerYearlyBalancesService:
    """Read service for combined yearly owner balances."""

    def test_get_yearly_balances_requires_owner(self):
        """Guard clause when owner is missing."""
        service = OwnerYearlyBalancesService()
        with pytest.raises(ValueError, match="owner=UsersDTO is required"):
            service.get_yearly_balances(owner=None)  # type: ignore[arg-type]

    def test_refresh_delegates_to_repository(self):
        """Refresh delegates to repository."""
        service = OwnerYearlyBalancesService()
        repo = MagicMock()
        service._repository = repo
        service.refresh(concurrently=True)
        repo.refresh_materialized_view.assert_called_once_with(concurrently=True)

    def test_get_yearly_balances_delegates_filters(self, owner: UsersDTO):
        """Repository receives owner and optional filters."""
        service = OwnerYearlyBalancesService()
        repo = MagicMock()
        repo.get_yearly_balances.return_value = pd.DataFrame([])
        service._repository = repo

        service.get_yearly_balances(owner=owner, balance_year=2025, currency="USD")

        repo.get_yearly_balances.assert_called_once_with(
            owner=owner,
            balance_year=2025,
            currency="USD",
        )
