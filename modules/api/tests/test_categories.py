"""Tests for category endpoints (PPT-036)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
from fastapi.testclient import TestClient

from auth_helpers import make_user
from papita_txnsapi.config.settings import get_settings
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.services import get_categories_service
from papita_txnsapi.main import create_app
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.model.enums import CategoryKind


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
        rows = pd.DataFrame([parent.model_dump(mode="python"), child.model_dump(mode="python")])
        mock_service.get_records.return_value = rows

        response = client.get("/api/v1/categories")

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert len(payload["items"][0]["subcategories"]) == 1
        assert payload["items"][0]["subcategories"][0]["name"] == "Restaurants"

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
