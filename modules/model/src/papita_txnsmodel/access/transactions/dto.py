"""Transactions DTO module for the Papita Transactions system.

This module defines the Data Transfer Objects (DTOs) for transaction entities in the system.
It provides validation and data structures for transaction templates (recurring/planned)
and posted ledger transactions.

Classes:
    TransactionTemplatesDTO: DTO for recurring or planned transaction templates.
    TransactionsDTO: DTO for posted financial transactions.
"""

import datetime
import uuid

from pydantic import Field, field_serializer

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.base.dto import CoreTableDTO, TableDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.users.dto import OwnedTableDTO
from papita_txnsmodel.model.enums import TransactionKind, TransactionStatus
from papita_txnsmodel.model.transactions import Transactions, TransactionTemplates


def _serialize_relation_id(value: uuid.UUID | TableDTO) -> uuid.UUID:
    """Return the UUID for a relation field that may be stored as a DTO."""
    if isinstance(value, TableDTO):
        if value.id is None:
            raise ValueError("Related DTO must include an id.")
        return value.id
    return value


class TransactionTemplatesDTO(OwnedTableDTO, CoreTableDTO):
    """DTO for recurring or planned transaction templates in the system.

    This class represents transaction templates that may generate posted transactions.
    It extends CoreTableDTO and links to the TransactionTemplates ORM model.

    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        category_id (uuid.UUID | CategoriesDTO): Associated income/expense category.
        planned_amount (float): Expected transaction amount. Must be positive.
        planned_day (int): Day of the month when the transaction is expected (1-31).
        use_month_end (bool): Whether to schedule on the last day of the month.
        due_date (datetime.date | None): Optional one-off calendar due date (PPT-071).
        remind_days_before (int | None): Optional lead days before due for in-app reminders.
        from_account_id (uuid.UUID | AccountsDTO | None): Optional pay-from account.
    """

    __dao_type__ = TransactionTemplates

    category_id: uuid.UUID | CategoriesDTO = Field(serialization_alias="category_id")
    planned_amount: float = Field(gt=0, description="Expected value of the transaction")
    planned_day: int = Field(ge=1, le=31, description="Day of the month when the transaction is expected to occur")
    use_month_end: bool = False
    due_date: datetime.date | None = Field(
        default=None,
        description="One-off payment due calendar date; recurring templates leave this null",
    )
    remind_days_before: int | None = Field(
        default=None,
        ge=0,
        description="Days before due to surface an in-app reminder; null means no lead window",
    )
    from_account_id: uuid.UUID | AccountsDTO | None = Field(
        default=None,
        description="Optional account to pay from when marking a due as paid",
    )

    @field_serializer("category_id", "from_account_id")
    def _serialize_template_relations(self, value: uuid.UUID | TableDTO | None) -> uuid.UUID | None:
        """Serialize category_id / from_account_id to UUID values.

        Args:
            value: Relation as UUID, DTO, or None.

        Returns:
            uuid.UUID | None: The related entity UUID, or None.
        """
        if value is None:
            return None
        return _serialize_relation_id(value)


class TransactionsDTO(OwnedTableDTO):
    """DTO for posted financial transactions in the system.

    This class represents ledger transactions with v3 semantics (kind, amount,
    category, template, and account links). It links to the Transactions ORM model.

    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        transaction_kind (TransactionKind): Income, expense, or transfer semantics.
        amount (float): Monetary amount. Must be positive.
        currency (str): ISO 4217 currency code.
        transaction_ts (datetime.datetime): Timestamp when the transaction occurred.
        from_account (Optional): Source account reference.
        to_account (Optional): Destination account reference.
        category_id (Optional): Associated category reference.
        template_id (Optional): Source template reference.
        status (TransactionStatus): Posting status.
    """

    __dao_type__ = Transactions

    transaction_kind: TransactionKind
    amount: float = Field(gt=0, description="Monetary value of the transaction")
    currency: str = Field(min_length=3, max_length=3, default="USD")
    transaction_ts: datetime.datetime = Field(default_factory=datetime.datetime.now)
    from_account_id: uuid.UUID | AccountsDTO | None = None
    to_account_id: uuid.UUID | AccountsDTO | None = None
    category_id: uuid.UUID | CategoriesDTO | None = None
    template_id: uuid.UUID | TransactionTemplatesDTO | None = None
    status: TransactionStatus = TransactionStatus.COMPLETED
    description: str = ""
    reference_number: str | None = None
    tags: list[str] = Field(default_factory=list)

    @field_serializer("from_account_id", "to_account_id", "category_id", "template_id")
    def _serialize_relations(self, value: uuid.UUID | TableDTO | None) -> uuid.UUID | None:
        """Serialize relationship fields to their ID values.

        Args:
            value: The relationship value to serialize, either a UUID, TableDTO instance, or None.

        Returns:
            uuid.UUID or None: The UUID of the related entity, or None if no relation exists.
        """
        if value is None:
            return None

        return _serialize_relation_id(value)
