"""B0 live-DB tests for PPT-072 upcoming dues / mark-paid services."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import text

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.transactions.dto import TransactionTemplatesDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import AccountKind, CategoryKind, LedgerSide, TransactionKind
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.categories import CategoriesService
from papita_txnsmodel.services.transactions import TransactionTemplatesService

from .conftest import requires_postgres

_VALID_PASSWORD = "Password1!"


def _user(user_id: uuid.UUID, label: str) -> UsersDTO:
    return UsersDTO(
        id=user_id,
        username=f"ppt072_{label}",
        email=f"ppt072_{label}@example.local",
        password=_VALID_PASSWORD,
        auth_provider="local",
    )


def _cleanup(engine, *, account_id: uuid.UUID, category_id: uuid.UUID, template_id: uuid.UUID) -> None:
    """Best-effort cleanup for PPT-072 integration rows."""
    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM papita_transactions.transactions WHERE template_id = :tid"),
            {"tid": str(template_id)},
        )
        conn.execute(
            text("DELETE FROM papita_transactions.transaction_templates WHERE id = :id"),
            {"id": str(template_id)},
        )
        conn.execute(
            text("DELETE FROM papita_transactions.accounts WHERE id = :id"),
            {"id": str(account_id)},
        )
        conn.execute(
            text("DELETE FROM papita_transactions.categories WHERE id = :id"),
            {"id": str(category_id)},
        )
        conn.commit()


@requires_postgres
class TestLiveDbPpt072DuesServices:
    """Upcoming dues + mark-paid / clear-paid against Docker Postgres (B0)."""

    def test_mark_paid_list_and_clear_paid_round_trip(
        self, postgres_connector, ensure_integration_users, integration_owner_ids
    ):
        """Owner can mark a due paid, see it in upcoming list, then clear paid."""
        owner = _user(integration_owner_ids["user_a"], "user_a")
        other = _user(integration_owner_ids["user_b"], "user_b")
        as_of = date(2026, 8, 10)

        accounts = AccountsService()
        categories = CategoriesService()
        templates = TransactionTemplatesService()

        account, _ = accounts.create_account(
            obj=AccountsDTO(
                name=f"PPT072 cash {uuid.uuid4().hex[:8]}",
                description="dues test",
                owner_id=owner.id,
                # OTHER_ASSET has no required *_account_details row.
                account_kind=AccountKind.OTHER_ASSET,
                ledger_side=LedgerSide.ASSET,
            ),
            owner=owner,
        )
        category = categories.create(
            obj=CategoriesDTO(
                name=f"PPT072 bills {uuid.uuid4().hex[:8]}",
                description="dues test",
                category_kind=CategoryKind.EXPENSE,
                owner_id=owner.id,
            ),
            owner=owner,
        )
        template = templates.create(
            obj=TransactionTemplatesDTO(
                owner_id=owner.id,
                category_id=category.id,
                name=f"PPT072 rent {uuid.uuid4().hex[:8]}",
                planned_amount=99.5,
                planned_day=12,
                use_month_end=False,
                remind_days_before=0,
                from_account_id=account.id,
            ),
            owner=owner,
            include_category=False,
        )
        assert template.id is not None
        assert account.id is not None
        assert category.id is not None

        try:
            upcoming = templates.list_upcoming_dues(owner=owner, as_of=as_of, window_days=7)
            matched = [row for row in upcoming if row.template.id == template.id]
            assert len(matched) == 1
            assert matched[0].is_paid is False
            assert matched[0].due_date == date(2026, 8, 12)

            # Cross-tenant list must not surface the row.
            other_upcoming = templates.list_upcoming_dues(owner=other, as_of=as_of, window_days=7)
            assert all(row.template.id != template.id for row in other_upcoming)

            posted = templates.mark_paid(template_id=template.id, owner=owner, as_of=as_of)
            assert posted.template_id == template.id or getattr(posted.template_id, "id", None) == template.id
            assert posted.transaction_kind == TransactionKind.EXPENSE
            assert posted.amount == pytest.approx(99.5)

            paid_list = templates.list_upcoming_dues(owner=owner, as_of=as_of, window_days=7)
            paid_row = next(row for row in paid_list if row.template.id == template.id)
            assert paid_row.is_paid is True
            assert paid_row.paid_transaction_id == posted.id

            with pytest.raises(ValueError, match="already marked paid"):
                templates.mark_paid(template_id=template.id, owner=owner, as_of=as_of)

            with pytest.raises(ValueError, match="not found|Pay account"):
                templates.mark_paid(template_id=template.id, owner=other, as_of=as_of)

            cleared = templates.clear_paid(template_id=template.id, owner=owner, as_of=as_of)
            assert cleared.id == posted.id

            after_clear = templates.list_upcoming_dues(owner=owner, as_of=as_of, window_days=7)
            unpaid = next(row for row in after_clear if row.template.id == template.id)
            assert unpaid.is_paid is False
        finally:
            _cleanup(
                postgres_connector.engine,
                account_id=account.id,
                category_id=category.id,
                template_id=template.id,
            )
