"""Transaction-template CRUD and payment-dues routes — PPT-073 / #166.

Exposes tenant-scoped template management under ``/transaction-templates``.
Handlers require JWT auth via ``get_current_owner`` and delegate persistence and
due logic to
:class:`~papita_txnsmodel.services.transactions.TransactionTemplatesService`.

Routes:
    ``GET /transaction-templates`` — paginated list with optional filters.
    ``GET /transaction-templates/upcoming-dues`` — owner-scoped upcoming dues window.
    ``GET /transaction-templates/{template_id}`` — single template.
    ``POST /transaction-templates`` — create template.
    ``PUT /transaction-templates/{template_id}`` — update tenant-owned template.
    ``DELETE /transaction-templates/{template_id}`` — soft-delete template.
    ``POST /transaction-templates/{template_id}/mark-paid`` — post linked txn.
    ``POST /transaction-templates/{template_id}/clear-paid`` — soft-delete paid posting.

Tenant scoping:
    Every path passes ``owner=`` so templates never leak across tenants.
    Cross-tenant ids resolve as not found (404).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis import Redis

from papita_txnsapi.core.cache import CacheNamespace, bump_cache_versions
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.pagination import PaginationParams, get_pagination
from papita_txnsapi.dependencies.rate_limit import enforce_tenant_api_rate_limit
from papita_txnsapi.dependencies.redis import get_optional_redis
from papita_txnsapi.dependencies.services import get_transaction_templates_service
from papita_txnsapi.schemas.common import PaginatedResponse
from papita_txnsapi.schemas.query_params import UpcomingDuesQuery, get_upcoming_dues_query
from papita_txnsapi.schemas.transaction_templates import (
    ClearPaidRequest,
    MarkPaidRequest,
    TransactionTemplateCreate,
    TransactionTemplateResponse,
    TransactionTemplateUpdate,
    UpcomingDueResponse,
    UpcomingDuesResponse,
    templates_from_dataframe,
)
from papita_txnsapi.schemas.transactions import TransactionResponse
from papita_txnsmodel.access.transactions.dto import TransactionTemplatesDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.transactions import TransactionTemplatesService

router = APIRouter(
    prefix="/transaction-templates",
    tags=["Transaction templates"],
    dependencies=[Depends(enforce_tenant_api_rate_limit)],
)

_TEMPLATE_NOT_FOUND = "Transaction template not found."
_CONFLICT_MESSAGES = frozenset(
    {
        "Template due is already marked paid for this period.",
        "Template due is not marked paid for this period.",
    }
)


def _template_not_found() -> HTTPException:
    """Build a 404 that avoids leaking cross-tenant template existence."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction template not found")


def _require_uuid(value: uuid.UUID | None) -> uuid.UUID:
    """Return a persisted UUID or raise when the DTO has no primary key."""
    if value is None:
        raise _template_not_found()
    return value


def _require_owner_id(owner: UsersDTO) -> uuid.UUID:
    """Return the authenticated owner's primary key."""
    if owner.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid owner context")
    return owner.id


def _invalidate_dues_caches(redis: Redis | None, owner: UsersDTO) -> None:
    """Bump ledger caches after mark-paid / clear-paid / template mutations."""
    bump_cache_versions(
        redis,
        owner.id,
        CacheNamespace.TRANSACTIONS,
        CacheNamespace.REPORTS,
        CacheNamespace.ACCOUNTS,
    )


def _map_dues_value_error(exc: ValueError) -> HTTPException:
    """Map model-layer dues ValueErrors to HTTP status codes.

    Args:
        exc: ValueError raised by ``TransactionTemplatesService`` dues methods.

    Returns:
        HTTPException with 404, 409, or 422 as appropriate.
    """
    message = str(exc)
    if message == _TEMPLATE_NOT_FOUND:
        return _template_not_found()
    if message in _CONFLICT_MESSAGES:
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)


def _build_template_filter_dto(
    *,
    category_id: uuid.UUID | None,
    is_active: bool | None,
) -> TransactionTemplatesDTO | None:
    """Build a partial filter DTO from list query parameters."""
    filter_fields: dict[str, object] = {}
    if category_id is not None:
        filter_fields["category_id"] = category_id
    if is_active is not None:
        filter_fields["active"] = is_active
    if not filter_fields:
        return None
    return TransactionTemplatesDTO.model_construct(**filter_fields)


@router.get("", response_model=PaginatedResponse[TransactionTemplateResponse])
def list_transaction_templates(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    templates_service: Annotated[TransactionTemplatesService, Depends(get_transaction_templates_service)],
    category_id: Annotated[uuid.UUID | None, Query(description="Filter by category")] = None,
    is_active: Annotated[bool | None, Query(description="Filter by active status")] = None,
) -> PaginatedResponse[TransactionTemplateResponse]:
    """List tenant transaction templates with optional filters.

    Args:
        owner: Authenticated tenant from JWT.
        pagination: Skip/limit window for the response page.
        templates_service: Injected templates service.
        category_id: Optional category filter.
        is_active: Optional soft-active filter.

    Returns:
        Paginated ``TransactionTemplateResponse`` items owned by ``owner``.
    """
    filter_dto = _build_template_filter_dto(category_id=category_id, is_active=is_active)
    total = templates_service.count_records(dto=filter_dto, owner=owner, include_category=False)
    page_df = templates_service.get_records(
        dto=filter_dto,
        owner=owner,
        skip=pagination.skip,
        limit=pagination.limit,
        include_category=False,
    )
    items = [TransactionTemplateResponse.from_dto(row) for row in templates_from_dataframe(page_df)]
    return PaginatedResponse(
        items=items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get("/upcoming-dues", response_model=UpcomingDuesResponse)
def list_upcoming_dues(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    templates_service: Annotated[TransactionTemplatesService, Depends(get_transaction_templates_service)],
    filters: Annotated[UpcomingDuesQuery, Depends(get_upcoming_dues_query)],
) -> UpcomingDuesResponse:
    """List owner-scoped templates with a due in the upcoming reminder window.

    Args:
        owner: Authenticated tenant from JWT.
        templates_service: Injected templates service.
        filters: ``as_of`` / ``window_days`` / ``include_paid`` query bundle.

    Returns:
        Upcoming dues sorted by the model service (due date, then name/id).

    Raises:
        HTTPException: 422 when ``window_days`` is rejected by the service.
    """
    try:
        dues = templates_service.list_upcoming_dues(owner=owner, **filters.service_kwargs())
    except ValueError as exc:
        raise _map_dues_value_error(exc) from exc
    return UpcomingDuesResponse(
        items=[UpcomingDueResponse.from_dto(due) for due in dues],
        as_of=filters.as_of,
        window_days=filters.window_days,
    )


@router.get("/{template_id}", response_model=TransactionTemplateResponse)
def get_transaction_template(
    template_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    templates_service: Annotated[TransactionTemplatesService, Depends(get_transaction_templates_service)],
) -> TransactionTemplateResponse:
    """Retrieve a tenant-owned transaction template by id.

    Raises:
        HTTPException: 404 when missing or not owned by ``owner``.
    """
    template = templates_service.get(obj=template_id, owner=owner, include_category=False)
    if not isinstance(template, TransactionTemplatesDTO) or template.id is None:
        raise _template_not_found()
    return TransactionTemplateResponse.from_dto(template)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TransactionTemplateResponse)
def create_transaction_template(
    body: TransactionTemplateCreate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    templates_service: Annotated[TransactionTemplatesService, Depends(get_transaction_templates_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> TransactionTemplateResponse:
    """Create a tenant-owned transaction template."""
    created = templates_service.create(
        obj=body.to_templates_dto(owner_id=_require_owner_id(owner)),
        owner=owner,
        include_category=False,
    )
    if not isinstance(created, TransactionTemplatesDTO):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create transaction template",
        )
    _require_uuid(created.id)
    _invalidate_dues_caches(redis, owner)
    return TransactionTemplateResponse.from_dto(created)


@router.put("/{template_id}", response_model=TransactionTemplateResponse)
def update_transaction_template(
    template_id: uuid.UUID,
    body: TransactionTemplateUpdate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    templates_service: Annotated[TransactionTemplatesService, Depends(get_transaction_templates_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> TransactionTemplateResponse:
    """Update a tenant-owned transaction template.

    Raises:
        HTTPException: 404 when missing or not owned by ``owner``.
    """
    existing = templates_service.get(obj=template_id, owner=owner, include_category=False)
    if not isinstance(existing, TransactionTemplatesDTO) or existing.id is None:
        raise _template_not_found()
    updated = templates_service.create(
        obj=body.apply_to(existing),
        owner=owner,
        include_category=False,
    )
    if not isinstance(updated, TransactionTemplatesDTO):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update transaction template",
        )
    _invalidate_dues_caches(redis, owner)
    return TransactionTemplateResponse.from_dto(updated)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction_template(
    template_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    templates_service: Annotated[TransactionTemplatesService, Depends(get_transaction_templates_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> None:
    """Soft-delete a tenant-owned transaction template.

    Raises:
        HTTPException: 404 when missing or not owned by ``owner``.
    """
    existing = templates_service.get(obj=template_id, owner=owner, include_category=False)
    if not isinstance(existing, TransactionTemplatesDTO) or existing.id is None:
        raise _template_not_found()
    templates_service.delete(
        obj=TransactionTemplatesDTO.model_construct(id=template_id),
        owner=owner,
        hard=False,
    )
    _invalidate_dues_caches(redis, owner)


@router.post(
    "/{template_id}/mark-paid",
    status_code=status.HTTP_201_CREATED,
    response_model=TransactionResponse,
)
def mark_template_paid(
    template_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    templates_service: Annotated[TransactionTemplatesService, Depends(get_transaction_templates_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    body: MarkPaidRequest | None = None,
) -> TransactionResponse:
    """Post a linked EXPENSE/INCOME for the template due (mark paid).

    Raises:
        HTTPException: 404 / 409 / 422 from mapped service ValueErrors.
    """
    payload = body or MarkPaidRequest()
    try:
        posted = templates_service.mark_paid(
            template_id=template_id,
            owner=owner,
            as_of=payload.as_of,
            amount=payload.amount,
            transaction_ts=payload.transaction_ts,
        )
    except ValueError as exc:
        raise _map_dues_value_error(exc) from exc
    _invalidate_dues_caches(redis, owner)
    return TransactionResponse.from_dto(posted)


@router.post(
    "/{template_id}/clear-paid",
    response_model=TransactionResponse,
)
def clear_template_paid(
    template_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    templates_service: Annotated[TransactionTemplatesService, Depends(get_transaction_templates_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    body: ClearPaidRequest | None = None,
) -> TransactionResponse:
    """Soft-delete the linked posting for the template due period.

    Raises:
        HTTPException: 404 / 409 / 422 from mapped service ValueErrors.
    """
    payload = body or ClearPaidRequest()
    try:
        cleared = templates_service.clear_paid(
            template_id=template_id,
            owner=owner,
            as_of=payload.as_of,
        )
    except ValueError as exc:
        raise _map_dues_value_error(exc) from exc
    _invalidate_dues_caches(redis, owner)
    return TransactionResponse.from_dto(cleared)
