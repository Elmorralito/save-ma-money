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
from typing import Annotated, List, Self, Tuple

import pandas as pd
from pydantic import Field, model_validator
from rapidfuzz import fuzz
from rapidfuzz import process as fuzz_process

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.transactions import IdentifiedTransactionsService, TransactionsService
from papita_txnsmodel.services.types import TypesService
from papita_txnsmodel.utils.modelutils import validate_interest_rate
from papita_txnsregistrar.utils.enums import OnMultipleMatchesDo

from .abstract import AbstractLoadHandler
from .core import BaseLoadTableHandler

logger = logging.getLogger(__name__)


class IdentifiedTransactionsTableHandler(BaseLoadTableHandler[IdentifiedTransactionsService], TypesService):
    """
    Handler for loading and processing identified transactions table data.

    This handler specializes in managing identified transactions, which represent
    categorized or classified transaction templates in the system. It extends
    BaseLoadTableHandler with IdentifiedTransactionsService as the parameterized
    service type, and also inherits from TypesService to access transaction type
    information.

    The handler provides the necessary infrastructure to load, process, and save
    identified transaction data through the appropriate service layers. It establishes
    a dependency on TypesService to properly categorize and classify transactions
    based on their types.

    Attributes:
        dependencies: A dictionary mapping service names to service types,
                        automatically configured to include TypesService for type
                        information and classification.

    Examples:
        ```python
        handler = IdentifiedTransactionsTableHandler(config)
        handler.load_data(source_data)
        processed_data = handler.process()
        handler.dump_results(destination)
        ```
    """

    @model_validator(mode="after")
    def _validate(self) -> Self:
        """
        Validates and sets up the required dependencies for the handler.

        This method ensures that the handler has the necessary service dependencies
        established. If no dependencies are defined, it initializes them with
        TypesService which is required for properly handling identified transactions
        and their classification.

        Returns:
            Self: The validated instance of IdentifiedTransactionsTableHandler.
        """
        if not self.dependencies:
            self.dependencies = {
                "type": TypesService,
            }

        return self

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        return "identified_transactions_table", "identified_transactions"


class TransactionsHandler(AbstractLoadHandler[TransactionsService]):
    """
    Handler for processing and matching transaction data.

    This class extends AbstractLoadHandler to provide specialized functionality for
    transaction data processing, including matching account IDs and identified transactions.
    It supports both exact matching and fuzzy matching strategies with configurable
    thresholds and behaviors for handling multiple matches.

    The handler processes raw transaction data through a series of matching operations:
    1. Matches account IDs against the accounts database
    2. Matches identified transaction references against the identified transactions database
    3. Standardizes the data according to the service DTO type specification

    Attributes:
        accounts_service: Service for accessing and querying account data.
        identified_transactions_service: Service for accessing identified transaction data.
        on_multiple_account_matches: Strategy to use when multiple accounts match (FAIL, TAKE_FIRST, etc.).
        case_sensitive: Whether string matching should be case-sensitive.
        fuzzy_match: Whether to use fuzzy string matching instead of exact matching.
        fuzzy_match_threshold: Threshold value for fuzzy matching (0.7-100), determining match quality.
    """

    accounts_service: AccountsService
    identified_transactions_service: IdentifiedTransactionsService
    on_multiple_account_matches: OnMultipleMatchesDo = OnMultipleMatchesDo.FAIL
    case_sensitive: bool = False
    fuzzy_match: bool = False
    fuzzy_match_threshold: Annotated[int | float, Field(gt=0.7, lt=100), validate_interest_rate] = 0.9

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        return "transactions_handler", "transactions"

    @property
    def accounts(self) -> pd.DataFrame:
        """
        Get account data from the accounts service.

        Retrieves all accounts from the accounts service and returns them as a DataFrame
        for use in matching operations.

        Returns:
            DataFrame containing account data with all available fields.
        """
        return self._load_core_data(self.accounts_service)

    @property
    def identified_transactions(self) -> pd.DataFrame:
        """
        Get identified transaction data from the identified transactions service.

        Retrieves all identified transactions from the service and returns them as a DataFrame
        for use in matching operations.

        Returns:
            DataFrame containing identified transaction data with all available fields.
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

        Performs exact string comparison to find matches in the provided data. A match
        is found if the value exactly equals the ID, name, or is contained in the tags list.

        Args:
            value: The value to match against records (account name, ID, etc.).
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

        Performs similarity-based string comparison using the RapidFuzz library to find
        approximate matches. The fuzzy_match_threshold determines the minimum similarity
        score required for a match.

        Args:
            value: The value to match against records (account name, ID, etc.).
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
        based on the instance configuration. It serves as the main entry point for the
        matching process.

        Args:
            value: The value to match against records (account name, ID, etc.).
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
        in the system. It handles both from_account_id and to_account_id columns and filters out
        invalid transactions (those with both accounts null or both accounts non-null).

        Args:
            data: DataFrame containing transaction data with from_account_id and to_account_id columns.
            **kwargs: Additional arguments passed to the matching functions.

        Returns:
            DataFrame with matched account IDs, filtered to include only valid entries where exactly
            one of from_account_id or to_account_id is non-null.
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
        in the system. It uses the same matching strategy as account matching but applies it to the
        identified_transaction_id column.

        Args:
            data: DataFrame containing transaction data with identified_transaction_id column.
            **kwargs: Additional arguments passed to the matching functions.

        Returns:
            DataFrame with matched identified transaction IDs where possible.
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

    def dump(self, **kwargs) -> Self:
        """
        Save the loaded transaction data using the associated service.

        This method persists the processed and matched transaction data to the underlying
        data store through the service layer.

        Args:
            **kwargs: Additional arguments passed to the service's upsert_records method,
                     such as batch size or conflict resolution strategies.

        Returns:
            Self instance for method chaining.

        Raises:
            ValueError: If there is no loaded data to dump (call load() first).
        """
        if not isinstance(self._loaded_data, pd.DataFrame):
            raise ValueError("There is no loaded data to dump.")

        return self.service.upsert_records(df=self._loaded_data, **kwargs)

    def load(self, *, data: pd.DataFrame | List[TableDTO] | List[dict] | TableDTO, **kwargs) -> Self:
        """
        Load and process transaction data.

        This method performs the complete transaction data processing pipeline:
        1. Loads the raw transaction data
        2. Matches account IDs for both from_account and to_account fields
        3. Matches identified transaction IDs
        4. Standardizes the data according to the DTO type specification

        Args:
            data: Raw transaction data to be processed, can be in various formats.
            **kwargs: Additional arguments for processing and error handling,
                      including loggers and strategy-specific parameters.

        Returns:
            Self instance for method chaining.

        Raises:
            Various exceptions may be raised based on the on_failure_do strategy
            when data is empty or invalid.
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
