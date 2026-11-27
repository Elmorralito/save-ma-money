"""Pydantic schemas for the owner-scoped User Settings Console (/api/v1/settings)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from papita_txnsmodel.access.users.dto import UsersDTO

SupportedCurrency = Literal["COP", "USD", "EUR", "GBP", "MXN", "CLP", "PEN", "BRL"]
SupportedLocale = Literal["es-CO", "en-US", "es-ES", "en-GB"]
SupportedDateFormat = Literal["YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY"]
SupportedPageSize = Literal[10, 25, 50, 100]


class UserPreferencesSchema(BaseModel):
    """Structured per-user domain preferences stored in ``users.preferences``."""

    model_config = ConfigDict(extra="forbid")

    # Currency, locale & display
    base_currency: SupportedCurrency = "COP"
    locale: SupportedLocale = "es-CO"
    timezone: str = Field(default="America/Bogota", min_length=2, max_length=64)
    date_format: SupportedDateFormat = "YYYY-MM-DD"
    default_page_size: SupportedPageSize = 25
    hide_balances_by_default: bool = False

    # Ledger & reconciliation defaults
    default_account_id: uuid.UUID | None = None
    default_income_category_id: uuid.UUID | None = None
    default_expense_category_id: uuid.UUID | None = None
    credit_card_cashflow_only: bool = True
    auto_refresh_balances: bool = True
    fiscal_month_start_day: int = Field(default=1, ge=1, le=28)

    # Alerts & financial health thresholds
    payment_due_reminder_days: int = Field(default=5, ge=1, le=30)
    low_runway_months_threshold: int = Field(default=3, ge=1, le=24)
    high_utilization_pct_threshold: int = Field(default=30, ge=10, le=100)
    large_transaction_alert_amount: float | None = Field(default=None, gt=0)

    # Privacy & security controls
    redact_card_numbers: bool = True
    require_dkim_spf_for_email_ingestion: bool = True
    session_idle_timeout_minutes: int = Field(default=120, ge=15, le=1440)

    # Per-account financial projection & amortization overrides (managed via /projections)
    projection_configs: dict[str, Any] = Field(default_factory=dict)
    # Owner-scoped AI/LLM provider & CLI/API configuration (secrets stripped on read)
    ai_config: dict[str, Any] = Field(default_factory=dict)


class UserSettingsResponse(BaseModel):
    """Complete read model for the User Settings Console (never exposes password/tokens)."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    username: str
    email: str
    display_name: str | None = None
    phone: str | None = None
    auth_provider: str
    provider_type: str
    preferences: UserPreferencesSchema
    updated_at: datetime | None = None

    @classmethod
    def from_dto(cls, user: UsersDTO) -> UserSettingsResponse:
        if user.id is None:
            raise ValueError("User id is required.")
        raw_prefs = dict(getattr(user, "preferences", None) or {})
        if isinstance(raw_prefs.get("ai_config"), dict):
            raw_prefs["ai_config"] = {
                k: v for k, v in raw_prefs["ai_config"].items() if k not in ("api_key", "api_key_enc")
            }
        prefs = UserPreferencesSchema.model_validate(raw_prefs)
        provider_type = user.provider_type.value if hasattr(user.provider_type, "value") else str(user.provider_type)
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            phone=user.phone,
            auth_provider=user.auth_provider,
            provider_type=provider_type,
            preferences=prefs,
            updated_at=user.updated_at,
        )


class UserSettingsUpdateRequest(BaseModel):
    """Partial update payload for ``PATCH /api/v1/settings``."""

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    preferences: UserPreferencesSchema | None = None


__all__ = [
    "UserPreferencesSchema",
    "UserSettingsResponse",
    "UserSettingsUpdateRequest",
]
