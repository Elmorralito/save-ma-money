"""
Transaction Data Processing and Matching Module.

This module provides functionality for handling transaction data within the papita_txnsregistrar system.
It includes capabilities for matching transaction accounts and identified transactions against existing
records, with support for both exact and fuzzy matching strategies. The module is primarily used for
data processing, validation, and standardization of transaction records before they are persisted.

The main class, TransactionsHandler, extends AbstractLoadHandler to provide specific transaction
processing logic including account matching and identified transaction matching.
"""

import logging
import uuid
from typing import Annotated

import pandas as pd
from pydantic import Field
from rapidfuzz import fuzz
from rapidfuzz import process as fuzz_process

from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.transactions import IdentifiedTransactionsService, TransactionsService
from papita_txnsmodel.utils.modelutils import validate_interest_rate
from papita_txnsregistrar.handlers.abstract import AbstractLoadHandler
from papita_txnsregistrar.utils.enums import OnMultipleMatchesDo

logger = logging.getLogger(__name__)


class TransactionsHandler(AbstractLoadHandler[TransactionsService]):
    """
    Handler for processing and matching transaction data.

    This class extends AbstractLoadHandler to provide specialized functionality for
    transaction data processing, including matching account IDs and identified transactions.
    It supports both exact matching and fuzzy matching strategies with configurable
    thresholds and behaviors for handling multiple matches.

    Attributes:
        accounts_service: Service for accessing account data.
        identified_transactions_service: Service for accessing identified transaction data.
        on_multiple_account_matches: Strategy to use when multiple accounts match.
        case_sensitive: Whether string matching should be case-sensitive.
        fuzzy_match: Whether to use fuzzy string matching instead of exact matching.
        fuzzy_match_threshold: Threshold value for fuzzy matching (0.7-100).
    """

    accounts_service: AccountsService
    identified_transactions_service: IdentifiedTransactionsService
    on_multiple_account_matches: OnMultipleMatchesDo = OnMultipleMatchesDo.FAIL
    case_sensitive: bool = False
    fuzzy_match: bool = False
    fuzzy_match_threshold: Annotated[int | float, Field(gt=0.7, lt=100), validate_interest_rate] = 0.9

    @property
    def accounts(self) -> pd.DataFrame:
        """
        Get account data from the accounts service.

        Returns:
            DataFrame containing account data.
        """
        return self._load_core_data(self.accounts_service)

    @property
    def identified_transactions(self) -> pd.DataFrame:
        """
        Get identified transaction data from the identified transactions service.

        Returns:
            DataFrame containing identified transaction data.
        """
        return self._load_core_data(self.identified_transactions_service)

    def _match_exact_records(
        self,
        *,
        value: str | uuid.UUID,
        core_data: pd.DataFrame,
        core_id_column: str,
        core_name_column: str,
        core_tags_column: str,
        **kwargs,
    ) -> str | uuid.UUID | None:
        """
        Match records using exact matching on ID, name, or tags.

        Args:
            value: The value to match against records.
            core_data: DataFrame containing the records to match against.
            core_id_column: Column name for the ID field in core_data.
            core_name_column: Column name for the name field in core_data.
            core_tags_column: Column name for the tags field in core_data.
            **kwargs: Additional arguments passed to the matching strategy.

        Returns:
            Matched ID, or None if no match was found.
        """
        filtered = core_data.loc[
            (core_data[core_id_column] == value)
            | (core_data[core_name_column] == value)
            | core_data[core_tags_column].apply(lambda li: value in li)
        ]
        record = self.on_multiple_account_matches.choose(matches=filtered, **kwargs)
        if getattr(record, "empty", True):
            return None

        return record[core_id_column]

    def _match_fuzzy_records(
        self,
        *,
        value: str | uuid.UUID,
        core_data: pd.DataFrame,
        core_id_column: str,
        core_name_column: str,
        core_tags_column: str,
        **kwargs,
    ) -> str | uuid.UUID | None:
        """
        Match records using fuzzy matching on ID, name, or tags.

        Args:
            value: The value to match against records.
            core_data: DataFrame containing the records to match against.
            core_id_column: Column name for the ID field in core_data.
            core_name_column: Column name for the name field in core_data.
            core_tags_column: Column name for the tags field in core_data.
            **kwargs: Additional arguments passed to the matching strategy.

        Returns:
            Matched ID, or None if no match was found.
        """

        def _compare_record(row: pd.Series) -> bool:
            if value == row[core_id_column]:
                return True

            if fuzz.ratio(value, row[core_name_column]) >= self.fuzzy_match_threshold:
                return True

            labels = fuzz_process.extractOne(value, row[core_tags_column], scorer=self.fuzzy_match_threshold)
            if labels is None:
                return False

            return True

        filtered = core_data.apply(_compare_record, axis=1)
        record = self.on_multiple_account_matches.choose(matches=core_data.iloc[filtered.loc[filtered].index], **kwargs)
        if record.empty:
            return None

        return record[core_id_column]

    def _match_records(
        self,
        *,
        value: str | uuid.UUID,
        core_data: pd.DataFrame,
        core_id_column: str,
        core_name_column: str,
        core_tags_column: str,
        **kwargs,
    ) -> str | uuid.UUID | None:
        """
        Match records using either exact or fuzzy matching based on configuration.

        This method handles case sensitivity and delegates to either exact or fuzzy matching
        based on the instance configuration.

        Args:
            value: The value to match against records.
            core_data: DataFrame containing the records to match against.
            core_id_column: Column name for the ID field in core_data.
            core_name_column: Column name for the name field in core_data.
            core_tags_column: Column name for the tags field in core_data.
            **kwargs: Additional arguments passed to the matching strategy.

        Returns:
            Matched ID, or None if no match was found.
        """
        if self.case_sensitive:
            value_ = value.lower() if isinstance(value, str) else value
            core_data_ = core_data.copy()
            core_data_[core_name_column] = core_data_[core_name_column].str.lower()
            core_data_[core_tags_column] = core_data_[core_tags_column].apply(lambda li: map(str.lower, li))
        else:
            value_ = value
            core_data_ = core_data.copy()

        if self.fuzzy_match:
            return self._match_fuzzy_records(
                value=value_,
                core_data=core_data_,
                core_id_column=core_id_column,
                core_name_column=core_name_column,
                core_tags_column=core_tags_column,
                **kwargs,
            )

        return self._match_exact_records(
            value=value_,
            core_data=core_data_,
            core_id_column=core_id_column,
            core_name_column=core_name_column,
            core_tags_column=core_tags_column,
            **kwargs,
        )

    def _match_accounts(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        Match account IDs in the transaction data with accounts in the accounts DataFrame.

        This method processes the transaction data to resolve account references to actual account IDs
        in the system. It handles both from_account_id and to_account_id columns.

        Args:
            data: DataFrame containing transaction data with from_account_id and to_account_id columns.
            **kwargs: Additional arguments passed to the matching functions.

        Returns:
            DataFrame with matched account IDs, filtered to include only valid entries.
        """
        id_column = self.accounts_service.dto_type.__dao_type__.__table__.c.id.key
        name_column = self.accounts_service.dto_type.__dao_type__.__table__.c.name.key
        tags_column = self.accounts_service.dto_type.__dao_type__.__table__.c.tags.key
        from_account_id_column = self.service.dto_type.__dao_type__.__table__.c.from_account_id.key
        to_account_id_column = self.service.dto_type.__dao_type__.__table__.c.to_account_id.key
        accounts = self.accounts[[id_column, name_column, tags_column]]
        data_columns = [from_account_id_column, to_account_id_column]
        data_ = data.copy()
        for col_ in data_columns:
            data_[col_] = data_[col_].apply(
                lambda value: self._match_records(
                    value=value,
                    core_data=accounts,
                    core_id_column=id_column,
                    core_name_column=name_column,
                    core_tags_column=tags_column,
                    **kwargs,
                )
            )

        return data_.loc[
            ~(
                (pd.isna(data_[from_account_id_column]) & pd.isna(data_[to_account_id_column]))
                | (~pd.isna(data_[from_account_id_column]) & ~pd.isna(data_[to_account_id_column]))
            )
        ]

    def _match_identifed_transactions(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        Match identified transaction IDs in the transaction data.

        This method resolves references to identified transactions to actual identified transaction IDs
        in the system.

        Args:
            data: DataFrame containing transaction data with identified_transaction_id column.
            **kwargs: Additional arguments passed to the matching functions.

        Returns:
            DataFrame with matched identified transaction IDs.
        """
        id_column = self.identified_transactions_service.dto_type.__dao_type__.__table__.c.id.key
        name_column = self.identified_transactions_service.dto_type.__dao_type__.__table__.c.name.key
        tags_column = self.identified_transactions_service.dto_type.__dao_type__.__table__.c.tags.key
        identified_transaction_id_column = self.service.dto_type.__dao_type__.__table__.c.identified_transaction_id.key
        identified_transactions = self.identified_transactions[[id_column, name_column, tags_column]]
        data_ = data.copy()
        data_[identified_transaction_id_column] = data_[identified_transaction_id_column].apply(
            lambda value: self._match_records(
                value=value,
                core_data=identified_transactions,
                core_id_column=id_column,
                core_name_column=name_column,
                core_tags_column=tags_column,
                **kwargs,
            )
        )
        return data_

    def dump(self, **kwargs) -> "AbstractLoadHandler":
        """
        Save the loaded transaction data using the associated service.

        Args:
            **kwargs: Additional arguments passed to the service's upsert_records method.

        Returns:
            Self instance for method chaining.

        Raises:
            ValueError: If there is no loaded data to dump.
        """
        if not isinstance(self._loaded_data, pd.DataFrame):
            raise ValueError("There is no loaded data to dump.")

        return self.service.upsert_records(df=self._loaded_data, **kwargs)

    def load(self, *, data: pd.DataFrame, **kwargs) -> "AbstractLoadHandler":
        """
        Load and process transaction data.

        This method loads transaction data, matches account IDs and identified transaction IDs,
        and standardizes the data according to the DTO type specification.

        Args:
            data: DataFrame containing raw transaction data to be processed.
            **kwargs: Additional arguments for processing and error handling.

        Returns:
            Self instance for method chaining.

        Raises:
            Various exceptions may be raised based on the on_failure_do strategy.
        """
        logger.debug("Loading data from loader '%s'", self.loader.__class__.__name__)
        if getattr(data, "empty", True):
            self.on_failure_do.handle("There are no data or it's empty.", logger=kwargs.pop("logger", logger), **kwargs)

        accounts_data_ = self._match_accounts(data, **kwargs)
        if getattr(accounts_data_, "empty", True):
            self.on_failure_do.handle(
                "There are no data with valid account relationships.", logger=kwargs.pop("logger", logger), **kwargs
            )

        identified_data_ = self._match_accounts(accounts_data_, **kwargs)
        self._loaded_data = self.service.dto_type.standardized_dataframe(identified_data_, **kwargs)
        return self
