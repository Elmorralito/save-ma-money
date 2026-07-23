"""Deferred budget endpoints — return 501 in MVP (FR-09).

Placeholder router reserving the ``/budgets`` URL space for v4.1 budget features.
All handlers require JWT auth (parity with other protected routers) and respond with
HTTP 501 and a :class:`~papita_txnsapi.schemas.common.DeferredResponse` payload; no
model services are invoked yet.

Routes (all deferred):
    ``GET /budgets`` — list budgets.
    ``GET /budgets/{budget_id}`` — fetch one budget.
    ``POST /budgets`` — create budget.
    ``PUT /budgets/{budget_id}`` — update budget.
    ``DELETE /budgets/{budget_id}`` — delete budget.
    ``GET /budgets/{budget_id}/summary`` — budget summary rollup.
    ``POST /budgets/{budget_id}/allocations`` — update category allocations.

Service delegation:
    None in MVP. Future implementation will delegate to a budgets service in
    ``papita_txnsmodel`` with ``owner`` scoping consistent with accounts/categories.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.rate_limit import enforce_tenant_api_rate_limit
from papita_txnsapi.schemas.common import DeferredResponse

router = APIRouter(
    prefix="/budgets",
    tags=["Budgets (deferred)"],
    dependencies=[Depends(get_current_owner), Depends(enforce_tenant_api_rate_limit)],
)

_DEFERRED = DeferredResponse(deferred_reason="FR-09 budgets deferred to v4.1")


@router.get("", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def list_budgets() -> DeferredResponse:
    """List budgets — deferred post-MVP.

    Returns:
        DeferredResponse: Explains that budget listing is not available in MVP.
    """
    return _DEFERRED


@router.get("/{budget_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def get_budget(budget_id: str) -> DeferredResponse:
    """Get budget — deferred post-MVP.

    Args:
        budget_id: Path identifier reserved for future budget primary key.

    Returns:
        DeferredResponse: Explains that budget retrieval is not available in MVP.
    """
    _ = budget_id
    return _DEFERRED


@router.post("", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def create_budget() -> DeferredResponse:
    """Create budget — deferred post-MVP.

    Returns:
        DeferredResponse: Explains that budget creation is not available in MVP.
    """
    return _DEFERRED


@router.put("/{budget_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def update_budget(budget_id: str) -> DeferredResponse:
    """Update budget — deferred post-MVP.

    Args:
        budget_id: Path identifier reserved for future budget primary key.

    Returns:
        DeferredResponse: Explains that budget updates are not available in MVP.
    """
    _ = budget_id
    return _DEFERRED


@router.delete("/{budget_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def delete_budget(budget_id: str) -> DeferredResponse:
    """Delete budget — deferred post-MVP.

    Args:
        budget_id: Path identifier reserved for future budget primary key.

    Returns:
        DeferredResponse: Explains that budget deletion is not available in MVP.
    """
    _ = budget_id
    return _DEFERRED


@router.get("/{budget_id}/summary", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def get_budget_summary(budget_id: str) -> DeferredResponse:
    """Budget summary — deferred post-MVP.

    Args:
        budget_id: Path identifier reserved for future budget primary key.

    Returns:
        DeferredResponse: Explains that budget summaries are not available in MVP.
    """
    _ = budget_id
    return _DEFERRED


@router.post("/{budget_id}/allocations", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def update_budget_allocations(budget_id: str) -> DeferredResponse:
    """Budget allocations — deferred post-MVP.

    Args:
        budget_id: Path identifier reserved for future budget primary key.

    Returns:
        DeferredResponse: Explains that allocation updates are not available in MVP.
    """
    _ = budget_id
    return _DEFERRED
