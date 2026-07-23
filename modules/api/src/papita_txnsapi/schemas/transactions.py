"""Transaction request/response schemas for PPT-037 transactions CRUD.

Maps REST transaction payloads to ``TransactionsDTO`` from ``papita_txnsmodel``.
INCOME/EXPENSE rows use API ``account_id`` mapped to ``to_account_id`` /
``from_account_id`` per the v3 ledger contract.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator

from papita_txnsapi.config.settings import (
    MAX_BULK_TRANSACTIONS_HARD_CAP,
    MAX_DESCRIPTION_LENGTH,
    MAX_TAG_LENGTH,
    MAX_TAGS_PER_TRANSACTION,
)
from papita_txnsapi.schemas.accounts import paginate_dataframe
from papita_txnsapi.schemas.converters import enum_to_api_slug, parse_transaction_kind, parse_transaction_status
from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.model.enums import TransactionKind, TransactionStatus


def _relation_uuid(value: uuid.UUID | Any | None) -> uuid.UUID | None:
    """Extract a UUID from a relation field that may be a DTO."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, (AccountsDTO, CategoriesDTO)):
        return value.id
    return uuid.UUID(str(value))


def derive_account_id(transaction: TransactionsDTO) -> uuid.UUID | None:
    """Map v3 account legs to the API ``account_id`` field.

    Args:
        transaction: Posted transaction DTO.

    Returns:
        Primary account UUID for INCOME/EXPENSE rows, or ``None`` for TRANSFER.
    """
    if transaction.transaction_kind == TransactionKind.INCOME:
        return _relation_uuid(transaction.to_account_id)
    if transaction.transaction_kind == TransactionKind.EXPENSE:
        return _relation_uuid(transaction.from_account_id)
    return None


def _parse_transaction_date(value: date | datetime | str) -> datetime:
    """Normalize API date or datetime to a timezone-aware ``transaction_ts``."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


class TransactionCreate(BaseModel):
    """Request body for ``POST /transactions`` (INCOME/EXPENSE only)."""

    model_config = ConfigDict(extra="forbid")

    account_id: uuid.UUID
    category_id: uuid.UUID
    transaction_type: Literal["income", "expense"]
    amount: float = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    description: str = Field(default="", max_length=MAX_DESCRIPTION_LENGTH)
    transaction_date: date | datetime
    reference_number: str | None = Field(default=None, max_length=128)
    tags: list[str] = Field(default_factory=list, max_length=MAX_TAGS_PER_TRANSACTION)
    status: str | None = None

    @field_validator("tags")
    @classmethod
    def _bound_tags(cls, value: list[str]) -> list[str]:
        for tag in value:
            if len(tag) > MAX_TAG_LENGTH:
                raise ValueError(f"each tag must be at most {MAX_TAG_LENGTH} characters")
        return value

    def to_transactions_dto(self, *, owner_id: uuid.UUID) -> TransactionsDTO:
        """Build a ``TransactionsDTO`` for ``TransactionsService.create``."""
        kind = parse_transaction_kind(self.transaction_type)
        status = TransactionStatus.COMPLETED
        if self.status is not None:
            status = parse_transaction_status(self.status)

        dto_fields: dict[str, object] = {
            "owner_id": owner_id,
            "transaction_kind": kind,
            "amount": self.amount,
            "currency": self.currency.upper(),
            "transaction_ts": _parse_transaction_date(self.transaction_date),
            "category_id": self.category_id,
            "description": self.description,
            "reference_number": self.reference_number,
            "tags": self.tags,
            "status": status,
        }
        if kind == TransactionKind.INCOME:
            dto_fields["to_account_id"] = self.account_id
        else:
            dto_fields["from_account_id"] = self.account_id
        return TransactionsDTO(**dto_fields)


class TransactionUpdate(BaseModel):
    """Request body for ``PUT /transactions/{transaction_id}``."""

    model_config = ConfigDict(extra="forbid")

    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    transaction_type: str | None = None
    amount: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    transaction_date: date | datetime | None = None
    reference_number: str | None = Field(default=None, max_length=128)
    tags: list[str] | None = Field(default=None, max_length=MAX_TAGS_PER_TRANSACTION)
    status: str | None = None

    @field_validator("tags")
    @classmethod
    def _bound_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        for tag in value:
            if len(tag) > MAX_TAG_LENGTH:
                raise ValueError(f"each tag must be at most {MAX_TAG_LENGTH} characters")
        return value

    def apply_to(self, existing: TransactionsDTO) -> TransactionsDTO:
        """Merge partial update fields onto an existing transaction DTO."""
        updates = self.model_dump(
            exclude_unset=True,
            exclude={"transaction_type", "transaction_date", "status", "account_id"},
        )
        if self.currency is not None:
            updates["currency"] = self.currency.upper()
        if self.transaction_date is not None:
            updates["transaction_ts"] = _parse_transaction_date(self.transaction_date)
        if self.status is not None:
            updates["status"] = parse_transaction_status(self.status)

        kind = existing.transaction_kind
        if self.transaction_type is not None:
            kind = parse_transaction_kind(self.transaction_type)
            if kind == TransactionKind.TRANSFER:
                raise ValueError("Use PUT /movements to update transfer transactions.")
            updates["transaction_kind"] = kind

        merged = existing.model_copy(update=updates)

        if self.account_id is not None:
            if kind == TransactionKind.INCOME:
                merged.to_account_id = self.account_id
                merged.from_account_id = None
            elif kind == TransactionKind.EXPENSE:
                merged.from_account_id = self.account_id
                merged.to_account_id = None

        if self.category_id is not None:
            merged.category_id = self.category_id

        return merged


class TransactionResponse(BaseModel):
    """Transaction resource returned by CRUD endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID | None = None
    account_name: str | None = None
    category_id: uuid.UUID | None = None
    category_name: str | None = None
    transaction_type: str
    status: str
    amount: float
    currency: str
    description: str
    transaction_date: date
    reference_number: str | None = None
    tags: list[str] = Field(default_factory=list)
    is_recurring: bool = False
    template_id: uuid.UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_dto(cls, transaction: TransactionsDTO, *, include_names: bool = False) -> TransactionResponse:
        """Build an API response from a ``TransactionsDTO``."""
        account_name: str | None = None
        category_name: str | None = None
        if include_names:
            from_account = transaction.from_account_id
            to_account = transaction.to_account_id
            if isinstance(from_account, AccountsDTO):
                account_name = from_account.name
            elif isinstance(to_account, AccountsDTO):
                account_name = to_account.name
            category = transaction.category_id
            if isinstance(category, CategoriesDTO):
                category_name = category.name

        ts = transaction.transaction_ts
        if isinstance(ts, datetime):
            txn_date = ts.date()
        else:
            txn_date = ts

        template_id = _relation_uuid(transaction.template_id)
        return cls(
            id=transaction.id,
            account_id=derive_account_id(transaction),
            account_name=account_name,
            category_id=_relation_uuid(transaction.category_id),
            category_name=category_name,
            transaction_type=enum_to_api_slug(transaction.transaction_kind),
            status=enum_to_api_slug(transaction.status),
            amount=float(transaction.amount),
            currency=transaction.currency,
            description=transaction.description,
            transaction_date=txn_date,
            reference_number=transaction.reference_number,
            tags=list(transaction.tags or []),
            is_recurring=template_id is not None,
            template_id=template_id,
            created_at=transaction.created_at,
            updated_at=transaction.updated_at,
        )


class TransactionBulkCreate(BaseModel):
    """Request body for ``POST /transactions/bulk``."""

    model_config = ConfigDict(extra="forbid")

    # Hard schema ceiling; effective limit is ``Settings.API_BULK_MAX_TRANSACTIONS`` (router).
    transactions: list[TransactionCreate] = Field(min_length=1, max_length=MAX_BULK_TRANSACTIONS_HARD_CAP)


class TransactionBulkResponse(BaseModel):
    """Response body for ``POST /transactions/bulk``."""

    created: int = Field(ge=0)
    failed: int = Field(ge=0)
    transactions: list[TransactionResponse] = Field(default_factory=list)


def transactions_from_dataframe(df: pd.DataFrame) -> list[TransactionsDTO]:
    """Convert a transactions query DataFrame to DTO instances."""
    if getattr(df, "empty", True):
        return []
    dao_type = TransactionsDTO.__dao_type__
    transactions: list[TransactionsDTO] = []
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        if "Transactions" in row_dict and isinstance(row_dict["Transactions"], dao_type):
            transactions.append(TransactionsDTO.from_dao(row_dict["Transactions"]))
            continue
        if len(row_dict) == 1:
            only_value = next(iter(row_dict.values()))
            if isinstance(only_value, dao_type):
                transactions.append(TransactionsDTO.from_dao(only_value))
                continue
        transactions.append(TransactionsDTO.model_validate(row_dict))
    return transactions


__all__ = [
    "TransactionBulkCreate",
    "TransactionBulkResponse",
    "TransactionCreate",
    "TransactionResponse",
    "TransactionUpdate",
    "derive_account_id",
    "paginate_dataframe",
    "transactions_from_dataframe",
]
