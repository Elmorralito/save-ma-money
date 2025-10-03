"""Unit tests for the asset service classes in papita_txnsmodel.services.assets.

This module contains tests that verify the configuration, inheritance, and
attributes of the asset service classes, ensuring they properly integrate
with the service architecture.
"""

import pytest
from unittest.mock import patch, MagicMock

from papita_txnsmodel.services.assets import (
    AssetAccountsService,
    ExtendedAssetAccountService,
    RealEstateAssetAccountsService,
    TradingAssetAccountsService,
)
from papita_txnsmodel.services.extends import LinkedEntitiesService, TypedLinkedEntitiesServiceMixin
from papita_txnsmodel.access.assets.dto import (
    AssetAccountsDTO,
    ExtendedAssetAccountDTO,
    RealEstateAssetAccountsDTO,
    TradingAssetAccountsDTO,
)
from papita_txnsmodel.access.assets.repository import AssetAccountsRepository, ExtendedAssetAccountRepository
from papita_txnsmodel.access.types.dto import TypesDTO
from papita_txnsmodel.services.types import TypesService
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.liabilities import ExtendedLiabilityAccountService


@pytest.fixture
def types_service():
    return TypesService()


# ================= AssetAccountsService Tests =================

def test_asset_accounts_service_inherits_typed_linked_entities_service_mixin():
    """Test that AssetAccountsService inherits from TypedLinkedEntitiesServiceMixin."""
    assert issubclass(AssetAccountsService, TypedLinkedEntitiesServiceMixin)


def test_asset_accounts_service_dto_type(types_service):
    """Test that AssetAccountsService has correct DTO type configuration."""
    assert AssetAccountsService(types_service=types_service).dto_type == AssetAccountsDTO


def test_asset_accounts_service_repository_type(types_service):
    """Test that AssetAccountsService has correct repository type configuration."""
    assert AssetAccountsService(types_service=types_service).repository_type == AssetAccountsRepository


def test_asset_accounts_service_types_dto_type(types_service):
    """Test that AssetAccountsService has correct types DTO type configuration."""
    assert AssetAccountsService(types_service=types_service).types_dto_type == TypesDTO


def test_asset_accounts_service_type_configuration(types_service):
    """Test that AssetAccountsService has correct type field configurations."""
    service = AssetAccountsService(types_service=types_service)
    assert service.type_id_column_name == "account_type_id"
    assert service.type_id_field_name == "account_type"


def test_asset_accounts_service_links_configuration(types_service):
    """Test that AssetAccountsService has correct links configuration."""
    service = AssetAccountsService(types_service=types_service)

    # Check account link
    assert "account" in service.__links__
    account_link = service.__links__["account"]
    assert account_link.expected_other_entity_service_type == AccountsService
    assert account_link.other_entity_link_column_name == "id"
    assert account_link.other_entity_link_field_name == "id"
    assert account_link.own_entity_link_column_name == "account_id"
    assert account_link.own_entity_link_field_name == "account"

    # Check bank_credit_liability_account link
    assert "bank_credit_liability_account" in service.__links__
    liability_link = service.__links__["bank_credit_liability_account"]
    assert liability_link.expected_other_entity_service_type == ExtendedLiabilityAccountService
    assert liability_link.other_entity_link_column_name == "id"
    assert liability_link.other_entity_link_field_name == "id"
    assert liability_link.own_entity_link_column_name == "bank_credit_liability_account_id"
    assert liability_link.own_entity_link_field_name == "bank_credit_liability_account"


def test_asset_accounts_service_instantiation(types_service):
    """Test that AssetAccountsService can be instantiated."""
    service = AssetAccountsService(types_service=types_service)
    assert isinstance(service, AssetAccountsService)
    assert isinstance(service, TypedLinkedEntitiesServiceMixin)


# ================= ExtendedAssetAccountService Tests =================

def test_extended_asset_account_service_inherits_linked_entities_service():
    """Test that ExtendedAssetAccountService inherits from LinkedEntitiesService."""
    assert issubclass(ExtendedAssetAccountService, LinkedEntitiesService)


def test_extended_asset_account_service_dto_type():
    """Test that ExtendedAssetAccountService has correct DTO type configuration."""
    assert ExtendedAssetAccountService().dto_type == ExtendedAssetAccountDTO


def test_extended_asset_account_service_repository_type():
    """Test that ExtendedAssetAccountService has correct repository type configuration."""
    assert ExtendedAssetAccountService().repository_type == ExtendedAssetAccountRepository


def test_extended_asset_account_service_links_configuration():
    """Test that ExtendedAssetAccountService has correct links configuration."""
    service = ExtendedAssetAccountService()

    assert "asset_account" in service.__links__
    link = service.__links__["asset_account"]
    assert link.expected_other_entity_service_type == AssetAccountsService
    assert link.other_entity_link_column_name == "id"
    assert link.other_entity_link_field_name == "id"
    assert link.own_entity_link_column_name == "asset_account_id"
    assert link.own_entity_link_field_name == "asset_account"


def test_extended_asset_account_service_instantiation():
    """Test that ExtendedAssetAccountService can be instantiated."""
    service = ExtendedAssetAccountService()
    assert isinstance(service, ExtendedAssetAccountService)
    assert isinstance(service, LinkedEntitiesService)


# ================= RealEstateAssetAccountsService Tests =================

def test_real_state_asset_accounts_service_inherits_linked_entities_service():
    """Test that RealEstateAssetAccountsService inherits from LinkedEntitiesService."""
    assert issubclass(RealEstateAssetAccountsService, LinkedEntitiesService)


def test_real_state_asset_accounts_service_dto_type():
    """Test that RealEstateAssetAccountsService has correct DTO type configuration."""
    assert RealEstateAssetAccountsService().dto_type == RealEstateAssetAccountsDTO


def test_real_state_asset_accounts_service_repository_type():
    """Test that RealEstateAssetAccountsService has correct repository type configuration."""
    assert RealEstateAssetAccountsService().repository_type == ExtendedAssetAccountRepository


def test_real_state_asset_accounts_service_links_configuration():
    """Test that RealEstateAssetAccountsService has correct links configuration."""
    service = RealEstateAssetAccountsService()

    assert "asset_account" in service.__links__
    link = service.__links__["asset_account"]
    assert link.expected_other_entity_service_type == AssetAccountsService
    assert link.other_entity_link_column_name == "id"
    assert link.other_entity_link_field_name == "id"
    assert link.own_entity_link_column_name == "asset_account_id"
    assert link.own_entity_link_field_name == "asset_account"


def test_real_state_asset_accounts_service_instantiation():
    """Test that RealEstateAssetAccountsService can be instantiated."""
    service = RealEstateAssetAccountsService()
    assert isinstance(service, RealEstateAssetAccountsService)
    assert isinstance(service, LinkedEntitiesService)


# ================= TradingAssetAccountsService Tests =================

def test_trading_asset_accounts_service_inherits_linked_entities_service():
    """Test that TradingAssetAccountsService inherits from LinkedEntitiesService."""
    assert issubclass(TradingAssetAccountsService, LinkedEntitiesService)


def test_trading_asset_accounts_service_dto_type():
    """Test that TradingAssetAccountsService has correct DTO type configuration."""
    assert TradingAssetAccountsService().dto_type == TradingAssetAccountsDTO


def test_trading_asset_accounts_service_repository_type():
    """Test that TradingAssetAccountsService has correct repository type configuration."""
    assert TradingAssetAccountsService().repository_type == ExtendedAssetAccountRepository


def test_trading_asset_accounts_service_links_configuration():
    """Test that TradingAssetAccountsService has correct links configuration."""
    service = TradingAssetAccountsService()

    assert "asset_account" in service.__links__
    link = service.__links__["asset_account"]
    assert link.expected_other_entity_service_type == AssetAccountsService
    assert link.other_entity_link_column_name == "id"
    assert link.other_entity_link_field_name == "id"
    assert link.own_entity_link_column_name == "asset_account_id"
    assert link.own_entity_link_field_name == "asset_account"


def test_trading_asset_accounts_service_instantiation():
    """Test that TradingAssetAccountsService can be instantiated."""
    service = TradingAssetAccountsService()
    assert isinstance(service, TradingAssetAccountsService)
    assert isinstance(service, LinkedEntitiesService)
