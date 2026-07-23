"""Transaction CRUD routes — PPT-037.

Exposes tenant-scoped INCOME/EXPENSE transaction management under ``/transactions``.
All handlers require JWT auth via ``get_current_owner`` and delegate persistence to
:class:`~papita_txnsmodel.services.transactions.TransactionsService`. TRANSFER rows
are excluded from default list responses; use ``/movements`` or
``?transaction_type=transfer`` to include them.

Routes:
    ``GET /transactions`` — paginated list with G4 filters; excludes TRANSFER by default.
    ``GET /transactions/{transaction_id}`` — single transaction with linked names.
    ``POST /transactions`` — create INCOME/EXPENSE row (optional ``Idempotency-Key``).
    ``POST /transactions/bulk`` — bulk create INCOME/EXPENSE rows (optional ``Idempotency-Key``).
    ``PUT /transactions/{transaction_id}`` — update tenant-owned transaction.
    ``DELETE /transactions/{transaction_id}`` — soft-delete tenant-owned transaction.
    ``POST /transactions/{transaction_id}/split`` — deferred 501 (v4).

Tenant scoping:
    Every mutating and read path passes ``owner=`` so ledger rows never leak across
    tenants. Cross-tenant ids resolve as not found (404).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from redis import Redis

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.cache import (
    CacheNamespace,
    bump_cache_versions,
    get_versioned_cached_json,
    set_versioned_cached_json,
    ttl_for_namespace,
)
from papita_txnsapi.core.client_contract import ERROR_BULK_TOO_LARGE, HEADER_ERROR_CODE
from papita_txnsapi.core.idempotency import begin_idempotency, clear_idempotency_pending, complete_idempotency
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.pagination import PaginationParams, get_pagination
from papita_txnsapi.dependencies.rate_limit import enforce_tenant_api_rate_limit
from papita_txnsapi.dependencies.redis import get_optional_redis
from papita_txnsapi.dependencies.services import get_transactions_service
from papita_txnsapi.schemas.common import DeferredResponse, PaginatedResponse
from papita_txnsapi.schemas.query_params import TransactionListQuery, get_transaction_list_query
from papita_txnsapi.schemas.transactions import (
    TransactionBulkCreate,
    TransactionBulkResponse,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
    transactions_from_dataframe,
)
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import TransactionKind
from papita_txnsmodel.services.transactions import TransactionsService

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
    dependencies=[Depends(enforce_tenant_api_rate_limit)],
)

_DEFERRED_SPLIT = DeferredResponse(deferred_reason="Transaction split deferred to v4 transaction_splits")
_IDEMPOTENCY_CREATE = "transactions:create"
_IDEMPOTENCY_BULK = "transactions:bulk"


def _invalidate_ledger_caches(redis: Redis | None, owner: UsersDTO) -> None:
    """Bump transactions, reports, and accounts caches after ledger mutations."""
    bump_cache_versions(
        redis,
        owner.id,
        CacheNamespace.TRANSACTIONS,
        CacheNamespace.REPORTS,
        CacheNamespace.ACCOUNTS,
    )


def _transaction_not_found() -> HTTPException:
    """Build a 404 response for a missing or inaccessible transaction.

    Returns:
        HTTPException: 404 with a generic detail that avoids leaking cross-tenant
            existence of ledger rows.
    """
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")


def _require_uuid(value: uuid.UUID | None) -> uuid.UUID:
    """Return a persisted UUID or raise when the DTO has no primary key.

    Args:
        value: Primary key from a DTO that may not yet be persisted.

    Returns:
        The non-``None`` UUID value.

    Raises:
        HTTPException: 404 when ``value`` is ``None``.
    """
    if value is None:
        raise _transaction_not_found()
    return value


def _require_owner_id(owner: UsersDTO) -> uuid.UUID:
    """Return the authenticated owner's primary key.

    Args:
        owner: Authenticated tenant DTO from JWT resolution.

    Returns:
        Non-null tenant UUID used when constructing create DTOs.

    Raises:
        HTTPException: 401 when ``owner.id`` is missing (invalid auth context).
    """
    if owner.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid owner context")
    return owner.id


def _idempotency_conflict() -> HTTPException:
    """Return 409 when an idempotency key is still pending on another request."""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="A request with this Idempotency-Key is already in progress.",
    )


@router.get("", response_model=PaginatedResponse[TransactionResponse])
def list_transactions(  # pylint: disable=too-many-positional-arguments
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    filters: Annotated[TransactionListQuery, Depends(get_transaction_list_query)],
    settings: Annotated[Settings, Depends(get_settings)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    response: Response,
) -> PaginatedResponse[TransactionResponse]:
    """List tenant transactions with optional G4 filters.

    By default TRANSFER rows are excluded (``exclude_transfer=True``) unless the
    client filters ``transaction_type=transfer``. Short-TTL Redis cache-aside when enabled.

    Args:
        owner: Authenticated tenant from JWT.
        pagination: Skip/limit window for the response page.
        transactions_service: Injected service providing ``list_transactions``.
        filters: Bundled query parameters mapped to service kwargs.
        settings: Application settings (cache TTL).
        redis: Optional Redis client when ``REDIS_ENABLED``.
        response: FastAPI response used to set ``X-Cache`` status.

    Returns:
        Paginated ``TransactionResponse`` items owned by ``owner``.
    """
    cache_params = {
        "skip": pagination.skip,
        "limit": pagination.limit,
        **filters.model_dump(mode="json"),
    }
    owner_id = owner.id
    if owner_id is not None:
        cached, cache_status = get_versioned_cached_json(
            redis, owner_id, CacheNamespace.TRANSACTIONS, "transactions:list", cache_params
        )
        response.headers["X-Cache"] = cache_status
        if cached is not None:
            return PaginatedResponse[TransactionResponse].model_validate(cached)
    else:
        response.headers["X-Cache"] = "BYPASS"

    records_df, total = transactions_service.list_transactions(
        owner=owner,
        skip=pagination.skip,
        limit=pagination.limit,
        **filters.service_kwargs(),
    )
    items = [TransactionResponse.from_dto(txn) for txn in transactions_from_dataframe(records_df)]
    payload: PaginatedResponse[TransactionResponse] = PaginatedResponse(
        items=items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    if owner_id is not None:
        set_versioned_cached_json(
            redis,
            owner_id,
            CacheNamespace.TRANSACTIONS,
            "transactions:list",
            cache_params,
            value=payload.model_dump(mode="json"),
            ttl_seconds=ttl_for_namespace(settings, CacheNamespace.TRANSACTIONS),
        )
    return payload


@router.post("/bulk", status_code=status.HTTP_201_CREATED, response_model=TransactionBulkResponse)
def bulk_create_transactions(  # pylint: disable=too-many-positional-arguments
    body: TransactionBulkCreate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> TransactionBulkResponse:
    """Create multiple INCOME/EXPENSE transactions for the authenticated tenant.

    Each item is created independently; ``ValueError`` / ``TypeError`` on an item
    increments ``failed`` without aborting the remainder of the batch. Optional
    ``Idempotency-Key`` replays a prior bulk response when Redis is enabled.

    Args:
        body: Bulk payload containing one or more ``TransactionCreate`` items.
        owner: Authenticated tenant that will own every created row.
        transactions_service: Injected service used for per-item ``create``.
        settings: Application settings (idempotency TTL).
        redis: Optional Redis client for cache invalidation / idempotency.
        idempotency_key: Optional client key for safe retries.

    Returns:
        TransactionBulkResponse with counts and successfully created items.

    Raises:
        HTTPException: 401 when the owner context lacks a primary key; 409 when
            an idempotency key is still pending; 422 when the batch exceeds
            ``API_BULK_MAX_TRANSACTIONS``.
    """
    if len(body.transactions) > settings.API_BULK_MAX_TRANSACTIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Bulk create accepts at most {settings.API_BULK_MAX_TRANSACTIONS} "
                "transactions per request; chunk larger batches."
            ),
            headers={HEADER_ERROR_CODE: ERROR_BULK_TOO_LARGE},
        )

    owner_id = _require_owner_id(owner)
    begun = begin_idempotency(
        redis,
        owner_id,
        scope=_IDEMPOTENCY_BULK,
        key=idempotency_key,
        ttl_seconds=settings.REDIS_IDEMPOTENCY_TTL_SECONDS,
    )
    if begun.state == "hit" and begun.payload is not None:
        return TransactionBulkResponse.model_validate(begun.payload)
    if begun.state == "conflict":
        raise _idempotency_conflict()

    created_items: list[TransactionResponse] = []
    failed = 0

    try:
        for item in body.transactions:
            try:
                dto = item.to_transactions_dto(owner_id=owner_id)
                # Defer MV refresh to once after the batch (avoid N× refresh).
                result = transactions_service.create(obj=dto, owner=owner, refresh_balances=False)
                created_items.append(TransactionResponse.from_dto(result))
            except (ValueError, TypeError):
                failed += 1
    except Exception:
        clear_idempotency_pending(redis, owner_id, scope=_IDEMPOTENCY_BULK, key=idempotency_key)
        raise

    if created_items:
        transactions_service.refresh_balance_views()
        _invalidate_ledger_caches(redis, owner)
    payload = TransactionBulkResponse(created=len(created_items), failed=failed, transactions=created_items)
    complete_idempotency(
        redis,
        owner_id,
        scope=_IDEMPOTENCY_BULK,
        key=idempotency_key,
        body=payload.model_dump(mode="json"),
        ttl_seconds=settings.REDIS_IDEMPOTENCY_TTL_SECONDS,
        http_status=201,
    )
    return payload


@router.post("/{transaction_id}/split", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def split_transaction(transaction_id: uuid.UUID) -> DeferredResponse:
    """Defer transaction split until v4 ``transaction_splits`` (MVP stub).

    Args:
        transaction_id: Path identifier reserved for a future split target row.

    Returns:
        DeferredResponse explaining that split is not implemented in MVP.
    """
    del transaction_id
    return _DEFERRED_SPLIT


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(  # pylint: disable=too-many-positional-arguments
    transaction_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    response: Response,
) -> TransactionResponse:
    """Retrieve a single tenant-owned transaction with linked names.

    Args:
        transaction_id: Ledger primary key from the path.
        owner: Authenticated tenant from JWT.
        transactions_service: Injected service for owner-scoped get-by-id.
        settings: Application settings (cache TTL).
        redis: Optional Redis client when ``REDIS_ENABLED``.
        response: FastAPI response used to set ``X-Cache`` status.

    Returns:
        TransactionResponse including account/category names when linked DTOs load.

    Raises:
        HTTPException: 404 when the row is missing or not owned by ``owner``.
    """
    cache_params = {"transaction_id": str(transaction_id)}
    owner_id = owner.id
    if owner_id is not None:
        cached, cache_status = get_versioned_cached_json(
            redis, owner_id, CacheNamespace.TRANSACTIONS, "transactions:detail", cache_params
        )
        response.headers["X-Cache"] = cache_status
        if cached is not None:
            return TransactionResponse.model_validate(cached)
    else:
        response.headers["X-Cache"] = "BYPASS"

    transaction = transactions_service.get(obj=transaction_id, owner=owner, include_linked_dtos=True)
    if transaction is None:
        raise _transaction_not_found()
    result = TransactionResponse.from_dto(transaction, include_names=True)
    if owner_id is not None:
        set_versioned_cached_json(
            redis,
            owner_id,
            CacheNamespace.TRANSACTIONS,
            "transactions:detail",
            cache_params,
            value=result.model_dump(mode="json"),
            ttl_seconds=ttl_for_namespace(settings, CacheNamespace.TRANSACTIONS),
        )
    return result


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TransactionResponse)
def create_transaction(  # pylint: disable=too-many-positional-arguments
    body: TransactionCreate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> TransactionResponse:
    """Create an INCOME or EXPENSE transaction for the authenticated tenant.

    Optional ``Idempotency-Key`` header (when Redis is enabled) makes retries safe:
    a repeated key returns the original create response without inserting again.

    Args:
        body: Create payload (account, category, type, amount, date, optional fields).
        owner: Authenticated tenant that will own the new row.
        transactions_service: Injected service providing ``create``.
        settings: Application settings (idempotency TTL).
        redis: Optional Redis client for cache invalidation / idempotency.
        idempotency_key: Optional client key for safe retries.

    Returns:
        TransactionResponse for the persisted row.

    Raises:
        HTTPException: 401 when owner id is missing; 409 when idempotency key is
            pending; domain errors may surface as 400 via the global handler.
    """
    owner_id = _require_owner_id(owner)
    begun = begin_idempotency(
        redis,
        owner_id,
        scope=_IDEMPOTENCY_CREATE,
        key=idempotency_key,
        ttl_seconds=settings.REDIS_IDEMPOTENCY_TTL_SECONDS,
    )
    if begun.state == "hit" and begun.payload is not None:
        return TransactionResponse.model_validate(begun.payload)
    if begun.state == "conflict":
        raise _idempotency_conflict()

    try:
        dto = body.to_transactions_dto(owner_id=owner_id)
        created = transactions_service.create(obj=dto, owner=owner, refresh_balances=False)
    except Exception:
        clear_idempotency_pending(redis, owner_id, scope=_IDEMPOTENCY_CREATE, key=idempotency_key)
        raise

    transactions_service.refresh_balance_views()
    _invalidate_ledger_caches(redis, owner)
    result = TransactionResponse.from_dto(created)
    complete_idempotency(
        redis,
        owner_id,
        scope=_IDEMPOTENCY_CREATE,
        key=idempotency_key,
        body=result.model_dump(mode="json"),
        ttl_seconds=settings.REDIS_IDEMPOTENCY_TTL_SECONDS,
        http_status=201,
    )
    return result


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: uuid.UUID,
    body: TransactionUpdate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> TransactionResponse:
    """Update a tenant-owned INCOME/EXPENSE transaction via upsert.

    TRANSFER rows must be updated through ``PUT /movements`` instead.

    Args:
        transaction_id: Ledger primary key from the path.
        body: Partial update fields applied onto the existing DTO.
        owner: Authenticated tenant that must own the row.
        transactions_service: Injected service for get and upsert.
        redis: Optional Redis client for cache invalidation.

    Returns:
        TransactionResponse for the updated row.

    Raises:
        HTTPException: 404 when missing; 422 when the row is a TRANSFER.
    """
    existing = transactions_service.get(obj=transaction_id, owner=owner, include_linked_dtos=False)
    if existing is None:
        raise _transaction_not_found()
    if existing.transaction_kind == TransactionKind.TRANSFER:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Use PUT /movements to update transfer transactions.",
        )

    merged = body.apply_to(existing)
    updated = transactions_service.create(obj=merged, owner=owner, refresh_balances=False)
    transactions_service.refresh_balance_views()
    _invalidate_ledger_caches(redis, owner)
    return TransactionResponse.from_dto(updated)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> None:
    """Soft-delete a tenant-owned transaction.

    Args:
        transaction_id: Ledger primary key from the path.
        owner: Authenticated tenant that must own the row.
        transactions_service: Injected service providing soft ``delete``.
        redis: Optional Redis client for cache invalidation.

    Raises:
        HTTPException: 404 when the row is missing or not owned by ``owner``.
    """
    existing = transactions_service.get(obj=transaction_id, owner=owner, include_linked_dtos=False)
    if existing is None:
        raise _transaction_not_found()
    transactions_service.delete(
        obj=TransactionsDTO.model_construct(id=transaction_id),
        owner=owner,
        refresh_balances=False,
    )
    transactions_service.refresh_balance_views()
    _invalidate_ledger_caches(redis, owner)
