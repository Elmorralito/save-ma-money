# pylint: disable=access-member-before-definition
# mypy: disable-error-code="has-type"
"""
Transaction Data Processing and Matching Module.

This module provides functionality for handling transaction data within the papita_txnsregistrar system.
It includes capabilities for matching transaction accounts and templates against existing records,
with support for both exact and fuzzy matching strategies.
"""

import inspect
import logging
from typing import TYPE_CHECKING, Annotated, List, Self, Tuple

import pandas as pd
from pydantic import Field, model_validator

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.categories import CategoriesService
from papita_txnsmodel.services.transactions import TransactionsService, TransactionTemplatesService
from papita_txnsmodel.utils.enums import OnMultipleMatchesDo
from papita_txnsmodel.utils.modelutils import validate_interest_rate

from .abstract import AbstractHandler
from .base import BaseTableHandler
from .matching import ReferenceIndex, bulk_match_column

if TYPE_CHECKING:
    from papita_txnsmodel.access.users.dto import UsersDTO

logger = logging.getLogger(__name__)


class TransactionTemplatesTableHandler(BaseTableHandler[TransactionTemplatesService, CategoriesService]):
    """Handler for loading and processing transaction template table data."""

    @model_validator(mode="after")
    def _validate(self) -> Self:
        """Validate and set up the required dependencies for the handler."""
        if not self.dependencies:
            self.dependencies = {
                "category_id": CategoriesService,
            }

        connector = self.service.connector
        self.dependencies = {
            name: (service.model_validate({"connector": connector}) if inspect.isclass(service) else service)
            for name, service in self.dependencies.items()
        }
        return self

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        """Get the v3 label identifiers for this handler."""
        return (
            "transaction_templates_table",
            "transaction_templates",
        )

    @classmethod
    def legacy_labels(cls) -> Tuple[str, ...]:
        """Registrar-compat labels that emit DeprecationWarning on lookup."""
        return "identified_transactions_table", "identified_transactions"


# Backward-compatible alias for legacy callers.
IdentifiedTransactionsTableHandler = TransactionTemplatesTableHandler


class TransactionsHandler(AbstractHandler[TransactionsService]):
    """Handler for processing and matching posted transaction data."""

    service: TransactionsService
    accounts_service: AccountsService
    categories_service: CategoriesService | None = None
    transaction_templates_service: TransactionTemplatesService | None = None
    on_multiple_account_matches: OnMultipleMatchesDo = OnMultipleMatchesDo.FAIL
    on_conflict_do: OnUpsertConflictDo = OnUpsertConflictDo.UPDATE
    case_sensitive: bool = False
    fuzzy_match: bool = False
    fuzzy_match_threshold: Annotated[int | float, Field(gt=0.7, lt=100), validate_interest_rate] = 0.9

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        """Get the label identifiers for this handler."""
        return "transactions_handler", "transactions"

    def accounts(self, owner: "UsersDTO | None" = None) -> pd.DataFrame:
        """Get account data from the accounts service."""
        return self._load_core_data(self.accounts_service, owner=owner)

    def transaction_templates(self, owner: "UsersDTO | None" = None) -> pd.DataFrame:
        """Get transaction template data from the templates service."""
        return self._load_core_data(self.transaction_templates_service, owner=owner)

    def categories(self, owner: "UsersDTO | None" = None) -> pd.DataFrame:
        """Get category data from the categories service."""
        return self._load_core_data(self.categories_service, owner=owner)

    def _reference_index(
        self,
        core_data: pd.DataFrame,
        *,
        id_column: str,
        name_column: str,
        tags_column: str,
    ) -> ReferenceIndex:
        """Build a reference index for bulk column matching."""
        return ReferenceIndex(
            core_data,
            id_column=id_column,
            name_column=name_column,
            tags_column=tags_column,
            case_sensitive=self.case_sensitive,
        )

    def _bulk_match_column(
        self,
        data: pd.DataFrame,
        column: str,
        core_data: pd.DataFrame,
        *,
        id_column: str,
        name_column: str,
        tags_column: str,
        owner: "UsersDTO | None" = None,
        **kwargs,
    ) -> pd.Series:
        """Match a single column using bulk exact matching with optional fuzzy fallback."""
        if column not in data.columns:
            return data[column] if column in data.columns else pd.Series(dtype=object)

        index = self._reference_index(
            core_data,
            id_column=id_column,
            name_column=name_column,
            tags_column=tags_column,
        )
        return bulk_match_column(
            data[column],
            index,
            fuzzy_match=self.fuzzy_match,
            fuzzy_threshold=self.fuzzy_match_threshold,
            on_multiple_matches=kwargs.pop("on_conflict_do", self.on_multiple_account_matches),
            core_data=core_data,
        )

    def _match_accounts(self, data: pd.DataFrame, owner: "UsersDTO | None" = None, **kwargs) -> pd.DataFrame:
        """Match account IDs in the transaction data with accounts in the accounts DataFrame."""
        id_column = self.accounts_service.dto_type.__dao_type__.__table__.c.id.key
        name_column = self.accounts_service.dto_type.__dao_type__.__table__.c.name.key
        tags_column = self.accounts_service.dto_type.__dao_type__.__table__.c.tags.key
        from_account_id_column = self.service.dto_type.__dao_type__.__table__.c.from_account_id.key
        to_account_id_column = self.service.dto_type.__dao_type__.__table__.c.to_account_id.key
        accounts = self.accounts(owner=owner)[[id_column, name_column, tags_column]]
        data_ = data.copy()
        for col_ in (from_account_id_column, to_account_id_column):
            if col_ not in data_.columns:
                continue
            data_[col_] = self._bulk_match_column(
                data_,
                col_,
                accounts,
                id_column=id_column,
                name_column=name_column,
                tags_column=tags_column,
                owner=owner,
                **kwargs,
            )

        has_from = from_account_id_column in data_.columns
        has_to = to_account_id_column in data_.columns
        if has_from and has_to:
            return data_.loc[~(pd.isna(data_[from_account_id_column]) & pd.isna(data_[to_account_id_column]))]
        if has_from:
            return data_.loc[~pd.isna(data_[from_account_id_column])]
        if has_to:
            return data_.loc[~pd.isna(data_[to_account_id_column])]
        return data_

    def _match_templates(self, data: pd.DataFrame, owner: "UsersDTO | None" = None, **kwargs) -> pd.DataFrame:
        """Match template IDs in the transaction data."""
        if self.transaction_templates_service is None:
            return data

        id_column = self.transaction_templates_service.dto_type.__dao_type__.__table__.c.id.key
        name_column = self.transaction_templates_service.dto_type.__dao_type__.__table__.c.name.key
        tags_column = self.transaction_templates_service.dto_type.__dao_type__.__table__.c.tags.key
        template_id_column = self.service.dto_type.__dao_type__.__table__.c.template_id.key
        templates = self.transaction_templates(owner=owner)[[id_column, name_column, tags_column]]
        data_ = data.copy()
        if template_id_column not in data_.columns:
            return data_

        data_[template_id_column] = self._bulk_match_column(
            data_,
            template_id_column,
            templates,
            id_column=id_column,
            name_column=name_column,
            tags_column=tags_column,
            owner=owner,
            **kwargs,
        )
        return data_

    def _match_categories(self, data: pd.DataFrame, owner: "UsersDTO | None" = None, **kwargs) -> pd.DataFrame:
        """Match category IDs in the transaction data."""
        if self.categories_service is None:
            return data

        id_column = self.categories_service.dto_type.__dao_type__.__table__.c.id.key
        name_column = self.categories_service.dto_type.__dao_type__.__table__.c.name.key
        tags_column = self.categories_service.dto_type.__dao_type__.__table__.c.tags.key
        category_id_column = self.service.dto_type.__dao_type__.__table__.c.category_id.key
        categories = self.categories(owner=owner)[[id_column, name_column, tags_column]]
        data_ = data.copy()
        if category_id_column not in data_.columns:
            return data_

        data_[category_id_column] = self._bulk_match_column(
            data_,
            category_id_column,
            categories,
            id_column=id_column,
            name_column=name_column,
            tags_column=tags_column,
            owner=owner,
            **kwargs,
        )
        return data_

    def dump(self, *, owner: "UsersDTO | None" = None, **kwargs) -> Self:
        """Save the loaded transaction data using the associated service."""
        if not isinstance(self._loaded_data, pd.DataFrame):
            raise ValueError("There is no loaded data to dump.")

        self.service.upsert_records(
            df=self._loaded_data,
            owner=owner,
            on_conflict_do=kwargs.pop("on_conflict_do", self.on_conflict_do),
            **kwargs,
        )
        return self

    def load(
        self,
        *,
        data: pd.DataFrame | List[TableDTO] | List[dict] | TableDTO,
        owner: "UsersDTO | None" = None,
        **kwargs,
    ) -> Self:
        """Load and process transaction data."""
        logger.debug("Loading data into %s", self.service.dto_type.__dao_type__.__tablename__)
        if getattr(data, "empty", True):
            self.on_failure_do.handle("There are no data or it's empty.", logger=kwargs.pop("logger", logger), **kwargs)

        accounts_data_ = self._match_accounts(data, owner=owner, **kwargs)
        if getattr(accounts_data_, "empty", True):
            self.on_failure_do.handle(
                "There are no data with valid account relationships.", logger=kwargs.pop("logger", logger), **kwargs
            )

        template_data_ = self._match_templates(accounts_data_, owner=owner, **kwargs)
        category_data_ = self._match_categories(template_data_, owner=owner, **kwargs)
        self._loaded_data = self.service.dto_type.standardized_dataframe(category_data_, **kwargs)
        return self
