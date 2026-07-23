"""Unit tests for PR-F efficiency slices (E7/E8/E9)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import AccountKind, CategoryKind, LedgerSide
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.services.extends import LinkedEntitiesService, LinkedEntity
from papita_txnsmodel.services.transactions import TransactionsService

_VALID_PASSWORD = "Password1!"


@pytest.fixture
def owner() -> UsersDTO:
    """Tenant user for service calls."""
    return UsersDTO(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        username="user_a_test",
        email="user_a@example.local",
        password=_VALID_PASSWORD,
        auth_provider="local",
    )


class TestPageWithTotal:
    """E9: list helpers use repository page+total."""

    def test_list_accounts_uses_page_with_total(self, owner: UsersDTO) -> None:
        with patch("papita_txnsmodel.services.accounts.AccountsRepository"):
            service = AccountsService()
            service._repository = MagicMock()
            service.balances_service = MagicMock()
            service._repository.get_page_with_total.return_value = (pd.DataFrame([]), 7)

        page, total = service.list_accounts(owner=owner, skip=2, limit=5)
        assert total == 7
        assert page.empty
        assert service._repository.get_page_with_total.call_args.kwargs["skip"] == 2
        assert service._repository.get_page_with_total.call_args.kwargs["limit"] == 5

    def test_get_page_with_total_empty_page_falls_back_to_count(self) -> None:
        from sqlmodel import Session

        from papita_txnsmodel.access.base.repository import BaseRepository

        repo = BaseRepository()
        session = MagicMock()
        page_result = MagicMock()
        page_result.all.return_value = []
        count_result = MagicMock()
        count_result.one.return_value = 12
        session.exec.side_effect = [page_result, count_result]

        unwrapped = BaseRepository.get_page_with_total.__wrapped__
        real_isinstance = isinstance

        def _isinstance(obj: object, typ: object) -> bool:
            if typ is Session:
                return True
            return real_isinstance(obj, typ)  # type: ignore[arg-type]

        with patch("papita_txnsmodel.access.base.repository.isinstance", side_effect=_isinstance):
            page, total = unwrapped(
                repo,
                dto_type=AccountsDTO,
                _db_session=session,
                skip=100,
                limit=10,
            )
        assert page.empty
        assert total == 12


class TestSpendingSqlAggregate:
    """E8: spending uses SQL aggregate helper."""

    def test_aggregate_spending_delegates_to_repository(self, owner: UsersDTO) -> None:
        with patch("papita_txnsmodel.services.transactions.TransactionsRepository"):
            service = TransactionsService()
            service._repository = MagicMock()
            expected = {
                "group_by": "category",
                "expenses": [{"category_id": uuid.uuid4(), "total": 10.0}],
                "expense_total": 10.0,
                "income_total": 5.0,
            }
            service._repository.aggregate_spending.return_value = expected

        result = service.aggregate_spending(owner=owner, group_by="category")
        assert result == expected
        service._repository.aggregate_spending.assert_called_once()


class TestLinkedDtoCache:
    """E7: create reuses prefetched link DTOs."""

    def test_create_uses_linked_dto_cache_without_get_or_create(self, owner: UsersDTO) -> None:
        account_id = uuid.uuid4()
        account = AccountsDTO(
            id=account_id,
            owner_id=owner.id,
            name="Checking",
            account_kind=AccountKind.CHECKING,
            ledger_side=LedgerSide.ASSET,
            currency="USD",
            initial_value=0.0,
        )
        with patch("papita_txnsmodel.services.accounts.AccountsRepository"):
            linked_service = AccountsService()
        linked_service.get_or_create = MagicMock()
        link = LinkedEntity(
            expected_other_entity_service_type=AccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="from_account_id",
            own_entity_link_field_name="from_account_id",
        )
        object.__setattr__(link, "other_entity_service", linked_service)
        service = object.__new__(LinkedEntitiesService)
        service.__links__ = {"from_account_id": link}
        created = MagicMock(name="created_dto")

        with patch.object(BaseService, "create", return_value=created) as mock_base_create:
            result = LinkedEntitiesService.create(
                service,
                obj={"from_account_id": account_id, "amount": 1.0},
                owner=owner,
                linked_dto_cache={("from_account_id", account_id): account},
            )

        linked_service.get_or_create.assert_not_called()
        mock_base_create.assert_called_once()
        assert result is created
        assert result.from_account_id is account

    def test_prefetch_link_dtos_loads_accounts_and_categories(self, owner: UsersDTO) -> None:
        account_id = uuid.uuid4()
        category_id = uuid.uuid4()
        account = AccountsDTO(
            id=account_id,
            owner_id=owner.id,
            name="Checking",
            account_kind=AccountKind.CHECKING,
            ledger_side=LedgerSide.ASSET,
            currency="USD",
            initial_value=0.0,
        )
        category = CategoriesDTO(
            id=category_id,
            owner_id=owner.id,
            name="Food",
            description="",
            category_kind=CategoryKind.EXPENSE,
        )
        with (
            patch("papita_txnsmodel.services.accounts.AccountsRepository"),
            patch("papita_txnsmodel.services.categories.CategoriesRepository"),
            patch("papita_txnsmodel.services.transactions.TransactionsRepository"),
        ):
            accounts_service = AccountsService()
            from papita_txnsmodel.services.categories import CategoriesService

            categories_service = CategoriesService()
            service = TransactionsService()
        accounts_service.get = MagicMock(return_value=account)
        categories_service.get = MagicMock(return_value=category)
        service = service.load_link_services(
            {
                "from_account_id": accounts_service,
                "to_account_id": accounts_service,
                "category_id": categories_service,
            }
        )

        cache = service.prefetch_link_dtos(
            owner=owner,
            account_ids=[account_id],
            category_ids=[category_id],
        )
        assert cache[("from_account_id", account_id)] is account
        assert cache[("to_account_id", account_id)] is account
        assert cache[("category_id", category_id)] is category
        accounts_service.get.assert_called_once_with(obj=account_id, owner=owner)
        categories_service.get.assert_called_once_with(obj=category_id, owner=owner)
