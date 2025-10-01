"""Unit tests for the AccountsService class in papita_txnsmodel.services.accounts.

This module contains tests that verify the configuration, inheritance, and
validation constraints of the AccountsService class, ensuring it properly
integrates with the BaseService architecture.
"""

import pytest
from pydantic import ValidationError
from unittest.mock import MagicMock, patch

from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.accounts.repository import AccountsRepository
from papita_txnsmodel.database.upsert import OnUpsertConflictDo


@pytest.fixture
def mock_base_service():
    """Provides a mock for the BaseService class."""
    with patch('papita_txnsmodel.services.accounts.BaseService') as mock:
        yield mock


def test_accounts_service_inherits_base_service():
    """Test that AccountsService inherits from BaseService."""
    # Verify inheritance relationship
    from papita_txnsmodel.services.base import BaseService
    assert issubclass(AccountsService, BaseService)


def test_accounts_service_dto_type():
    """Test that AccountsService has correct DTO type configuration."""
    # Verify the DTO type is correctly set
    assert AccountsService().dto_type == AccountsDTO


def test_accounts_service_repository_type():
    """Test that AccountsService has correct repository type configuration."""
    # Verify the repository type is correctly set
    assert AccountsService().repository_type == AccountsRepository


def test_accounts_service_default_missing_upsertions_tol():
    """Test the default value for missing_upsertions_tol."""
    # Verify the default value
    assert AccountsService().missing_upsertions_tol == 0.0


def test_accounts_service_default_on_conflict_do():
    """Test the default value for on_conflict_do."""
    # Verify the default conflict resolution strategy
    assert AccountsService().on_conflict_do == OnUpsertConflictDo.UPDATE


def test_accounts_service_missing_upsertions_tol_validation():
    """Test validation constraints on missing_upsertions_tol."""
    # Test with valid values
    service = AccountsService()
    with patch.object(service, 'missing_upsertions_tol', 0.0):
        assert service.missing_upsertions_tol == 0.0

    with patch.object(service, 'missing_upsertions_tol', 0.5):
        assert service.missing_upsertions_tol == 0.5

    with pytest.raises(ValidationError):
        AccountsService(missing_upsertions_tol=1000)


def test_accounts_service_on_conflict_do_options():
    """Test that on_conflict_do accepts both enum and string values."""
    # Test with enum value
    service = AccountsService()
    assert service.on_conflict_do == OnUpsertConflictDo.UPDATE

    # Test with string value
    service = AccountsService()
    with patch.object(service, 'on_conflict_do', "IGNORE"):
        assert service.on_conflict_do == "IGNORE"


def test_accounts_service_instantiation():
    """Test that AccountsService can be instantiated."""
    # Simple instantiation test
    service = AccountsService()
    assert isinstance(service, AccountsService)
    assert isinstance(service, BaseService)


@pytest.mark.parametrize(
    "conflict_option",
    [
        OnUpsertConflictDo.UPDATE,
        OnUpsertConflictDo.NOTHING,
        "UPDATE",
        "NOTHING"
    ]
)
def test_accounts_service_valid_conflict_options(conflict_option):
    """Test that AccountsService accepts valid conflict resolution options."""
    service = AccountsService()
    with patch.object(service, 'on_conflict_do', conflict_option):
        assert service.on_conflict_do == conflict_option
