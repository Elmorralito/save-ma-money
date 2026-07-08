"""Transactions service module for the Papita Transactions system.

This module provides services for managing transaction entities in the system, including
transaction templates (recurring/planned) and posted transactions. It implements the
necessary functionality to handle relationships between transactions, accounts, and categories.

Classes:
    TransactionTemplatesService: Service for managing transaction template entities.
    TransactionsService: Service for managing posted transaction entities.
"""

import logging
from typing import Annotated, Dict

import pandas as pd
from pydantic import Field

from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO, TransactionTemplatesDTO
from papita_txnsmodel.access.transactions.repository import TransactionsRepository, TransactionTemplatesRepository
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
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

    def upsert_records(self, *, df: pd.DataFrame, owner: UsersDTO | None = None, **kwargs) -> pd.DataFrame:
        """Upsert transactions and optionally refresh balance materialized views."""
        mappings = super().upsert_records(df=df, owner=owner, **kwargs)
        if kwargs.get("refresh_balances", True):
            try:
                refresh_balance_materialized_views(
                    self.connector,
                    concurrently=kwargs.get("refresh_balances_concurrently", False),
                )
            except Exception:
                logger.exception("Failed to refresh balance materialized views after transaction upsert.")
        return mappings
