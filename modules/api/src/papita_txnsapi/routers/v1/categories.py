"""Category CRUD routes — PPT-036.

Exposes tenant-scoped category management under ``/categories``. Handlers require an
authenticated owner and delegate to
:class:`~papita_txnsmodel.services.categories.CategoriesService`. Global seed
categories (``owner_id is None``) are readable but not mutable per G7 / FR-15.

Routes:
    ``GET /categories`` — paginated list with optional parent and kind filters.
    ``GET /categories/{category_id}`` — single tenant-owned or global seed category.
    ``POST /categories`` — create tenant-owned category.
    ``PUT /categories/{category_id}`` — update tenant-owned category.
    ``DELETE /categories/{category_id}`` — soft-delete tenant-owned category.

Tenant scoping:
    List and read operations return both tenant-owned and global seed rows visible to
    the owner. Create, update, and delete pass ``owner`` to the service and reject
    mutations on global seeds.

Service delegation:
    Lists use ``list_categories`` / ``get_categories_for_parents``; reads use ``get``;
    mutations use ``create`` (upsert) and ``delete``. Global-category guard violations
    from the service are mapped to 404.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from redis import Redis

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.cache import (
    CacheNamespace,
    bump_cache_versions,
    get_versioned_cached_json,
    set_versioned_cached_json,
    ttl_for_namespace,
)
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.pagination import PaginationParams, get_pagination
from papita_txnsapi.dependencies.rate_limit import enforce_tenant_api_rate_limit
from papita_txnsapi.dependencies.redis import get_optional_redis
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

router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
    dependencies=[Depends(enforce_tenant_api_rate_limit)],
)

_GLOBAL_CATEGORY_MESSAGES = frozenset(
    {
        "Tenants cannot create or modify global categories.",
        "Tenants cannot modify global categories.",
    }
)


def _category_not_found() -> HTTPException:
    """Build a 404 response for a missing, global, or inaccessible category.

    Returns:
        HTTPException: 404 with a generic "Category not found" detail to avoid leaking
            cross-tenant or global-mutation restrictions.
    """
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")


def _reject_global_category(category) -> None:
    """Block mutations on global seed categories (G7 / FR-15).

    Args:
        category: Category DTO fetched for the current request.

    Raises:
        HTTPException: 404 when ``category.owner_id`` is ``None`` (global seed).
    """
    if category.owner_id is None:
        raise _category_not_found()


def _invalidate_category_caches(redis: Redis | None, owner: UsersDTO) -> None:
    """Bump categories + reports versions after category mutations."""
    bump_cache_versions(redis, owner.id, CacheNamespace.CATEGORIES, CacheNamespace.REPORTS)


@router.get("", response_model=PaginatedResponse[CategoryResponse])
def list_categories(  # pylint: disable=too-many-positional-arguments,too-many-locals
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    categories_service: Annotated[CategoriesService, Depends(get_categories_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    response: Response,
    parent_id: Annotated[uuid.UUID | None, Query(description="Filter by parent category")] = None,
    category_type: Annotated[str | None, Query(description="Filter by income or expense")] = None,
) -> PaginatedResponse[CategoryResponse]:
    """List tenant and global seed categories with optional hierarchy nesting.

    When Redis is enabled, list responses are cache-aside with versioned keys.

    Args:
        owner: Authenticated tenant from JWT.
        pagination: Skip/limit window for the response page.
        categories_service: Injected categories service scoped to the request lifecycle.
        settings: Application settings (cache TTL).
        redis: Optional Redis client when ``REDIS_ENABLED``.
        response: FastAPI response used to set ``X-Cache`` status.
        parent_id: Optional parent category id; when omitted, returns top-level categories
            with nested subcategory summaries.
        category_type: Optional income/expense slug filter.

    Returns:
        Paginated categories; top-level rows include embedded subcategory lists when
        ``parent_id`` is not set.
    """
    cache_params = {
        "skip": pagination.skip,
        "limit": pagination.limit,
        "parent_id": str(parent_id) if parent_id is not None else None,
        "category_type": category_type,
    }
    owner_id = owner.id
    if owner_id is not None:
        cached, cache_status, cache_version = get_versioned_cached_json(
            redis, owner_id, CacheNamespace.CATEGORIES, "categories:list", cache_params
        )
        response.headers["X-Cache"] = cache_status
        if cached is not None:
            return PaginatedResponse[CategoryResponse].model_validate(cached)
    else:
        response.headers["X-Cache"] = "BYPASS"
        cache_version = 0

    kind = parse_category_kind(category_type) if category_type is not None else None
    payload: PaginatedResponse[CategoryResponse]
    if parent_id is None:
        page_df, total = categories_service.list_categories(
            owner=owner,
            roots_only=True,
            category_kind=kind,
            skip=pagination.skip,
            limit=pagination.limit,
        )
        page_categories = categories_from_dataframe(page_df)
        parent_ids = [category.id for category in page_categories if category.id is not None]
        children_df = categories_service.get_categories_for_parents(
            owner=owner,
            parent_ids=parent_ids,
            category_kind=kind,
        )
        subcategory_map = build_subcategory_map(categories_from_dataframe(children_df))
        items = [
            CategoryResponse.from_dto(
                category,
                subcategories=subcategory_map.get(category.id, []) if category.id is not None else [],
            )
            for category in page_categories
        ]
        payload = PaginatedResponse(
            items=items,
            total=total,
            skip=pagination.skip,
            limit=pagination.limit,
        )
    else:
        page_df, total = categories_service.list_categories(
            owner=owner,
            parent_id=parent_id,
            category_kind=kind,
            skip=pagination.skip,
            limit=pagination.limit,
        )
        items = [CategoryResponse.from_dto(category) for category in categories_from_dataframe(page_df)]
        payload = PaginatedResponse(
            items=items,
            total=total,
            skip=pagination.skip,
            limit=pagination.limit,
        )

    if owner_id is not None:
        set_versioned_cached_json(
            redis,
            owner_id,
            CacheNamespace.CATEGORIES,
            "categories:list",
            cache_params,
            value=payload.model_dump(mode="json"),
            ttl_seconds=ttl_for_namespace(settings, CacheNamespace.CATEGORIES),
            version=cache_version,
        )
    return payload


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    categories_service: Annotated[CategoriesService, Depends(get_categories_service)],
) -> CategoryResponse:
    """Retrieve a tenant-owned or global seed category by id.

    Args:
        category_id: Primary key of the category to fetch.
        owner: Authenticated tenant from JWT.
        categories_service: Injected categories service scoped to the request lifecycle.

    Returns:
        Category payload for a visible tenant-owned or global seed row.

    Raises:
        HTTPException: 404 when the category is not visible to the tenant.
    """
    category = categories_service.get(obj=category_id, owner=owner)
    if category is None:
        raise _category_not_found()
    return CategoryResponse.from_dto(category)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CategoryResponse)
def create_category(
    body: CategoryCreate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    categories_service: Annotated[CategoriesService, Depends(get_categories_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> CategoryResponse:
    """Create a tenant-owned category.

    Args:
        body: Validated create payload converted to a categories DTO.
        owner: Authenticated tenant from JWT.
        categories_service: Injected categories service scoped to the request lifecycle.
        redis: Optional Redis client for cache invalidation.

    Returns:
        Newly created category owned by the authenticated tenant.

    Raises:
        HTTPException: 404 when the service rejects global-category mutation attempts.
        ValueError: Propagated for other validation failures from the service layer.
    """
    try:
        created = categories_service.create(obj=body.to_categories_dto(), owner=owner)
    except ValueError as exc:
        if str(exc) in _GLOBAL_CATEGORY_MESSAGES:
            raise _category_not_found() from exc
        raise
    _invalidate_category_caches(redis, owner)
    return CategoryResponse.from_dto(created)


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: uuid.UUID,
    body: CategoryUpdate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    categories_service: Annotated[CategoriesService, Depends(get_categories_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> CategoryResponse:
    """Update a tenant-owned category.

    Args:
        category_id: Primary key of the category to update.
        body: Partial update payload merged onto the existing DTO.
        owner: Authenticated tenant from JWT.
        categories_service: Injected categories service scoped to the request lifecycle.
        redis: Optional Redis client for cache invalidation.

    Returns:
        Updated category owned by the authenticated tenant.

    Raises:
        HTTPException: 404 when the category is missing, global, or not owned by the tenant.
        ValueError: Propagated for other validation failures from the service layer.
    """
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
    _invalidate_category_caches(redis, owner)
    return CategoryResponse.from_dto(updated)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    categories_service: Annotated[CategoriesService, Depends(get_categories_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> None:
    """Soft-delete a tenant-owned category.

    Args:
        category_id: Primary key of the category to delete.
        owner: Authenticated tenant from JWT.
        categories_service: Injected categories service scoped to the request lifecycle.
        redis: Optional Redis client for cache invalidation.

    Returns:
        ``None``; response body is empty on success.

    Raises:
        HTTPException: 404 when the category is missing, global, or not owned by the tenant.
    """
    existing = categories_service.get(obj=category_id, owner=owner)
    if existing is None:
        raise _category_not_found()
    _reject_global_category(existing)
    categories_service.delete(obj=CategoriesDTO.model_construct(id=category_id), owner=owner)
    _invalidate_category_caches(redis, owner)
