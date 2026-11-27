"""Owner-scoped User Settings Console API router (/api/v1/settings)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.rate_limit import enforce_tenant_api_rate_limit
from papita_txnsapi.dependencies.services import get_users_service
from papita_txnsapi.schemas.settings import (
    UserPreferencesSchema,
    UserSettingsResponse,
    UserSettingsUpdateRequest,
)
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.users import UsersService

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
    dependencies=[Depends(enforce_tenant_api_rate_limit)],
)


@router.get("", response_model=UserSettingsResponse)
def get_user_settings(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
) -> UserSettingsResponse:
    """Return the authenticated owner's profile and domain preferences."""
    return UserSettingsResponse.from_dto(owner)


@router.patch("", response_model=UserSettingsResponse)
def update_user_settings(
    payload: UserSettingsUpdateRequest,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
) -> UserSettingsResponse:
    """Update the authenticated owner's profile fields and/or domain preferences."""
    fields_set = payload.model_fields_set
    try:
        updated = users_service.update_user_settings(
            owner=owner,
            display_name=payload.display_name,
            update_display_name="display_name" in fields_set,
            phone=payload.phone,
            update_phone="phone" in fields_set,
            preferences=payload.preferences.model_dump(mode="json") if payload.preferences is not None else None,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return UserSettingsResponse.from_dto(updated)


@router.post("/reset", response_model=UserSettingsResponse)
def reset_user_settings(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
) -> UserSettingsResponse:
    """Reset the authenticated owner's domain preferences back to secure defaults."""
    defaults = UserPreferencesSchema().model_dump(mode="json")
    updated = users_service.update_user_settings(owner=owner, preferences=defaults)
    return UserSettingsResponse.from_dto(updated)
