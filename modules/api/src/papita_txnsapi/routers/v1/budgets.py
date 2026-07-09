"""Deferred budget endpoints — return 501 in MVP (FR-09)."""

from __future__ import annotations

from fastapi import APIRouter, status

from papita_txnsapi.schemas.common import DeferredResponse

router = APIRouter(prefix="/budgets", tags=["Budgets (deferred)"])

_DEFERRED = DeferredResponse(deferred_reason="FR-09 budgets deferred to v4.1")


def _not_implemented() -> DeferredResponse:
    return _DEFERRED


@router.get("", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def list_budgets() -> DeferredResponse:
    """List budgets — deferred post-MVP."""
    return _not_implemented()


@router.get("/{budget_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def get_budget(budget_id: str) -> DeferredResponse:
    """Get budget — deferred post-MVP."""
    return _not_implemented()


@router.post("", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def create_budget() -> DeferredResponse:
    """Create budget — deferred post-MVP."""
    return _not_implemented()


@router.put("/{budget_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def update_budget(budget_id: str) -> DeferredResponse:
    """Update budget — deferred post-MVP."""
    return _not_implemented()


@router.delete("/{budget_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def delete_budget(budget_id: str) -> DeferredResponse:
    """Delete budget — deferred post-MVP."""
    return _not_implemented()


@router.get("/{budget_id}/summary", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def get_budget_summary(budget_id: str) -> DeferredResponse:
    """Budget summary — deferred post-MVP."""
    return _not_implemented()


@router.post("/{budget_id}/allocations", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def update_budget_allocations(budget_id: str) -> DeferredResponse:
    """Budget allocations — deferred post-MVP."""
    return _not_implemented()
