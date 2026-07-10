"""Category CRUD routes — PPT-036."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.pagination import PaginationParams, get_pagination
from papita_txnsapi.dependencies.services import get_categories_service
from papita_txnsapi.schemas.categories import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    build_subcategory_map,
    categories_from_dataframe,
)
from papita_txnsapi.schemas.common import PaginatedResponse
from papita_txnsapi.schemas.converters import parse_category_kind
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.categories import CategoriesService

router = APIRouter(prefix="/categories", tags=["Categories"])

_GLOBAL_CATEGORY_MESSAGES = frozenset(
    {
        "Tenants cannot create or modify global categories.",
        "Tenants cannot modify global categories.",
    }
)


def _category_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")


def _reject_global_category(category) -> None:
    """Global seeds are readable but not mutable by tenants (G7 / FR-15)."""
    if category.owner_id is None:
        raise _category_not_found()


@router.get("", response_model=PaginatedResponse[CategoryResponse])
def list_categories(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    categories_service: Annotated[CategoriesService, Depends(get_categories_service)],
    parent_id: Annotated[uuid.UUID | None, Query(description="Filter by parent category")] = None,
    category_type: Annotated[str | None, Query(description="Filter by income or expense")] = None,
) -> PaginatedResponse[CategoryResponse]:
    """List tenant and global seed categories with optional hierarchy nesting."""
    records_df = categories_service.get_records(None, owner=owner)
    all_categories = categories_from_dataframe(records_df)

    filtered = all_categories
    if category_type is not None:
        kind = parse_category_kind(category_type)
        filtered = [category for category in filtered if category.category_kind == kind]
    if parent_id is not None:
        filtered = [category for category in filtered if category.parent_id == parent_id]

    subcategory_map = build_subcategory_map(all_categories)

    if parent_id is None:
        top_level = [category for category in filtered if category.parent_id is None]
        page = top_level[pagination.skip : pagination.skip + pagination.limit]
        items = [
            CategoryResponse.from_dto(
                category,
                subcategories=subcategory_map.get(category.id, []) if category.id is not None else [],
            )
            for category in page
        ]
        return PaginatedResponse(
            items=items,
            total=len(top_level),
            skip=pagination.skip,
            limit=pagination.limit,
        )

    page = filtered[pagination.skip : pagination.skip + pagination.limit]
    items = [CategoryResponse.from_dto(category) for category in page]
    return PaginatedResponse(
        items=items,
        total=len(filtered),
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    categories_service: Annotated[CategoriesService, Depends(get_categories_service)],
) -> CategoryResponse:
    """Retrieve a tenant-owned or global seed category by id."""
    category = categories_service.get(obj=category_id, owner=owner)
    if category is None:
        raise _category_not_found()
    return CategoryResponse.from_dto(category)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CategoryResponse)
def create_category(
    body: CategoryCreate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    categories_service: Annotated[CategoriesService, Depends(get_categories_service)],
) -> CategoryResponse:
    """Create a tenant-owned category."""
    try:
        created = categories_service.create(obj=body.to_categories_dto(), owner=owner)
    except ValueError as exc:
        if str(exc) in _GLOBAL_CATEGORY_MESSAGES:
            raise _category_not_found() from exc
        raise
    return CategoryResponse.from_dto(created)


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: uuid.UUID,
    body: CategoryUpdate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    categories_service: Annotated[CategoriesService, Depends(get_categories_service)],
) -> CategoryResponse:
    """Update a tenant-owned category."""
    existing = categories_service.get(obj=category_id, owner=owner)
    if existing is None:
        raise _category_not_found()
    _reject_global_category(existing)

    merged = body.apply_to(existing)
    try:
        updated = categories_service.create(obj=merged, owner=owner)
    except ValueError as exc:
        if str(exc) in _GLOBAL_CATEGORY_MESSAGES:
            raise _category_not_found() from exc
        raise
    return CategoryResponse.from_dto(updated)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    categories_service: Annotated[CategoriesService, Depends(get_categories_service)],
) -> None:
    """Soft-delete a tenant-owned category."""
    existing = categories_service.get(obj=category_id, owner=owner)
    if existing is None:
        raise _category_not_found()
    _reject_global_category(existing)
    categories_service.delete(obj=CategoriesDTO.model_construct(id=category_id), owner=owner)
