"""Tests for category endpoints (PPT-036)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
from fastapi.testclient import TestClient

from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.model.enums import CashflowBucket, CategoryKind


def _sample_category(*, owner_id: uuid.UUID | None = None, parent_id: uuid.UUID | None = None) -> CategoriesDTO:
    now = datetime.now(timezone.utc)
    return CategoriesDTO(
        id=uuid.uuid4(),
        name="Food & Dining",
        description="Meals",
        tags=["food", "dining"],
        category_kind=CategoryKind.EXPENSE,
        owner_id=owner_id,
        parent_id=parent_id,
        icon="utensils",
        color="#FF5733",
        created_at=now,
        updated_at=now,
    )


class TestCategoriesAuth:
    """Protected route contract."""

    def test_list_categories_without_token_returns_401(self, client: TestClient) -> None:
        response = client.get("/api/v1/categories")
        assert response.status_code == 401


class TestCategoriesRoutes:
    """Category CRUD with mocked CategoriesService."""

    def test_list_categories_nests_subcategories(
        self,
        categories_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = categories_client
        parent = _sample_category(owner_id=owner.id)
        child = _sample_category(owner_id=owner.id, parent_id=parent.id)
        child.name = "Restaurants"
        mock_service.list_categories.return_value = (
            pd.DataFrame([parent.model_dump(mode="python")]),
            1,
        )
        mock_service.get_categories_for_parents.return_value = pd.DataFrame([child.model_dump(mode="python")])

        response = client.get("/api/v1/categories")

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert len(payload["items"][0]["subcategories"]) == 1
        assert payload["items"][0]["subcategories"][0]["name"] == "Restaurants"
        mock_service.list_categories.assert_called_once()
        assert mock_service.list_categories.call_args.kwargs["roots_only"] is True
        assert mock_service.list_categories.call_args.kwargs["skip"] == 0

    def test_create_category_returns_201(
        self,
        categories_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = categories_client
        created = _sample_category(owner_id=owner.id)
        mock_service.create.return_value = created

        response = client.post(
            "/api/v1/categories",
            json={
                "name": "Entertainment",
                "category_type": "expense",
                "icon": "film",
                "color": "#9B59B6",
            },
        )

        assert response.status_code == 201
        assert response.json()["category_type"] == "expense"

    def test_category_cashflow_bucket_create_and_clear(
        self,
        categories_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, owner, mock_service = categories_client
        created = _sample_category(owner_id=owner.id).model_copy(
            update={"cashflow_bucket": CashflowBucket.FIXED_EXPENSE}
        )
        cleared = created.model_copy(update={"cashflow_bucket": None})
        mock_service.create.side_effect = [created, cleared]
        mock_service.get.return_value = created

        create_resp = client.post(
            "/api/v1/categories",
            json={
                "name": "Rent",
                "category_type": "expense",
                "cashflow_bucket": "fixed_expense",
            },
        )
        assert create_resp.status_code == 201
        assert create_resp.json()["cashflow_bucket"] == "fixed_expense"

        update_resp = client.put(
            f"/api/v1/categories/{created.id}",
            json={"cashflow_bucket": None},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["cashflow_bucket"] is None
        sent_dto = mock_service.create.call_args_list[1].kwargs["obj"]
        assert sent_dto.cashflow_bucket is None

    def test_update_global_category_returns_404(
        self,
        categories_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, _owner, mock_service = categories_client
        global_category = _sample_category(owner_id=None)
        mock_service.get.return_value = global_category

        response = client.put(
            f"/api/v1/categories/{global_category.id}",
            json={"name": "Tampered"},
        )

        assert response.status_code == 404

    def test_delete_global_category_returns_404(
        self,
        categories_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, _owner, mock_service = categories_client
        global_category = _sample_category(owner_id=None)
        mock_service.get.return_value = global_category

        response = client.delete(f"/api/v1/categories/{global_category.id}")

        assert response.status_code == 404
        mock_service.delete.assert_not_called()

    def test_get_category_not_found_returns_404(
        self,
        categories_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, _owner, mock_service = categories_client
        mock_service.get.return_value = None

        response = client.get(f"/api/v1/categories/{uuid.uuid4()}")

        assert response.status_code == 404


class TestCategoriesTenancy:
    """Cross-tenant category access returns 404."""

    def test_get_other_tenant_category_returns_404(
        self,
        categories_client: tuple[TestClient, object, MagicMock],
    ) -> None:
        client, _owner, mock_service = categories_client
        mock_service.get.return_value = None

        response = client.get(f"/api/v1/categories/{uuid.uuid4()}")

        assert response.status_code == 404


class TestCategoriesOpenAPI:
    """OpenAPI registration."""

    def test_categories_routes_registered(self, client: TestClient) -> None:
        schema = client.get("/api/openapi.json").json()
        assert "/api/v1/categories" in schema["paths"]
        assert "/api/v1/categories/{category_id}" in schema["paths"]
