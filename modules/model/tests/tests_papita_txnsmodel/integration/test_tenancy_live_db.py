"""Live-DB tenancy integration tests (NFR-04, FR-02)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlmodel import Session, select

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.accounts.repository import AccountsRepository
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.categories.repository import CategoriesRepository
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.access.transactions.repository import TransactionsRepository
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.categories import Categories
from papita_txnsmodel.model.enums import AccountKind, CategoryKind, LedgerSide, TransactionKind
from papita_txnsmodel.services.categories import CategoriesService

from .conftest import requires_postgres

_VALID_PASSWORD = "Password1!"


def _user(user_id: uuid.UUID, label: str) -> UsersDTO:
    return UsersDTO(
        id=user_id,
        username=f"ppt041_{label}",
        email=f"ppt041_{label}@example.local",
        password=_VALID_PASSWORD,
    )


@requires_postgres
class TestLiveDbTenancyIsolation:
    """User A cannot read or write User B owned rows on PostgreSQL."""

    def test_cross_tenant_account_upsert_rejected(
        self, postgres_connector, ensure_integration_users, integration_owner_ids
    ):
        """OwnedTableRepository rejects mismatched owner_id on upsert."""
        user_a = _user(integration_owner_ids["user_a"], "user_a")
        user_b = _user(integration_owner_ids["user_b"], "user_b")
        repository = AccountsRepository()
        dto = AccountsDTO(
            id=uuid.uuid4(),
            name="Tenant B Account",
            description="isolated",
            owner_id=user_b.id,
            account_kind=AccountKind.OTHER_ASSET,
            ledger_side=LedgerSide.ASSET,
        )
        with pytest.raises(ValueError, match="owner_id does not match"):
            repository.upsert_record(dto, owner=user_a)

    def test_user_a_cannot_see_user_b_account(
        self, postgres_connector, ensure_integration_users, integration_owner_ids, db_session
    ):
        """Owner filter prevents cross-tenant reads."""
        user_a = _user(integration_owner_ids["user_a"], "user_a")
        user_b = _user(integration_owner_ids["user_b"], "user_b")
        account_id = uuid.uuid4()
        repository = AccountsRepository()
        repository.upsert_record(
            AccountsDTO(
                id=account_id,
                name="B only",
                description="private",
                owner_id=user_b.id,
                account_kind=AccountKind.CASH,
                ledger_side=LedgerSide.ASSET,
            ),
            owner=user_b,
        )
        record = repository.get_record_by_id(account_id, owner=user_a, dto_type=AccountsDTO)
        assert record is None

        with Session(postgres_connector.engine) as cleanup_session:
            cleanup_session.execute(
                text("DELETE FROM papita_transactions.accounts WHERE id = :id"),
                {"id": str(account_id)},
            )
            cleanup_session.commit()

    def test_cross_tenant_transaction_upsert_rejected(
        self, postgres_connector, ensure_integration_users, integration_owner_ids
    ):
        """Transactions repository enforces tenant ownership on writes."""
        user_a = _user(integration_owner_ids["user_a"], "user_a")
        user_b = _user(integration_owner_ids["user_b"], "user_b")
        repository = TransactionsRepository()
        dto = TransactionsDTO(
            id=uuid.uuid4(),
            owner_id=user_b.id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=12.5,
        )
        with pytest.raises(ValueError, match="owner_id does not match"):
            repository.upsert_record(dto, owner=user_a)

    def test_global_category_readable_but_not_writable(
        self, postgres_connector, ensure_integration_users, integration_owner_ids, db_session
    ):
        """Global seeds (owner_id IS NULL) are visible but immutable for tenants."""
        user_a = _user(integration_owner_ids["user_a"], "user_a")
        global_id = uuid.uuid4()
        db_session.execute(
            text(
                """
                INSERT INTO papita_transactions.categories
                    (id, owner_id, parent_id, name, category_kind, description, tags, active, created_at, updated_at)
                VALUES
                    (:id, NULL, NULL, :name, 'EXPENSE', 'seed', '{}', true, NOW(), NOW())
                """
            ),
            {"id": str(global_id), "name": f"Global Utilities {global_id.hex[:8]}"},
        )
        db_session.commit()

        with Session(postgres_connector.engine) as read_session:
            rows = read_session.exec(select(Categories).where(Categories.id == global_id)).all()
        assert len(rows) == 1
        assert rows[0].owner_id is None

        categories_repo = CategoriesRepository()
        tenant_rows = categories_repo.get_records(
            Categories.id == global_id,
            owner=user_a,
            dto_type=CategoriesDTO,
        )
        assert not tenant_rows.empty

        service = CategoriesService()
        with pytest.raises(ValueError, match="global categories"):
            service.create(
                obj=CategoriesDTO(
                    id=global_id,
                    name="Tampered",
                    description="seed",
                    category_kind=CategoryKind.EXPENSE,
                    owner_id=user_a.id,
                ),
                owner=user_a,
            )

        db_session.execute(
            text("DELETE FROM papita_transactions.categories WHERE id = :id"),
            {"id": str(global_id)},
        )
        db_session.commit()
