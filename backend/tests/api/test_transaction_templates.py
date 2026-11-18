"""Tests for transaction-template endpoints (PPT-073 / #166)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
from fastapi.testclient import TestClient

from papita_txnsmodel.access.transactions.dto import TransactionsDTO, TransactionTemplatesDTO
from papita_txnsmodel.model.enums import TransactionKind, TransactionStatus
from papita_txnsmodel.services.dues import UpcomingDueDTO


def _sample_template(owner_id: uuid.UUID, **overrides) -> TransactionTemplatesDTO:
    now = datetime.now(timezone.utc)
    payload = {
        "id": uuid.uuid4(),
        "name": "Rent",
        "description": "Monthly rent",
        "owner_id": owner_id,
        "category_id": uuid.uuid4(),
        "planned_amount": 1200.0,
        "planned_day": 1,
        "use_month_end": False,
        "due_date": None,
        "remind_days_before": 3,
        "from_account_id": uuid.uuid4(),
        "tags": ["housing"],
        "active": True,
        "created_at": now,
        "updated_at": now,
    }
    payload.update(overrides)
    return TransactionTemplatesDTO(**payload)


def _sample_transaction(owner_id: uuid.UUID, *, template_id: uuid.UUID) -> TransactionsDTO:
    now = datetime.now(timezone.utc)
    return TransactionsDTO(
        id=uuid.uuid4(),
        owner_id=owner_id,
        transaction_kind=TransactionKind.EXPENSE,
        amount=1200.0,
        currency="USD",
        transaction_ts=now,
        from_account_id=uuid.uuid4(),
        to_account_id=None,
        category_id=uuid.uuid4(),
        template_id=template_id,
        status=TransactionStatus.COMPLETED,
        description="Rent",
        tags=["housing"],
        created_at=now,
        updated_at=now,
    )


class TestTransactionTemplatesAuth:
    """Protected route contract."""

    def test_list_templates_without_token_returns_401(self, client: TestClient) -> None:
        response = client.get("/api/v1/transaction-templates")
        assert response.status_code == 401

    def test_upcoming_dues_without_token_returns_401(self, client: TestClient) -> None:
        response = client.get("/api/v1/transaction-templates/upcoming-dues")
        assert response.status_code == 401


class TestTransactionTemplatesRoutes:
    """Template CRUD with mocked TransactionTemplatesService."""

    def test_list_templates_returns_paginated_items(
        self,
        templates_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = templates_client
        template = _sample_template(owner.id)
        mock_service.count_records.return_value = 1
        mock_service.get_records.return_value = pd.DataFrame([template.model_dump(mode="python")])

        response = client.get("/api/v1/transaction-templates")

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert payload["items"][0]["name"] == "Rent"
        assert payload["items"][0]["remind_days_before"] == 3
        mock_service.count_records.assert_called_once()
        mock_service.get_records.assert_called_once()
        assert mock_service.get_records.call_args.kwargs["skip"] == 0
        assert mock_service.get_records.call_args.kwargs["limit"] == 100
        assert mock_service.get_records.call_args.kwargs["owner"] is owner

    def test_list_templates_forwards_category_and_active_filters(
        self,
        templates_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = templates_client
        category_id = uuid.uuid4()
        mock_service.count_records.return_value = 0
        mock_service.get_records.return_value = pd.DataFrame([])

        response = client.get(
            "/api/v1/transaction-templates",
            params={"category_id": str(category_id), "is_active": "false"},
        )

        assert response.status_code == 200
        filter_dto = mock_service.get_records.call_args.kwargs["dto"]
        assert filter_dto is not None
        assert filter_dto.category_id == category_id
        assert filter_dto.active is False
        assert mock_service.get_records.call_args.kwargs["owner"] is owner
        assert mock_service.count_records.call_args.kwargs["dto"] is filter_dto

    def test_get_template_not_found_returns_404(
        self,
        templates_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, _owner, mock_service = templates_client
        mock_service.get.return_value = None

        response = client.get(f"/api/v1/transaction-templates/{uuid.uuid4()}")

        assert response.status_code == 404
        assert response.json()["detail"] == "Transaction template not found"

    def test_create_template_returns_201(
        self,
        templates_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = templates_client
        category_id = uuid.uuid4()
        created = _sample_template(owner.id, category_id=category_id, name="Internet")
        mock_service.create.return_value = created

        response = client.post(
            "/api/v1/transaction-templates",
            json={
                "name": "Internet",
                "category_id": str(category_id),
                "planned_amount": 80.0,
                "planned_day": 15,
                "remind_days_before": 2,
            },
        )

        assert response.status_code == 201
        assert response.json()["name"] == "Internet"
        mock_service.create.assert_called_once()
        assert mock_service.create.call_args.kwargs["owner"] is owner

    def test_update_template_merges_fields(
        self,
        templates_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = templates_client
        existing = _sample_template(owner.id, name="Old")
        updated = _sample_template(owner.id, id=existing.id, name="New", planned_amount=1300.0)
        mock_service.get.return_value = existing
        mock_service.create.return_value = updated

        response = client.put(
            f"/api/v1/transaction-templates/{existing.id}",
            json={"name": "New", "planned_amount": 1300.0},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "New"
        assert response.json()["planned_amount"] == 1300.0

    def test_delete_template_returns_204(
        self,
        templates_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = templates_client
        existing = _sample_template(owner.id)
        mock_service.get.return_value = existing

        response = client.delete(f"/api/v1/transaction-templates/{existing.id}")

        assert response.status_code == 204
        mock_service.delete.assert_called_once()
        assert mock_service.delete.call_args.kwargs["owner"] is owner
        assert mock_service.delete.call_args.kwargs["hard"] is False


class TestUpcomingDuesAndMarkPaid:
    """Dues window and mark-paid / clear-paid endpoints."""

    def test_upcoming_dues_returns_items(
        self,
        templates_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = templates_client
        template = _sample_template(owner.id)
        mock_service.list_upcoming_dues.return_value = [
            UpcomingDueDTO(
                template=template,
                due_date=date(2026, 8, 12),
                remind_start=date(2026, 8, 9),
                is_paid=False,
                paid_transaction_id=None,
            )
        ]

        response = client.get(
            "/api/v1/transaction-templates/upcoming-dues",
            params={"as_of": "2026-08-10", "window_days": 7, "include_paid": False},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["as_of"] == "2026-08-10"
        assert payload["window_days"] == 7
        assert len(payload["items"]) == 1
        assert payload["items"][0]["due_date"] == "2026-08-12"
        assert payload["items"][0]["template"]["id"] == str(template.id)
        mock_service.list_upcoming_dues.assert_called_once_with(
            owner=owner,
            as_of=date(2026, 8, 10),
            window_days=7,
            include_paid=False,
        )

    def test_mark_paid_returns_created_transaction(
        self,
        templates_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = templates_client
        template_id = uuid.uuid4()
        posted = _sample_transaction(owner.id, template_id=template_id)
        mock_service.mark_paid.return_value = posted

        response = client.post(
            f"/api/v1/transaction-templates/{template_id}/mark-paid",
            json={"as_of": "2026-08-01"},
        )

        assert response.status_code == 201
        assert response.json()["template_id"] == str(template_id)
        mock_service.mark_paid.assert_called_once()
        assert mock_service.mark_paid.call_args.kwargs["template_id"] == template_id
        assert mock_service.mark_paid.call_args.kwargs["owner"] is owner
        assert mock_service.mark_paid.call_args.kwargs["as_of"] == date(2026, 8, 1)

    def test_mark_paid_flattens_nested_template_dto(
        self,
        templates_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        """LinkedEntitiesService.create hydrates template_id as a nested DTO."""
        client, owner, mock_service = templates_client
        template = _sample_template(owner.id)
        assert template.id is not None
        posted = _sample_transaction(owner.id, template_id=template.id)
        posted.template_id = template  # type: ignore[assignment]
        mock_service.mark_paid.return_value = posted

        response = client.post(
            f"/api/v1/transaction-templates/{template.id}/mark-paid",
            json={},
        )

        assert response.status_code == 201, response.text
        assert response.json()["template_id"] == str(template.id)

    def test_mark_paid_already_paid_returns_409(
        self,
        templates_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, _owner, mock_service = templates_client
        mock_service.mark_paid.side_effect = ValueError("Template due is already marked paid for this period.")

        response = client.post(f"/api/v1/transaction-templates/{uuid.uuid4()}/mark-paid", json={})

        assert response.status_code == 409
        assert "already marked paid" in response.json()["detail"]

    def test_mark_paid_missing_template_returns_404(
        self,
        templates_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, _owner, mock_service = templates_client
        mock_service.mark_paid.side_effect = ValueError("Transaction template not found.")

        response = client.post(f"/api/v1/transaction-templates/{uuid.uuid4()}/mark-paid", json={})

        assert response.status_code == 404

    def test_clear_paid_returns_transaction(
        self,
        templates_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = templates_client
        template_id = uuid.uuid4()
        cleared = _sample_transaction(owner.id, template_id=template_id)
        mock_service.clear_paid.return_value = cleared

        response = client.post(
            f"/api/v1/transaction-templates/{template_id}/clear-paid",
            json={"as_of": "2026-08-01"},
        )

        assert response.status_code == 200
        assert response.json()["id"] == str(cleared.id)
        mock_service.clear_paid.assert_called_once_with(
            template_id=template_id,
            owner=owner,
            as_of=date(2026, 8, 1),
        )
