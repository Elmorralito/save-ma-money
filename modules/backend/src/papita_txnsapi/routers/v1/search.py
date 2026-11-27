"""Unified holistic search HTTP route (/api/v1/search)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.rate_limit import enforce_tenant_api_rate_limit
from papita_txnsapi.dependencies.services import get_session_manager_dep
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.session import DatabaseSessionManager
from papita_txnsmodel.services.global_search import search_everything

router = APIRouter(
    prefix="/search",
    tags=["Search"],
    dependencies=[Depends(enforce_tenant_api_rate_limit)],
)


class GlobalSearchHitResponse(BaseModel):
    """One typed search hit; the client maps ``kind`` to a deep link or action."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    id: uuid.UUID
    title: str
    subtitle: str
    occurred_at: datetime | None = None
    status: str | None = None
    amount: float | None = None
    currency: str | None = None
    account_id: uuid.UUID | None = None
    flags: list[str] = Field(default_factory=list)


class GlobalSearchResponse(BaseModel):
    """Interleaved owner-scoped hits plus the kinds actually searched."""

    model_config = ConfigDict(extra="forbid")

    q: str
    kinds: list[str] = Field(default_factory=list)
    account_id: uuid.UUID | None = None
    limit: int
    items: list[GlobalSearchHitResponse] = Field(default_factory=list)


@router.get("", response_model=GlobalSearchResponse)
def search_domain(
    *,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    connector: Annotated[DatabaseSessionManager, Depends(get_session_manager_dep)],
    kinds: Annotated[list[str] | None, Query()] = None,
    account_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> GlobalSearchResponse:
    """Search accounts, transactions, payment dues, categories, and projections in one query.

    Supports kind selectors (``acc``, ``txn``, ``due``, ``cat``, ``proj``), structured
    filters (``date:>=2026-01-01``, ``amount:>=500000``, ``>100000``, ``currency:COP``,
    ``deleted:true``), and exact UUID matching. All results stay strictly within the
    authenticated owner's records.
    """
    with connector.session_scope() as session:
        result = search_everything(
            session,
            owner=owner,
            q=q,
            kinds=tuple(kinds or ()),
            account_id=account_id,
            limit=limit,
        )
    return GlobalSearchResponse(
        q=result.q,
        kinds=list(result.kinds),
        account_id=result.account_id,
        limit=result.limit,
        items=[
            GlobalSearchHitResponse(
                kind=hit.kind,
                id=hit.id,
                title=hit.title,
                subtitle=hit.subtitle,
                occurred_at=hit.occurred_at,
                status=hit.status,
                amount=hit.amount,
                currency=hit.currency,
                account_id=hit.account_id,
                flags=list(hit.flags),
            )
            for hit in result.items
        ],
    )
