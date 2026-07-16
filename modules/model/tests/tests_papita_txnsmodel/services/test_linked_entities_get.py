"""Unit tests for LinkedEntitiesService.get null-FK and link-resolution branches (PPT-040)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import AccountKind, LedgerSide, TransactionKind, TransactionStatus
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.services.extends import LinkedEntity
from papita_txnsmodel.services.transactions import TransactionsService

_VALID_PASSWORD = "Password1!"


@pytest.fixture
def owner() -> UsersDTO:
    """Tenant owner for linked-entity gets."""
    return UsersDTO(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        username="linked_get_user",
        email="linked_get@example.local",
        password=_VALID_PASSWORD,
        auth_provider="local",
    )


def _fresh_transaction_links() -> dict[str, LinkedEntity]:
    """Clone link defs with unloaded services.

    ``load_link_services`` mutates class-level ``LinkedEntity`` instances in place. Other
    suite tests can leave those services loaded, which hides the
    ``not isinstance(...): continue`` branch from Codecov when this file runs later.
    """
    return {
        name: LinkedEntity(
            expected_other_entity_service_type=link.expected_other_entity_service_type,
            other_entity_link_column_name=link.other_entity_link_column_name,
            other_entity_link_field_name=link.other_entity_link_field_name,
            own_entity_link_column_name=link.own_entity_link_column_name,
            own_entity_link_field_name=link.own_entity_link_field_name,
            other_entity_service=None,
        )
        for name, link in TransactionsService.__links__.items()
    }


def _transactions_service() -> TransactionsService:
    with patch("papita_txnsmodel.services.transactions.TransactionsRepository"):
        service = TransactionsService()
        service._repository = MagicMock()
        service.__links__ = _fresh_transaction_links()
        return service


def _accounts_service() -> AccountsService:
    with patch("papita_txnsmodel.services.accounts.AccountsRepository"):
        service = AccountsService()
        service._repository = MagicMock()
        service.balances_service = MagicMock()
        return service


def _expense(*, owner_id: uuid.UUID, from_account_id: uuid.UUID | None) -> TransactionsDTO:
    now = datetime.now(timezone.utc)
    return TransactionsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        transaction_kind=TransactionKind.EXPENSE,
        amount=42.5,
        currency="USD",
        transaction_ts=now,
        from_account_id=from_account_id,
        to_account_id=None,
        category_id=None,
        template_id=None,
        status=TransactionStatus.COMPLETED,
        description="linked-get fixture",
        created_at=now,
        updated_at=now,
    )


class TestLinkedEntitiesServiceGet:
    """Cover LinkedEntitiesService.get branches flagged by Codecov patch."""

    def test_get_skips_null_fks_and_unloaded_links(self, owner: UsersDTO) -> None:
        """Null FKs and unloaded link services are skipped without repository errors."""
        service = _transactions_service()
        from_id = uuid.uuid4()
        expense = _expense(owner_id=owner.id, from_account_id=from_id)
        account = AccountsDTO(
            id=from_id,
            name="Wallet",
            owner_id=owner.id,
            account_kind=AccountKind.OTHER_ASSET,
            ledger_side=LedgerSide.ASSET,
            currency="USD",
        )
        accounts_svc = _accounts_service()
        accounts_svc.get = MagicMock(return_value=account)
        # Only load from/to account links; category/template stay unloaded (None service).
        service.load_link_services({"from_account_id": accounts_svc, "to_account_id": accounts_svc})

        with patch.object(BaseService, "get", return_value=expense):
            result = service.get(obj=expense.id, owner=owner, include_linked_dtos=True)

        assert result is not None
        assert result.from_account_id == account
        accounts_svc.get.assert_called_once()
        assert accounts_svc.get.call_args.kwargs["obj"] == from_id

    def test_get_falls_back_to_fk_when_linked_service_returns_none(self, owner: UsersDTO) -> None:
        """When linked get misses, keep the raw FK UUID on the DTO field."""
        service = _transactions_service()
        from_id = uuid.uuid4()
        expense = _expense(owner_id=owner.id, from_account_id=from_id)
        accounts_svc = _accounts_service()
        accounts_svc.get = MagicMock(return_value=None)
        service.load_link_services({"from_account_id": accounts_svc})

        with patch.object(BaseService, "get", return_value=expense):
            result = service.get(obj=expense.id, owner=owner, include_linked_dtos=True)

        assert result is not None
        assert result.from_account_id == from_id
        accounts_svc.get.assert_called_once_with(obj=from_id, owner=owner, include_linked_dtos=True)

    def test_get_uses_resolved_dto_when_linked_service_hits(self, owner: UsersDTO) -> None:
        """When linked get returns a DTO, embed it on the transaction field."""
        service = _transactions_service()
        from_id = uuid.uuid4()
        expense = _expense(owner_id=owner.id, from_account_id=from_id)
        account = AccountsDTO(
            id=from_id,
            name="Hit Wallet",
            owner_id=owner.id,
            account_kind=AccountKind.OTHER_ASSET,
            ledger_side=LedgerSide.ASSET,
            currency="USD",
        )
        accounts_svc = _accounts_service()
        accounts_svc.get = MagicMock(return_value=account)
        service.load_link_services({"from_account_id": accounts_svc})

        with patch.object(BaseService, "get", return_value=expense):
            result = service.get(obj=expense.id, owner=owner, include_linked_dtos=True)

        assert result is not None
        assert result.from_account_id is account
        assert result.from_account_id.name == "Hit Wallet"

    def test_get_skips_links_when_include_linked_dtos_false(self, owner: UsersDTO) -> None:
        """include_linked_dtos=False returns the bare DTO without resolving FKs."""
        service = _transactions_service()
        from_id = uuid.uuid4()
        expense = _expense(owner_id=owner.id, from_account_id=from_id)
        accounts_svc = _accounts_service()
        accounts_svc.get = MagicMock()
        service.load_link_services({"from_account_id": accounts_svc})

        with patch.object(BaseService, "get", return_value=expense):
            result = service.get(obj=expense.id, owner=owner, include_linked_dtos=False)

        assert result is expense
        accounts_svc.get.assert_not_called()

    def test_get_returns_none_when_missing(self, owner: UsersDTO) -> None:
        """Propagate None when the base record lookup fails."""
        service = _transactions_service()
        with patch.object(BaseService, "get", return_value=None):
            assert service.get(obj=uuid.uuid4(), owner=owner) is None

    def test_get_with_all_null_fks_skips_model_rebuild(self, owner: UsersDTO) -> None:
        """When every linked FK is null, return the base DTO without rebuild."""
        service = _transactions_service()
        expense = _expense(owner_id=owner.id, from_account_id=None)
        accounts_svc = _accounts_service()
        accounts_svc.get = MagicMock()
        service.load_link_services({"from_account_id": accounts_svc, "to_account_id": accounts_svc})

        with patch.object(BaseService, "get", return_value=expense):
            result = service.get(obj=expense.id, owner=owner, include_linked_dtos=True)

        assert result is expense
        accounts_svc.get.assert_not_called()
