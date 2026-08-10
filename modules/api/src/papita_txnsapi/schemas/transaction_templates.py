"""Transaction-template request/response schemas for PPT-073.

Maps REST payloads to ``TransactionTemplatesDTO`` / ``UpcomingDueDTO`` from
``papita_txnsmodel``. Routers own HTTP shape only; due resolution stays in the
model service layer.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator

from papita_txnsapi.config.settings import MAX_DESCRIPTION_LENGTH, MAX_TAG_LENGTH, MAX_TAGS_PER_TRANSACTION
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.transactions.dto import TransactionTemplatesDTO
from papita_txnsmodel.services.dues import UpcomingDueDTO


def _relation_uuid(value: uuid.UUID | Any | None) -> uuid.UUID | None:
    """Extract a UUID from a relation field that may be a DTO."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, (AccountsDTO, CategoriesDTO, TransactionTemplatesDTO)):
        return value.id
    return uuid.UUID(str(value))


def _bound_tags(value: list[str]) -> list[str]:
    """Reject tags that exceed the configured per-tag length."""
    for tag in value:
        if len(tag) > MAX_TAG_LENGTH:
            raise ValueError(f"each tag must be at most {MAX_TAG_LENGTH} characters")
    return value


class TransactionTemplateCreate(BaseModel):
    """Request body for ``POST /transaction-templates``."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=MAX_DESCRIPTION_LENGTH)
    tags: list[str] = Field(default_factory=list, max_length=MAX_TAGS_PER_TRANSACTION)
    category_id: uuid.UUID
    planned_amount: float = Field(gt=0)
    planned_day: int = Field(ge=1, le=31)
    use_month_end: bool = False
    due_date: date | None = None
    remind_days_before: int | None = Field(default=None, ge=0)
    from_account_id: uuid.UUID | None = None

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, value: list[str]) -> list[str]:
        return _bound_tags(value)

    def to_templates_dto(self, *, owner_id: uuid.UUID) -> TransactionTemplatesDTO:
        """Build a ``TransactionTemplatesDTO`` for service create/upsert.

        Args:
            owner_id: Tenant owner UUID from the authenticated session.
        """
        return TransactionTemplatesDTO(
            name=self.name.strip(),
            description=self.description,
            tags=list(self.tags),
            owner_id=owner_id,
            category_id=self.category_id,
            planned_amount=self.planned_amount,
            planned_day=self.planned_day,
            use_month_end=self.use_month_end,
            due_date=self.due_date,
            remind_days_before=self.remind_days_before,
            from_account_id=self.from_account_id,
        )


class TransactionTemplateUpdate(BaseModel):
    """Partial update body for ``PUT /transaction-templates/{template_id}``."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    tags: list[str] | None = Field(default=None, max_length=MAX_TAGS_PER_TRANSACTION)
    category_id: uuid.UUID | None = None
    planned_amount: float | None = Field(default=None, gt=0)
    planned_day: int | None = Field(default=None, ge=1, le=31)
    use_month_end: bool | None = None
    due_date: date | None = None
    remind_days_before: int | None = Field(default=None, ge=0)
    from_account_id: uuid.UUID | None = None
    is_active: bool | None = None

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _bound_tags(value)

    def apply_to(self, existing: TransactionTemplatesDTO) -> TransactionTemplatesDTO:
        """Merge partial update fields onto an existing template DTO.

        Args:
            existing: Current template row from the repository.

        Returns:
            New ``TransactionTemplatesDTO`` with only supplied fields overwritten;
            ``is_active`` maps to DTO ``active``.
        """
        updates = self.model_dump(exclude_unset=True, exclude={"is_active"})
        if self.name is not None:
            updates["name"] = self.name.strip()
        if self.is_active is not None:
            updates["active"] = self.is_active
        return existing.model_copy(update=updates)


class TransactionTemplateResponse(BaseModel):
    """Transaction-template resource returned by CRUD endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    category_id: uuid.UUID
    planned_amount: float
    planned_day: int
    use_month_end: bool
    due_date: date | None = None
    remind_days_before: int | None = None
    from_account_id: uuid.UUID | None = None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_dto(cls, template: TransactionTemplatesDTO) -> TransactionTemplateResponse:
        """Build an API response from a ``TransactionTemplatesDTO``.

        Args:
            template: Template row from the model service.

        Returns:
            Serialized template with UUID relations flattened.
        """
        category_id = _relation_uuid(template.category_id)
        if category_id is None:
            raise ValueError("Template category_id is required.")
        template_id = template.id
        if template_id is None:
            raise ValueError("Template id is required.")
        return cls(
            id=template_id,
            name=template.name,
            description=template.description or "",
            tags=list(template.tags or []) if not isinstance(template.tags, str) else [template.tags],
            category_id=category_id,
            planned_amount=float(template.planned_amount),
            planned_day=int(template.planned_day),
            use_month_end=bool(template.use_month_end),
            due_date=template.due_date,
            remind_days_before=template.remind_days_before,
            from_account_id=_relation_uuid(template.from_account_id),
            is_active=bool(template.active),
            created_at=template.created_at,
            updated_at=template.updated_at,
        )


class UpcomingDueResponse(BaseModel):
    """Single upcoming-due row for in-app reminders."""

    model_config = ConfigDict(from_attributes=True)

    template: TransactionTemplateResponse
    due_date: date
    remind_start: date
    is_paid: bool = False
    paid_transaction_id: uuid.UUID | None = None

    @classmethod
    def from_dto(cls, due: UpcomingDueDTO) -> UpcomingDueResponse:
        """Build an API response from an ``UpcomingDueDTO``."""
        return cls(
            template=TransactionTemplateResponse.from_dto(due.template),
            due_date=due.due_date,
            remind_start=due.remind_start,
            is_paid=bool(due.is_paid),
            paid_transaction_id=due.paid_transaction_id,
        )


class UpcomingDuesResponse(BaseModel):
    """List payload for ``GET /transaction-templates/upcoming-dues``."""

    items: list[UpcomingDueResponse] = Field(default_factory=list)
    as_of: date
    window_days: int


class MarkPaidRequest(BaseModel):
    """Optional body for ``POST …/mark-paid``."""

    model_config = ConfigDict(extra="forbid")

    as_of: date | None = None
    amount: float | None = Field(default=None, gt=0)
    transaction_ts: datetime | None = None


class ClearPaidRequest(BaseModel):
    """Optional body for ``POST …/clear-paid``."""

    model_config = ConfigDict(extra="forbid")

    as_of: date | None = None


def templates_from_dataframe(df: pd.DataFrame) -> list[TransactionTemplatesDTO]:
    """Convert a templates query DataFrame to DTO instances.

    Args:
        df: DataFrame from ``TransactionTemplatesRepository`` / service reads.

    Returns:
        List of ``TransactionTemplatesDTO``; empty when the frame is empty.
    """
    if getattr(df, "empty", True):
        return []
    dao_type = TransactionTemplatesDTO.__dao_type__
    templates: list[TransactionTemplatesDTO] = []
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        if "TransactionTemplates" in row_dict and isinstance(row_dict["TransactionTemplates"], dao_type):
            templates.append(TransactionTemplatesDTO.from_dao(row_dict["TransactionTemplates"]))
            continue
        if len(row_dict) == 1:
            only_value = next(iter(row_dict.values()))
            if isinstance(only_value, dao_type):
                templates.append(TransactionTemplatesDTO.from_dao(only_value))
                continue
        templates.append(TransactionTemplatesDTO.model_validate(row_dict))
    return templates
