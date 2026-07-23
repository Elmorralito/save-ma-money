"""Movement (TRANSFER alias) routes — PPT-037.

Exposes tenant-scoped transfer management under ``/movements``. All rows persist
in ``transactions`` with ``transaction_kind = TRANSFER`` via
:class:`~papita_txnsmodel.services.transactions.TransactionsService` transfer helpers.
The API uses movement field names (``source_account_id`` / ``destination_account_id``)
that map to ledger ``from_account_id`` / ``to_account_id`` in schemas.

Routes:
    ``GET /movements`` — paginated transfer list with optional filters.
    ``GET /movements/{movement_id}`` — single transfer with linked account names.
    ``POST /movements`` — create transfer; ``scheduled: true`` leaves status PENDING.
    ``PUT /movements/{movement_id}`` — update a PENDING transfer.
    ``DELETE /movements/{movement_id}`` — cancel a PENDING transfer.
    ``POST /movements/{movement_id}/execute`` — complete a PENDING transfer.

Tenant scoping:
    Every handler resolves ``get_current_owner`` and passes ``owner=`` to service
    methods so transfers are never visible or mutable across tenants.
"""

from __future__ import annotations

import uuid
from datetime import timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from redis import Redis

from papita_txnsapi.core.cache import CacheNamespace, bump_cache_versions
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.pagination import PaginationParams, get_pagination
from papita_txnsapi.dependencies.rate_limit import enforce_tenant_api_rate_limit
from papita_txnsapi.dependencies.redis import get_optional_redis
from papita_txnsapi.dependencies.services import get_accounts_service, get_transactions_service
from papita_txnsapi.schemas.common import PaginatedResponse
from papita_txnsapi.schemas.movements import (
    MovementCreate,
    MovementExecuteResponse,
    MovementResponse,
    MovementUpdate,
    movements_from_dataframe,
)
from papita_txnsapi.schemas.query_params import MovementListQuery, get_movement_list_query
from papita_txnsapi.schemas.transactions import _relation_uuid
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import TransactionKind, TransactionStatus
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.transactions import TransactionsService

router = APIRouter(
    prefix="/movements",
    tags=["Movements"],
    dependencies=[Depends(enforce_tenant_api_rate_limit)],
)


def _invalidate_ledger_caches(redis: Redis | None, owner: UsersDTO) -> None:
    """Bump transactions, reports, and accounts caches after transfer mutations."""
    bump_cache_versions(
        redis,
        owner.id,
        CacheNamespace.TRANSACTIONS,
        CacheNamespace.REPORTS,
        CacheNamespace.ACCOUNTS,
    )


def _movement_not_found() -> HTTPException:
    """Build a 404 response for a missing or inaccessible movement.

    Returns:
        HTTPException: 404 with a generic detail that avoids leaking cross-tenant
            existence of transfer rows.
    """
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movement not found")


def _require_owner_id(owner: UsersDTO) -> uuid.UUID:
    """Return the authenticated owner's primary key.

    Args:
        owner: Authenticated tenant DTO from JWT resolution.

    Returns:
        Non-null tenant UUID used when constructing transfer DTOs.

    Raises:
        HTTPException: 401 when ``owner.id`` is missing (invalid auth context).
    """
    if owner.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid owner context")
    return owner.id


def _require_transfer(
    transactions_service: TransactionsService,
    movement_id: uuid.UUID,
    owner: UsersDTO,
) -> TransactionsDTO:
    """Load a tenant-owned TRANSFER row or raise 404.

    Args:
        transactions_service: Injected ledger service for owner-scoped lookups.
        movement_id: Transfer primary key from the path.
        owner: Authenticated tenant that must own the transfer.

    Returns:
        TransactionsDTO: The TRANSFER row for the tenant.

    Raises:
        HTTPException: 404 when the row is missing, not owned, or not a TRANSFER.
    """
    transfer = transactions_service.get(obj=movement_id, owner=owner, include_linked_dtos=False)
    if transfer is None or transfer.transaction_kind != TransactionKind.TRANSFER:
        raise _movement_not_found()
    return transfer


def _validate_transfer_accounts(
    accounts_service: AccountsService,
    owner: UsersDTO,
    *,
    source_account_id: uuid.UUID,
    destination_account_id: uuid.UUID,
    currency: str,
) -> None:
    """Ensure both accounts exist for the tenant and share the requested currency.

    Args:
        accounts_service: Injected accounts service for ownership lookups.
        owner: Authenticated tenant that must own both accounts.
        source_account_id: Debit (from) account primary key.
        destination_account_id: Credit (to) account primary key.
        currency: ISO currency code that must match both accounts.

    Raises:
        HTTPException: 422 when accounts are identical or currencies mismatch;
            404 when either account is missing for the tenant.
    """
    if source_account_id == destination_account_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Source and destination accounts must differ.",
        )

    source = accounts_service.get(obj=source_account_id, owner=owner)
    destination = accounts_service.get(obj=destination_account_id, owner=owner)
    if source is None or destination is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    normalized_currency = currency.upper()
    if source.currency != destination.currency or source.currency != normalized_currency:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Currency must match both accounts.",
        )


def _require_pending(transfer: TransactionsDTO) -> None:
    """Reject mutations on non-pending transfers.

    Args:
        transfer: Loaded transfer DTO whose status must be PENDING.

    Raises:
        HTTPException: 422 when the transfer is already completed or cancelled.
    """
    if transfer.status != TransactionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only pending movements can be modified.",
        )


@router.get("", response_model=PaginatedResponse[MovementResponse])
def list_movements(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    filters: Annotated[MovementListQuery, Depends(get_movement_list_query)],
) -> PaginatedResponse[MovementResponse]:
    """List tenant transfer rows with optional source/destination and date filters.

    Args:
        owner: Authenticated tenant from JWT.
        pagination: Skip/limit window for the response page.
        transactions_service: Injected service providing ``list_transfers``.
        filters: Bundled query parameters mapped to service kwargs.

    Returns:
        Paginated ``MovementResponse`` items for TRANSFER rows owned by ``owner``.
    """
    records_df, total = transactions_service.list_transfers(
        owner=owner,
        skip=pagination.skip,
        limit=pagination.limit,
        **filters.service_kwargs(),
    )
    items = [MovementResponse.from_dto(txn) for txn in movements_from_dataframe(records_df)]
    return PaginatedResponse(
        items=items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get("/{movement_id}", response_model=MovementResponse)
def get_movement(
    movement_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
) -> MovementResponse:
    """Retrieve a single transfer with linked account names.

    Args:
        movement_id: Transfer primary key from the path.
        owner: Authenticated tenant from JWT.
        transactions_service: Injected service for owner-scoped get-by-id.

    Returns:
        MovementResponse including source/destination names when linked DTOs load.

    Raises:
        HTTPException: 404 when the transfer is missing, not owned, or not TRANSFER.
    """
    transfer = transactions_service.get(obj=movement_id, owner=owner, include_linked_dtos=True)
    if transfer is None or transfer.transaction_kind != TransactionKind.TRANSFER:
        raise _movement_not_found()
    return MovementResponse.from_dto(transfer, include_names=True)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=MovementResponse)
def create_movement(
    body: MovementCreate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    accounts_service: Annotated[AccountsService, Depends(get_accounts_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> MovementResponse:
    """Create a transfer between two tenant-owned accounts.

    ``create_transfer`` always persists PENDING. When ``scheduled`` is false, the
    handler immediately calls ``complete_transfer`` so the response reflects COMPLETED.

    Args:
        body: Transfer create payload (accounts, amount, currency, scheduled flag).
        owner: Authenticated tenant that will own the transfer.
        transactions_service: Injected service for create/complete helpers.
        accounts_service: Injected service used to validate account ownership.
        redis: Optional Redis client for cache invalidation.

    Returns:
        MovementResponse for the created (and possibly completed) transfer.

    Raises:
        HTTPException: 404/422 from account validation; 401 when owner id is missing.
    """
    _validate_transfer_accounts(
        accounts_service,
        owner,
        source_account_id=body.source_account_id,
        destination_account_id=body.destination_account_id,
        currency=body.currency,
    )
    dto = body.to_transactions_dto(owner_id=_require_owner_id(owner))
    # Intermediate create/complete skip per-call MV refresh; one refresh below.
    created = transactions_service.create_transfer(obj=dto, owner=owner, refresh_balances=False)
    if not body.scheduled:
        created = transactions_service.complete_transfer(transaction_id=created, owner=owner, refresh_balances=False)
    transactions_service.refresh_balance_views()
    _invalidate_ledger_caches(redis, owner)
    return MovementResponse.from_dto(created)


@router.put("/{movement_id}", response_model=MovementResponse)
def update_movement(  # pylint: disable=too-many-positional-arguments
    movement_id: uuid.UUID,
    body: MovementUpdate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    accounts_service: Annotated[AccountsService, Depends(get_accounts_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> MovementResponse:
    """Update a pending transfer via upsert of the merged DTO.

    Args:
        movement_id: Transfer primary key from the path.
        body: Partial update fields applied onto the existing PENDING transfer.
        owner: Authenticated tenant that must own the transfer.
        transactions_service: Injected service for load and upsert.
        accounts_service: Injected service used to re-validate account legs.
        redis: Optional Redis client for cache invalidation.

    Returns:
        MovementResponse for the updated transfer row.

    Raises:
        HTTPException: 404 when missing; 422 when not PENDING or legs/currency invalid.
    """
    existing = _require_transfer(transactions_service, movement_id, owner)
    _require_pending(existing)

    merged = body.apply_to(existing)
    source_id = _relation_uuid(merged.from_account_id)
    destination_id = _relation_uuid(merged.to_account_id)
    if source_id is None or destination_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid account legs.")

    _validate_transfer_accounts(
        accounts_service,
        owner,
        source_account_id=source_id,
        destination_account_id=destination_id,
        currency=merged.currency,
    )
    updated = transactions_service.create(obj=merged, owner=owner, refresh_balances=False)
    transactions_service.refresh_balance_views()
    _invalidate_ledger_caches(redis, owner)
    return MovementResponse.from_dto(updated)


@router.delete("/{movement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movement(
    movement_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> None:
    """Cancel a pending transfer by setting status to CANCELLED.

    Note:
        This is not a soft-delete of the row; cancelled transfers remain in the ledger.

    Args:
        movement_id: Transfer primary key from the path.
        owner: Authenticated tenant that must own the transfer.
        transactions_service: Injected service providing ``cancel``.
        redis: Optional Redis client for cache invalidation.

    Raises:
        HTTPException: 404 when missing or cancel fails; 422 when not PENDING.
    """
    existing = _require_transfer(transactions_service, movement_id, owner)
    _require_pending(existing)
    try:
        transactions_service.cancel(transaction_id=movement_id, owner=owner, refresh_balances=False)
    except ValueError as exc:
        raise _movement_not_found() from exc
    transactions_service.refresh_balance_views()
    _invalidate_ledger_caches(redis, owner)


@router.post("/{movement_id}/execute", response_model=MovementExecuteResponse)
def execute_movement(
    movement_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> MovementExecuteResponse:
    """Complete a pending scheduled transfer.

    Args:
        movement_id: Transfer primary key from the path.
        owner: Authenticated tenant that must own the transfer.
        transactions_service: Injected service providing ``complete_transfer``.
        redis: Optional Redis client for cache invalidation.

    Returns:
        MovementExecuteResponse with completed status and execution timestamp.

    Raises:
        HTTPException: 404 when missing or complete fails; 422 when not PENDING.
    """
    existing = _require_transfer(transactions_service, movement_id, owner)
    _require_pending(existing)
    try:
        completed = transactions_service.complete_transfer(
            transaction_id=movement_id, owner=owner, refresh_balances=False
        )
    except ValueError as exc:
        raise _movement_not_found() from exc

    executed_at = completed.transaction_ts
    if executed_at.tzinfo is None:
        executed_at = executed_at.replace(tzinfo=timezone.utc)
    transactions_service.refresh_balance_views()
    _invalidate_ledger_caches(redis, owner)
    return MovementExecuteResponse(
        id=_require_uuid(completed.id),
        status="completed",
        executed_at=executed_at,
    )


def _require_uuid(value: uuid.UUID | None) -> uuid.UUID:
    """Return a persisted UUID or raise when the DTO has no primary key.

    Args:
        value: Primary key that may be unset on an incomplete DTO.

    Returns:
        The non-``None`` UUID value.

    Raises:
        HTTPException: 404 when ``value`` is ``None``.
    """
    if value is None:
        raise _movement_not_found()
    return value
