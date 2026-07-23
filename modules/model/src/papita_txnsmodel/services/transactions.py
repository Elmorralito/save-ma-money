"""Transactions service module for the Papita Transactions system.

This module provides services for managing transaction entities in the system, including
transaction templates (recurring/planned) and posted transactions. It implements the
necessary functionality to handle relationships between transactions, accounts, and categories.

Classes:
    TransactionTemplatesService: Service for managing transaction template entities.
    TransactionsService: Service for managing posted transaction entities.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime
from typing import Annotated, Any, Dict

import pandas as pd
from pydantic import Field

from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO, TransactionTemplatesDTO
from papita_txnsmodel.access.transactions.query_filters import TransactionListFilterSpec, build_transaction_list_filters
from papita_txnsmodel.access.transactions.repository import TransactionsRepository, TransactionTemplatesRepository
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.model.enums import TransactionKind, TransactionStatus
from papita_txnsmodel.model.transactions import Transactions
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.balance_views import refresh_balance_materialized_views
from papita_txnsmodel.services.categories import CategoriesService
from papita_txnsmodel.services.extends import CategorizedEntitiesService, LinkedEntitiesService, LinkedEntity

logger = logging.getLogger(__name__)


class TransactionTemplatesService(CategorizedEntitiesService):
    """Service for managing transaction template entities in the Papita Transactions system.

    Attributes:
        category_id_column_name (str): Name of the column storing the category ID.
        category_id_field_name (str): Name of the field storing the category.
        dto_type (type[TransactionTemplatesDTO]): DTO type for transaction templates.
        repository_type (type[TransactionTemplatesRepository]): Repository for templates.
        categories_dto_type (type[CategoriesDTO]): DTO type for categories.
    """

    category_id_column_name: str = "category_id"
    category_id_field_name: str = "category_id"
    dto_type: type[TransactionTemplatesDTO] = TransactionTemplatesDTO
    repository_type: type[TransactionTemplatesRepository] = TransactionTemplatesRepository
    categories_dto_type: type[CategoriesDTO] = CategoriesDTO


# Backward-compatible alias for legacy callers.
IdentifiedTransactionsService = TransactionTemplatesService


class TransactionsService(LinkedEntitiesService):
    """Service for managing posted transaction entities in the Papita Transactions system.

    Attributes:
        __links__ (Dict[str, LinkedEntity]): Relationships to templates and accounts.
        dto_type (type[TransactionsDTO]): DTO type for transactions.
        repository_type (type[TransactionsRepository]): Repository for transactions.
        missing_upsertions_tol (float): Tolerance threshold for missing upsertions.
        on_conflict_do (OnUpsertConflictDo | str): Action to take on upsert conflicts.
    """

    __links__: Dict[str, LinkedEntity] = {
        "template_id": LinkedEntity(
            expected_other_entity_service_type=TransactionTemplatesService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="template_id",
            own_entity_link_field_name="template_id",
        ),
        "from_account_id": LinkedEntity(
            expected_other_entity_service_type=AccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="from_account_id",
            own_entity_link_field_name="from_account_id",
        ),
        "to_account_id": LinkedEntity(
            expected_other_entity_service_type=AccountsService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="to_account_id",
            own_entity_link_field_name="to_account_id",
        ),
        "category_id": LinkedEntity(
            expected_other_entity_service_type=CategoriesService,
            other_entity_link_column_name="id",
            other_entity_link_field_name="id",
            own_entity_link_column_name="category_id",
            own_entity_link_field_name="category_id",
        ),
    }

    dto_type: type[TransactionsDTO] = TransactionsDTO
    repository_type: type[TransactionsRepository] = TransactionsRepository

    missing_upsertions_tol: Annotated[float, Field(ge=0, le=0.5)] = 0.0
    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE

    def _maybe_refresh_balances(self, **kwargs) -> None:
        """Refresh balance materialized views when ``refresh_balances=True``.

        Defaults to off so create/delete/bulk paths do not N×-refresh MVs. Callers
        that need fresh balances pass ``refresh_balances=True`` once (e.g. after a
        bulk batch or transfer completion).
        """
        if not kwargs.get("refresh_balances", False):
            return
        try:
            refresh_balance_materialized_views(
                self.connector,
                concurrently=kwargs.get("refresh_balances_concurrently", False),
            )
        except Exception:
            logger.exception("Failed to refresh balance materialized views after transaction write.")

    def refresh_balance_views(self, *, concurrently: bool = False) -> None:
        """Explicitly refresh account/owner balance materialized views."""
        self._maybe_refresh_balances(refresh_balances=True, refresh_balances_concurrently=concurrently)

    def create(
        self, *, obj: TransactionsDTO | dict[str, Any], owner: UsersDTO | None = None, **kwargs
    ) -> TransactionsDTO:
        """Create a transaction; MV refresh is opt-in via ``refresh_balances=True``."""
        result = super().create(obj=obj, owner=owner, **kwargs)
        self._maybe_refresh_balances(**kwargs)
        return result

    def delete(
        self, *, obj: TransactionsDTO | dict[str, Any], owner: UsersDTO | None = None, hard: bool = False, **kwargs
    ) -> pd.DataFrame:
        """Delete a transaction; MV refresh is opt-in via ``refresh_balances=True``."""
        result = super().delete(obj=obj, owner=owner, hard=hard, **kwargs)
        self._maybe_refresh_balances(**kwargs)
        return result

    def upsert_records(self, *, df: pd.DataFrame, owner: UsersDTO | None = None, **kwargs) -> pd.DataFrame:
        """Upsert transactions; MV refresh is opt-in via ``refresh_balances=True``."""
        mappings = super().upsert_records(df=df, owner=owner, **kwargs)
        self._maybe_refresh_balances(**kwargs)
        return mappings

    def list_transactions(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        *,
        owner: UsersDTO,
        account_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        transaction_kind: TransactionKind | None = None,
        exclude_transfer: bool = True,
        status: TransactionStatus | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
        **kwargs,
    ) -> tuple[pd.DataFrame, int]:
        """List posted transactions for a tenant using SQLModel WHERE filters."""
        query_filters = build_transaction_list_filters(
            TransactionListFilterSpec(
                transaction_kind=transaction_kind,
                exclude_transfer=exclude_transfer,
                status=status,
                account_id=account_id,
                category_id=category_id,
                start_date=start_date,
                end_date=end_date,
                min_amount=min_amount,
                max_amount=max_amount,
                search=search,
            )
        )
        order_by = (Transactions.transaction_ts.desc(), Transactions.id.desc())
        total = self._repository.count_records(*query_filters, dto_type=self.dto_type, owner=owner, **kwargs)
        records = self._repository.get_records(
            *query_filters,
            dto_type=self.dto_type,
            owner=owner,
            skip=skip,
            limit=limit,
            order_by=order_by,
            **kwargs,
        )
        return records, total

    def get_transactions_frame(  # pylint: disable=too-many-arguments
        self,
        *,
        owner: UsersDTO,
        account_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        transaction_kind: TransactionKind | None = None,
        exclude_transfer: bool = False,
        status: TransactionStatus | None = None,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Load matching tenant transactions without list pagination (report paths).

        Unlike ``list_transactions``, this applies SQL filters only and returns the
        full matching frame so analytics can aggregate without N+1 page loops.
        """
        query_filters = build_transaction_list_filters(
            TransactionListFilterSpec(
                transaction_kind=transaction_kind,
                exclude_transfer=exclude_transfer,
                status=status,
                account_id=account_id,
                category_id=category_id,
                start_date=start_date,
                end_date=end_date,
            )
        )
        return self._repository.get_records(
            *query_filters,
            dto_type=self.dto_type,
            owner=owner,
            **kwargs,
        )

    def list_transfers(  # pylint: disable=too-many-arguments
        self,
        *,
        owner: UsersDTO,
        source_account_id: uuid.UUID | None = None,
        destination_account_id: uuid.UUID | None = None,
        status: TransactionStatus | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        skip: int = 0,
        limit: int = 100,
        **kwargs,
    ) -> tuple[pd.DataFrame, int]:
        """List transfer transactions for a tenant owner."""
        query_filters = build_transaction_list_filters(
            TransactionListFilterSpec(
                transaction_kind=TransactionKind.TRANSFER,
                exclude_transfer=False,
                status=status,
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                start_date=start_date,
                end_date=end_date,
            )
        )
        order_by = (Transactions.transaction_ts.desc(), Transactions.id.desc())
        total = self._repository.count_records(*query_filters, dto_type=self.dto_type, owner=owner, **kwargs)
        records = self._repository.get_records(
            *query_filters,
            dto_type=self.dto_type,
            owner=owner,
            skip=skip,
            limit=limit,
            order_by=order_by,
            **kwargs,
        )
        return records, total

    def create_transfer(
        self,
        *,
        obj: TransactionsDTO | dict[str, Any],
        owner: UsersDTO | None = None,
        **kwargs,
    ) -> TransactionsDTO:
        """Create a transfer transaction with both account legs enforced."""
        transfer = self.parse_dto(obj)
        transfer.transaction_kind = TransactionKind.TRANSFER
        if transfer.from_account_id is None or transfer.to_account_id is None:
            raise ValueError("Transfers require from_account_id and to_account_id.")
        transfer.status = TransactionStatus.PENDING
        return self.create(obj=transfer, owner=owner, **kwargs)

    def complete_transfer(
        self,
        *,
        transaction_id: uuid.UUID | TransactionsDTO | dict[str, Any],
        owner: UsersDTO | None = None,
        **kwargs,
    ) -> TransactionsDTO:
        """Mark a transfer as completed (``POST /movements/{id}/execute``)."""
        transfer = self._get_transfer(transaction_id=transaction_id, owner=owner, **kwargs)
        transfer.status = TransactionStatus.COMPLETED
        return self.create(obj=transfer, owner=owner, **kwargs)

    def cancel(
        self,
        *,
        transaction_id: uuid.UUID | TransactionsDTO | dict[str, Any],
        owner: UsersDTO | None = None,
        **kwargs,
    ) -> TransactionsDTO:
        """Cancel a transfer by setting ``status=CANCELLED`` (not soft delete)."""
        transfer = self._get_transfer(transaction_id=transaction_id, owner=owner, **kwargs)
        if transfer.status == TransactionStatus.CANCELLED:
            return transfer
        transfer.status = TransactionStatus.CANCELLED
        return self.create(obj=transfer, owner=owner, **kwargs)

    def _get_transfer(
        self,
        *,
        transaction_id: uuid.UUID | TransactionsDTO | dict[str, Any],
        owner: UsersDTO | None,
        **kwargs,
    ) -> TransactionsDTO:
        """Load and validate a transfer row for status transitions."""
        transfer = self.get(obj=transaction_id, owner=owner, include_linked_dtos=False, **kwargs)
        if transfer is None:
            raise ValueError("Transfer transaction not found.")
        if transfer.transaction_kind != TransactionKind.TRANSFER:
            raise ValueError("Transaction is not a transfer.")
        return transfer
