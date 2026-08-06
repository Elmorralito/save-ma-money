"""Unit tests for TransactionTemplatesDTO payment-due fields (PPT-071)."""

import datetime
import uuid

import pytest
from pydantic import ValidationError

from papita_txnsmodel.access.transactions.dto import TransactionTemplatesDTO
from papita_txnsmodel.model.transactions import TransactionTemplates


def _base_kwargs(**overrides):
    """Minimal valid template payload with optional field overrides."""
    payload = {
        "owner_id": uuid.uuid4(),
        "category_id": uuid.uuid4(),
        "name": "Rent",
        "planned_amount": 1200.0,
        "planned_day": 1,
        "use_month_end": False,
    }
    payload.update(overrides)
    return payload


class TestTransactionTemplatesDTOPaymentDues:
    """PPT-071 additive due fields round-trip and validate."""

    def test_defaults_leave_due_fields_null(self):
        """Existing recurring shape stays valid without due columns set."""
        dto = TransactionTemplatesDTO(**_base_kwargs())
        assert dto.due_date is None
        assert dto.remind_days_before is None
        assert dto.from_account_id is None

    def test_accepts_one_off_due_fields(self):
        """One-off due date, remind lead, and pay-from account are stored."""
        account_id = uuid.uuid4()
        due = datetime.date(2026, 9, 15)
        dto = TransactionTemplatesDTO(
            **_base_kwargs(
                due_date=due,
                remind_days_before=3,
                from_account_id=account_id,
            )
        )
        assert dto.due_date == due
        assert dto.remind_days_before == 3
        assert dto.from_account_id == account_id

    def test_remind_days_before_rejects_negative(self):
        """Lead window cannot be negative."""
        with pytest.raises(ValidationError):
            TransactionTemplatesDTO(**_base_kwargs(remind_days_before=-1))

    def test_from_dao_round_trip_includes_due_fields(self):
        """DAO → DTO preserves payment-due columns."""
        owner_id = uuid.uuid4()
        category_id = uuid.uuid4()
        account_id = uuid.uuid4()
        due = datetime.date(2026, 10, 1)
        dao = TransactionTemplates(
            owner_id=owner_id,
            category_id=category_id,
            name="Insurance",
            planned_amount=50.0,
            planned_day=1,
            use_month_end=False,
            due_date=due,
            remind_days_before=7,
            from_account_id=account_id,
        )
        dto = TransactionTemplatesDTO.from_dao(dao)
        assert dto.due_date == due
        assert dto.remind_days_before == 7
        assert dto.from_account_id == account_id
