"""Unit tests for PPT-072 upcoming dues and mark-paid services."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO, TransactionTemplatesDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import AccountKind, CategoryKind, LedgerSide, TransactionKind, TransactionStatus
from papita_txnsmodel.services.dues import (
    candidate_due_dates,
    due_in_month,
    in_upcoming_window,
    period_key,
    remind_start_for,
    resolve_due_date,
    select_upcoming_due,
)
from papita_txnsmodel.services.transactions import TransactionTemplatesService

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


def _template(**overrides) -> TransactionTemplatesDTO:
    """Minimal recurring/one-off template for helper and service tests."""
    payload = {
        "id": uuid.uuid4(),
        "owner_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "category_id": uuid.uuid4(),
        "name": "Rent",
        "planned_amount": 1200.0,
        "planned_day": 15,
        "use_month_end": False,
        "due_date": None,
        "remind_days_before": None,
        "from_account_id": uuid.uuid4(),
    }
    payload.update(overrides)
    return TransactionTemplatesDTO(**payload)


class TestDueHelpers:
    """Pure due-resolution and window membership helpers."""

    def test_one_off_due_date_wins(self):
        """Explicit due_date takes precedence over planned_day."""
        due = date(2026, 9, 20)
        template = _template(due_date=due, planned_day=1)
        assert resolve_due_date(template, ref=date(2026, 3, 1)) == due

    def test_month_end_and_day_clamp(self):
        """use_month_end and planned_day=31 clamp to February length."""
        month_end = _template(use_month_end=True, planned_day=1)
        assert due_in_month(month_end, year=2026, month=2) == date(2026, 2, 28)
        day31 = _template(use_month_end=False, planned_day=31)
        assert due_in_month(day31, year=2026, month=2) == date(2026, 2, 28)

    def test_remind_null_treated_as_zero(self):
        """Null remind lead starts on the due date."""
        due = date(2026, 8, 10)
        assert remind_start_for(due, None) == due
        assert remind_start_for(due, 3) == date(2026, 8, 7)

    def test_upcoming_window_overlap_with_remind(self):
        """Due outside the raw window still matches when remind starts inside it."""
        due = date(2026, 8, 25)
        assert in_upcoming_window(due, 7, as_of=date(2026, 8, 10), window_days=14) is True
        assert in_upcoming_window(due, 0, as_of=date(2026, 8, 10), window_days=14) is False

    def test_select_upcoming_due_picks_earliest_in_window(self):
        """Recurring templates pick the earliest candidate in the window."""
        template = _template(planned_day=1, remind_days_before=0)
        assert select_upcoming_due(template, as_of=date(2026, 8, 1), window_days=14) == date(2026, 8, 1)
        assert select_upcoming_due(template, as_of=date(2026, 8, 5), window_days=14) is None

    def test_candidate_dues_for_recurring_span_adjacent_months(self):
        """Recurring candidates cover previous/current/next month."""
        template = _template(planned_day=10)
        candidates = candidate_due_dates(template, as_of=date(2026, 8, 15))
        assert candidates == [date(2026, 7, 10), date(2026, 8, 10), date(2026, 9, 10)]

    def test_period_key(self):
        """Paid matching keys on calendar year/month of the resolved due."""
        assert period_key(date(2026, 2, 28)) == (2026, 2)


def _templates_service() -> TransactionTemplatesService:
    """Build a templates service with mocked repositories and collaborators."""
    with (
        patch("papita_txnsmodel.services.transactions.TransactionTemplatesRepository"),
        patch("papita_txnsmodel.services.categories.CategoriesRepository"),
        patch("papita_txnsmodel.services.accounts.AccountsRepository"),
        patch("papita_txnsmodel.services.transactions.TransactionsRepository"),
    ):
        service = TransactionTemplatesService()
        service._repository = MagicMock()
        service.categories_service = MagicMock()
        service.accounts_service = MagicMock()
        service.transactions_service = MagicMock()
        return service


class TestListUpcomingDues:
    """TransactionTemplatesService.list_upcoming_dues behavior."""

    def test_filters_to_window_and_sorts(self, owner: UsersDTO):
        """Only in-window templates are returned, sorted by due date."""
        service = _templates_service()
        in_window = _template(
            id=uuid.uuid4(),
            name="Electric",
            planned_day=12,
            remind_days_before=0,
        )
        out_of_window = _template(
            id=uuid.uuid4(),
            name="Later",
            planned_day=28,
            remind_days_before=0,
        )
        frame = pd.DataFrame(
            [
                in_window.model_dump(mode="python"),
                out_of_window.model_dump(mode="python"),
            ]
        )
        with (
            patch.object(TransactionTemplatesService, "get_records", return_value=frame),
            patch.object(TransactionTemplatesService, "_paid_postings_by_template", return_value={}),
        ):
            results = service.list_upcoming_dues(owner=owner, as_of=date(2026, 8, 10), window_days=7)

        assert len(results) == 1
        assert results[0].template.id == in_window.id
        assert results[0].due_date == date(2026, 8, 12)
        assert results[0].is_paid is False

    def test_include_paid_false_omits_paid(self, owner: UsersDTO):
        """Paid dues are omitted when include_paid is False."""
        service = _templates_service()
        template = _template(planned_day=12, remind_days_before=0)
        paid = TransactionsDTO(
            id=uuid.uuid4(),
            owner_id=owner.id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=10.0,
            template_id=template.id,
            transaction_ts=datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
        )
        frame = pd.DataFrame([template.model_dump(mode="python")])
        with (
            patch.object(TransactionTemplatesService, "get_records", return_value=frame),
            patch.object(
                TransactionTemplatesService,
                "_paid_postings_by_template",
                return_value={template.id: paid},
            ),
        ):
            results = service.list_upcoming_dues(
                owner=owner,
                as_of=date(2026, 8, 10),
                window_days=7,
                include_paid=False,
            )
        assert results == []

    def test_batches_paid_lookup_once_per_month(self, owner: UsersDTO):
        """Same-month dues share one get_transactions_frame call."""
        service = _templates_service()
        t1 = _template(id=uuid.uuid4(), name="A", planned_day=12, remind_days_before=0)
        t2 = _template(id=uuid.uuid4(), name="B", planned_day=14, remind_days_before=0)
        frame = pd.DataFrame([t1.model_dump(mode="python"), t2.model_dump(mode="python")])
        service.transactions_service.get_transactions_frame.return_value = pd.DataFrame()
        with patch.object(TransactionTemplatesService, "get_records", return_value=frame):
            results = service.list_upcoming_dues(owner=owner, as_of=date(2026, 8, 10), window_days=7)

        assert len(results) == 2
        assert service.transactions_service.get_transactions_frame.call_count == 1

    def test_one_off_due_date_in_list(self, owner: UsersDTO):
        """One-off due_date templates appear when the due is in window."""
        service = _templates_service()
        template = _template(
            due_date=date(2026, 8, 15),
            planned_day=1,
            remind_days_before=0,
            name="One-off",
        )
        frame = pd.DataFrame([template.model_dump(mode="python")])
        with (
            patch.object(TransactionTemplatesService, "get_records", return_value=frame),
            patch.object(TransactionTemplatesService, "_paid_postings_by_template", return_value={}),
        ):
            results = service.list_upcoming_dues(owner=owner, as_of=date(2026, 8, 10), window_days=7)
        assert len(results) == 1
        assert results[0].due_date == date(2026, 8, 15)

    def test_paid_postings_match_template_in_month(self, owner: UsersDTO):
        """Batch paid helper keeps the latest posting per template_id in-period."""
        service = _templates_service()
        template_id = uuid.uuid4()
        older = TransactionsDTO(
            id=uuid.uuid4(),
            owner_id=owner.id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=10.0,
            template_id=template_id,
            transaction_ts=datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc),
        )
        newer = TransactionsDTO(
            id=uuid.uuid4(),
            owner_id=owner.id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=11.0,
            template_id=template_id,
            transaction_ts=datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
        )
        other = TransactionsDTO(
            id=uuid.uuid4(),
            owner_id=owner.id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=9.0,
            template_id=uuid.uuid4(),
            transaction_ts=datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc),
        )
        service.transactions_service.get_transactions_frame.return_value = pd.DataFrame(
            [
                older.model_dump(mode="python"),
                newer.model_dump(mode="python"),
                other.model_dump(mode="python"),
            ]
        )
        paid = service._paid_postings_by_template(
            owner=owner,
            dues_by_template={template_id: date(2026, 8, 15)},
        )
        assert paid[template_id].id == newer.id


class TestMarkPaidClearPaid:
    """mark_paid / clear_paid orchestration."""

    def test_mark_paid_expense_uses_from_account(self, owner: UsersDTO):
        """EXPENSE mark-paid posts from_account_id and template_id."""
        service = _templates_service()
        account_id = uuid.uuid4()
        category_id = uuid.uuid4()
        template = _template(
            category_id=category_id,
            from_account_id=account_id,
            planned_day=15,
            due_date=None,
        )
        category = CategoriesDTO(
            id=category_id,
            name="Bills",
            category_kind=CategoryKind.EXPENSE,
            owner_id=owner.id,
        )
        account = AccountsDTO(
            id=account_id,
            name="Checking",
            description="",
            owner_id=owner.id,
            account_kind=AccountKind.CHECKING,
            ledger_side=LedgerSide.ASSET,
        )
        created = TransactionsDTO(
            id=uuid.uuid4(),
            owner_id=owner.id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=template.planned_amount,
            from_account_id=account_id,
            template_id=template.id,
            category_id=category_id,
            status=TransactionStatus.COMPLETED,
        )
        service.categories_service.get.return_value = category
        service.accounts_service.get.return_value = account
        service.transactions_service.create.return_value = created

        with (
            patch.object(TransactionTemplatesService, "get", return_value=template),
            patch.object(TransactionTemplatesService, "_paid_posting_for_period", return_value=None),
        ):
            result = service.mark_paid(template_id=template.id, owner=owner, as_of=date(2026, 8, 1))

        assert result is created
        posted = service.transactions_service.create.call_args.kwargs["obj"]
        assert posted.transaction_kind == TransactionKind.EXPENSE
        assert posted.from_account_id == account_id
        assert posted.to_account_id is None
        assert posted.template_id == template.id
        assert posted.amount == template.planned_amount

    def test_mark_paid_income_uses_to_account(self, owner: UsersDTO):
        """INCOME mark-paid maps template from_account_id to to_account_id."""
        service = _templates_service()
        account_id = uuid.uuid4()
        category_id = uuid.uuid4()
        template = _template(category_id=category_id, from_account_id=account_id, name="Paycheck")
        category = CategoriesDTO(
            id=category_id,
            name="Salary",
            category_kind=CategoryKind.INCOME,
            owner_id=owner.id,
        )
        service.categories_service.get.return_value = category
        service.accounts_service.get.return_value = AccountsDTO(
            id=account_id,
            name="Checking",
            description="",
            owner_id=owner.id,
            account_kind=AccountKind.CHECKING,
            ledger_side=LedgerSide.ASSET,
        )
        service.transactions_service.create.return_value = TransactionsDTO(
            owner_id=owner.id,
            transaction_kind=TransactionKind.INCOME,
            amount=1.0,
            to_account_id=account_id,
            template_id=template.id,
        )

        with (
            patch.object(TransactionTemplatesService, "get", return_value=template),
            patch.object(TransactionTemplatesService, "_paid_posting_for_period", return_value=None),
        ):
            service.mark_paid(template_id=template.id, owner=owner, as_of=date(2026, 8, 1))

        posted = service.transactions_service.create.call_args.kwargs["obj"]
        assert posted.transaction_kind == TransactionKind.INCOME
        assert posted.to_account_id == account_id
        assert posted.from_account_id is None

    def test_mark_paid_rejects_already_paid(self, owner: UsersDTO):
        """Second mark-paid in the same period raises."""
        service = _templates_service()
        template = _template()
        paid = TransactionsDTO(
            id=uuid.uuid4(),
            owner_id=owner.id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=10.0,
            template_id=template.id,
        )
        with (
            patch.object(TransactionTemplatesService, "get", return_value=template),
            patch.object(TransactionTemplatesService, "_paid_posting_for_period", return_value=paid),
            pytest.raises(ValueError, match="already marked paid"),
        ):
            service.mark_paid(template_id=template.id, owner=owner, as_of=date(2026, 8, 1))

    def test_mark_paid_requires_account(self, owner: UsersDTO):
        """Missing from_account_id is rejected."""
        service = _templates_service()
        category_id = uuid.uuid4()
        template = _template(from_account_id=None, category_id=category_id)
        service.categories_service.get.return_value = CategoriesDTO(
            id=category_id,
            name="Bills",
            category_kind=CategoryKind.EXPENSE,
            owner_id=owner.id,
        )
        with (
            patch.object(TransactionTemplatesService, "get", return_value=template),
            patch.object(TransactionTemplatesService, "_paid_posting_for_period", return_value=None),
            pytest.raises(ValueError, match="from_account_id is required"),
        ):
            service.mark_paid(template_id=template.id, owner=owner, as_of=date(2026, 8, 1))

    def test_clear_paid_soft_deletes(self, owner: UsersDTO):
        """clear_paid soft-deletes the period-linked posting."""
        service = _templates_service()
        template = _template()
        paid = TransactionsDTO(
            id=uuid.uuid4(),
            owner_id=owner.id,
            transaction_kind=TransactionKind.EXPENSE,
            amount=10.0,
            template_id=template.id,
        )
        with (
            patch.object(TransactionTemplatesService, "get", return_value=template),
            patch.object(TransactionTemplatesService, "_paid_posting_for_period", return_value=paid),
        ):
            result = service.clear_paid(template_id=template.id, owner=owner, as_of=date(2026, 8, 1))

        assert result is paid
        service.transactions_service.delete.assert_called_once()
        assert service.transactions_service.delete.call_args.kwargs["hard"] is False

    def test_clear_paid_raises_when_unpaid(self, owner: UsersDTO):
        """clear_paid fails when no linked posting exists for the period."""
        service = _templates_service()
        template = _template()
        with (
            patch.object(TransactionTemplatesService, "get", return_value=template),
            patch.object(TransactionTemplatesService, "_paid_posting_for_period", return_value=None),
            pytest.raises(ValueError, match="not marked paid"),
        ):
            service.clear_paid(template_id=template.id, owner=owner, as_of=date(2026, 8, 1))
