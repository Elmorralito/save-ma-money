"""Public client-contract discovery endpoints (PPT-044).

Unauthenticated probes so SDKs and migration scripts can learn effective limits
and temporary compat flags without opening OpenAPI in production.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.client_contract import build_client_contract

router = APIRouter(prefix="/meta", tags=["Meta"])


@router.get("/client-contract")
def get_client_contract(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, Any]:
    """Return the effective PPT-044 client contract and migration checklist.

    Args:
        settings: Application settings (bulk/window limits and compat flags).

    Returns:
        JSON snapshot of secure defaults, effective values, compat flags, and
        stable ``X-Papita-Error-Code`` values clients should handle.
    """
    return build_client_contract(settings)
