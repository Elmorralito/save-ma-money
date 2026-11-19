"""Unified transaction & transfer CRUD routes — PPT-037 / PPT-099.

Exposes tenant-scoped INCOME, EXPENSE, and TRANSFER management under ``/transactions``.
"""

from __future__ import annotations

import uuid
from datetime import timezone
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
from papita_txnsapi.core.client_contract import (
    ERROR_BULK_TOO_LARGE,
    ERROR_IDEMPOTENCY_BODY_MISMATCH,
    HEADER_ERROR_CODE,
)
from papita_txnsapi.core.idempotency import (
    begin_idempotency,
    clear_idempotency_pending,
    complete_idempotency,
    request_body_digest,
)
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.pagination import PaginationParams, get_pagination
from papita_txnsapi.dependencies.rate_limit import enforce_tenant_api_rate_limit
from papita_txnsapi.dependencies.redis import get_optional_redis
from papita_txnsapi.dependencies.services import get_accounts_service, get_transactions_service
from papita_txnsapi.schemas.common import PaginatedResponse
from papita_txnsapi.schemas.query_params import TransactionListQuery, get_transaction_list_query
from papita_txnsapi.schemas.transactions import (
    TransactionBulkCreate,
    TransactionBulkResponse,
    TransactionCreate,
    TransactionExecuteResponse,
    TransactionResponse,
    TransactionUpdate,
    _relation_uuid,
    transactions_from_dataframe,
)
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import TransactionKind, TransactionStatus
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.ingestion import IngestionBridgeService
from papita_txnsmodel.services.transactions import TransactionsService

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
    dependencies=[Depends(enforce_tenant_api_rate_limit)],
)

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
    """Build a 404 response for a missing or inaccessible transaction."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")


def _require_uuid(value: uuid.UUID | None) -> uuid.UUID:
    """Return a persisted UUID or raise when the DTO has no primary key."""
    if value is None:
        raise _transaction_not_found()
    return value


def _require_owner_id(owner: UsersDTO) -> uuid.UUID:
    """Return the authenticated owner's primary key."""
    if owner.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid owner context")
    return owner.id


def _idempotency_conflict() -> HTTPException:
    """Return 409 when an idempotency key is still pending on another request."""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="A request with this Idempotency-Key is already in progress.",
    )


def _idempotency_body_mismatch() -> HTTPException:
    """Return 422 when the same Idempotency-Key is reused with a different body."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Idempotency-Key was already used with a different request body.",
        headers={HEADER_ERROR_CODE: ERROR_IDEMPOTENCY_BODY_MISMATCH},
    )


def _validate_transfer_accounts(
    accounts_service: AccountsService,
    owner: UsersDTO,
    *,
    source_account_id: uuid.UUID,
    destination_account_id: uuid.UUID,
    currency: str,
) -> None:
    """Ensure both accounts exist for the tenant and share the requested currency."""
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


def _require_pending_transfer(transfer: TransactionsDTO) -> None:
    """Reject mutations on non-pending transfers."""
    if transfer.status != TransactionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only pending transfers can be modified.",
        )


@router.get("", response_model=PaginatedResponse[TransactionResponse])
def list_transactions(  # pylint: disable=too-many-positional-arguments,too-many-locals
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    filters: Annotated[TransactionListQuery, Depends(get_transaction_list_query)],
    settings: Annotated[Settings, Depends(get_settings)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    response: Response,
) -> PaginatedResponse[TransactionResponse]:
    """List tenant transactions and transfers with optional filters."""
    cache_params = {
        "skip": pagination.skip,
        "limit": pagination.limit,
        **filters.model_dump(mode="json"),
    }
    owner_id = owner.id
    if owner_id is not None:
        cached, cache_status, cache_version = get_versioned_cached_json(
            redis, owner_id, CacheNamespace.TRANSACTIONS, "transactions:list", cache_params
        )
        response.headers["X-Cache"] = cache_status
        if cached is not None:
            return PaginatedResponse[TransactionResponse].model_validate(cached)
    else:
        response.headers["X-Cache"] = "BYPASS"
        cache_version = 0

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
            version=cache_version,
        )
    return payload


@router.post("/bulk", status_code=status.HTTP_201_CREATED, response_model=TransactionBulkResponse)
def bulk_create_transactions(  # pylint: disable=too-many-positional-arguments,too-many-locals
    body: TransactionBulkCreate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> TransactionBulkResponse:
    """Create multiple transactions for the authenticated tenant."""
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
    request_digest = request_body_digest(body.model_dump(mode="json"))
    begun = begin_idempotency(
        redis,
        owner_id,
        scope=_IDEMPOTENCY_BULK,
        key=idempotency_key,
        ttl_seconds=settings.REDIS_IDEMPOTENCY_TTL_SECONDS,
        body_digest=request_digest,
    )
    if begun.state == "hit" and begun.payload is not None:
        return TransactionBulkResponse.model_validate(begun.payload)
    if begun.state == "mismatch":
        raise _idempotency_body_mismatch()
    if begun.state == "conflict":
        raise _idempotency_conflict()

    created_items: list[TransactionResponse] = []
    failed = 0

    account_ids = {
        acc_id
        for item in body.transactions
        for acc_id in (item.account_id, item.resolved_source_account_id(), item.resolved_destination_account_id())
        if acc_id is not None
    }
    category_ids = {item.category_id for item in body.transactions if item.category_id is not None}
    linked_dto_cache = transactions_service.prefetch_link_dtos(
        owner=owner,
        account_ids=list(account_ids),
        category_ids=list(category_ids),
    )

    try:
        for item in body.transactions:
            try:
                dto = item.to_transactions_dto(owner_id=owner_id)
                result = transactions_service.create(
                    obj=dto,
                    owner=owner,
                    refresh_balances=False,
                    linked_dto_cache=linked_dto_cache,
                )
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
        body_digest=request_digest,
    )
    return payload


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(  # pylint: disable=too-many-positional-arguments
    transaction_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    response: Response,
) -> TransactionResponse:
    """Retrieve a single tenant-owned transaction or transfer with linked names."""
    cache_params = {"transaction_id": str(transaction_id)}
    owner_id = owner.id
    if owner_id is not None:
        cached, cache_status, cache_version = get_versioned_cached_json(
            redis, owner_id, CacheNamespace.TRANSACTIONS, "transactions:detail", cache_params
        )
        response.headers["X-Cache"] = cache_status
        if cached is not None:
            return TransactionResponse.model_validate(cached)
    else:
        response.headers["X-Cache"] = "BYPASS"
        cache_version = 0

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
            version=cache_version,
        )
    return result


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TransactionResponse)
def create_transaction(  # pylint: disable=too-many-positional-arguments
    body: TransactionCreate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    accounts_service: Annotated[AccountsService, Depends(get_accounts_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> TransactionResponse:
    """Create an INCOME, EXPENSE, or TRANSFER transaction for the authenticated tenant."""
    owner_id = _require_owner_id(owner)
    request_digest = request_body_digest(body.model_dump(mode="json"))
    begun = begin_idempotency(
        redis,
        owner_id,
        scope=_IDEMPOTENCY_CREATE,
        key=idempotency_key,
        ttl_seconds=settings.REDIS_IDEMPOTENCY_TTL_SECONDS,
        body_digest=request_digest,
    )
    if begun.state == "hit" and begun.payload is not None:
        return TransactionResponse.model_validate(begun.payload)
    if begun.state == "mismatch":
        raise _idempotency_body_mismatch()
    if begun.state == "conflict":
        raise _idempotency_conflict()

    should_refresh_mv = True
    try:
        if body.transaction_type == "transfer":
            src = body.resolved_source_account_id()
            dst = body.resolved_destination_account_id()
            if src is None or dst is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Transfer requires both source and destination accounts.",
                )
            _validate_transfer_accounts(
                accounts_service,
                owner,
                source_account_id=src,
                destination_account_id=dst,
                currency=body.currency,
            )
            dto = body.to_transactions_dto(owner_id=owner_id)
            created = transactions_service.create_transfer(obj=dto, owner=owner, refresh_balances=False)
            is_pending = body.scheduled or (body.status and body.status.lower() == "pending")
            if is_pending:
                should_refresh_mv = False
            else:
                created = transactions_service.complete_transfer(
                    transaction_id=created, owner=owner, refresh_balances=False
                )
        elif body.source_ref and body.source_ref.strip():
            bridge = IngestionBridgeService(transactions_service=transactions_service)
            ingested = bridge.ingest_transaction(
                owner=owner,
                request=body.to_ingest_request(),
                refresh_balances=False,
            )
            created = ingested.transaction
        else:
            dto = body.to_transactions_dto(owner_id=owner_id)
            created = transactions_service.create(obj=dto, owner=owner, refresh_balances=False)
    except Exception:
        clear_idempotency_pending(redis, owner_id, scope=_IDEMPOTENCY_CREATE, key=idempotency_key)
        raise

    if should_refresh_mv:
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
        body_digest=request_digest,
    )
    return result


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(  # pylint: disable=too-many-positional-arguments
    transaction_id: uuid.UUID,
    body: TransactionUpdate,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    accounts_service: Annotated[AccountsService, Depends(get_accounts_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> TransactionResponse:
    """Update a tenant-owned transaction or pending transfer via upsert."""
    existing = transactions_service.get(obj=transaction_id, owner=owner, include_linked_dtos=False)
    if existing is None:
        raise _transaction_not_found()

    merged = body.apply_to(existing)
    if merged.transaction_kind == TransactionKind.TRANSFER:
        _require_pending_transfer(existing)
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
        _invalidate_ledger_caches(redis, owner)
        return TransactionResponse.from_dto(updated)

    updated = transactions_service.create(obj=merged, owner=owner, refresh_balances=False)
    transactions_service.refresh_balance_views()
    _invalidate_ledger_caches(redis, owner)
    return TransactionResponse.from_dto(updated)


@router.post("/{transaction_id}/execute", response_model=TransactionExecuteResponse)
def execute_transaction(
    transaction_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> TransactionExecuteResponse:
    """Complete a pending scheduled transfer."""
    existing = transactions_service.get(obj=transaction_id, owner=owner, include_linked_dtos=False)
    if existing is None or existing.transaction_kind != TransactionKind.TRANSFER:
        raise _transaction_not_found()
    _require_pending_transfer(existing)
    try:
        completed = transactions_service.complete_transfer(
            transaction_id=transaction_id, owner=owner, refresh_balances=False
        )
    except ValueError as exc:
        raise _transaction_not_found() from exc

    executed_at = completed.transaction_ts
    if executed_at.tzinfo is None:
        executed_at = executed_at.replace(tzinfo=timezone.utc)
    transactions_service.refresh_balance_views()
    _invalidate_ledger_caches(redis, owner)
    return TransactionExecuteResponse(
        id=_require_uuid(completed.id),
        status="completed",
        settlement_status="settled",
        executed_at=executed_at,
    )


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> None:
    """Soft-delete a tenant-owned transaction or cancel a pending transfer."""
    existing = transactions_service.get(obj=transaction_id, owner=owner, include_linked_dtos=False)
    if existing is None:
        raise _transaction_not_found()
    if existing.transaction_kind == TransactionKind.TRANSFER and existing.status == TransactionStatus.PENDING:
        try:
            transactions_service.cancel(transaction_id=transaction_id, owner=owner, refresh_balances=False)
        except ValueError as exc:
            raise _transaction_not_found() from exc
        _invalidate_ledger_caches(redis, owner)
        return

    transactions_service.delete(
        obj=TransactionsDTO.model_construct(id=transaction_id),
        owner=owner,
        refresh_balances=False,
    )
    transactions_service.refresh_balance_views()
    _invalidate_ledger_caches(redis, owner)
