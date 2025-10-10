# pylint: disable=W0511

# import logging
# import uuid
# from typing import Annotated

# import pandas as pd
# from pydantic import Field
# from rapidfuzz import fuzz, process

# from papita_txnsmodel.services.accounts import AccountsService
# from papita_txnsmodel.services.transactions import IdentifiedTransactionsService, TransactionsService
# from papita_txnsmodel.utils.modelutils import validate_interest_rate
# from papita_txnsregistrar.handlers.abstract import AbstractLoadHandler
# from papita_txnsregistrar.utils.enums import OnMultipleMatchesDo

# logger = logging.getLogger(__name__)


# # TODO: FIX IT. I ain't convinced with da shiit, no ma'am
# class TransactionsHandler(AbstractLoadHandler[TransactionsService]):

#     accounts_service: AccountsService
#     identified_transactions_service: IdentifiedTransactionsService
#     on_multiple_account_matches: OnMultipleMatchesDo = OnMultipleMatchesDo.FAIL
#     fuzzy_match: bool = False
#     fuzzy_match_threshold: Annotated[int | float, Field(gt=0.7, lt=100), validate_interest_rate] = 0.9

#     @property
#     def accounts(self) -> pd.DataFrame:
#         return self._load_core_data(self.accounts_service)

#     @property
#     def identified_transactions(self) -> pd.DataFrame:
#         return self._load_core_data(self.identified_transactions_service)

#     def _match(
#         self, key: str | uuid.UUID, core_data: pd.DataFrame, id_column: str, name_column: str, tags_column: str
#     ) -> uuid.UUID:
#         """
#         Match a key against the core_data DataFrame using either strict or fuzzy matching.

#         Args:
#             key: The key to match (account name, id or tag)
#             core_data: DataFrame containing account data
#             id_column: Column name for id in core_data
#             name_column: Column name for name in core_data
#             tags_column: Column name for tags in core_data

#         Returns:
#             UUID of the matched account
#         """
#         if isinstance(key, uuid.UUID) or str(key).replace("-", "").isalnum() and len(str(key)) == 32:
#             # Direct ID match attempt first
#             direct_matches = core_data[core_data[id_column] == key]
#             if not direct_matches.empty:
#                 return direct_matches.iloc[0][id_column]

#         if self.fuzzy_match:
#             fuzzy_match_threshold = self.fuzzy_match_threshold * 100

#             # Try name matching with fuzzy ratio
#             name_matches = core_data[
#                 fuzz.ratio(str(key), core_data[name_column], score_cutoff=fuzzy_match_threshold) > 0
#             ]

#             # Try matching against tags if available
#             tag_matches = pd.DataFrame()
#             if tags_column in core_data.columns:
#                 # Filter rows where tags is not None or empty
#                 tag_rows = core_data[core_data[tags_column].notna() & (core_data[tags_column] != [])]

#                 if not tag_rows.empty:
#                     # Extract best matches from tags lists
#                     tag_matches_indices = []
#                     tag_match_scores = []

#                     for idx, row in tag_rows.iterrows():
#                         tags = row[tags_column]
#                         if isinstance(tags, list) and tags:
#                             match = process.extractOne(
#                                 str(key), tags, scorer=fuzz.ratio, score_cutoff=fuzzy_match_threshold
#                             )
#                             if match:
#                                 tag_matches_indices.append(idx)
#                                 tag_match_scores.append(match[1])  # match[1] is the score

#                     if tag_matches_indices:
#                         tag_matches = tag_rows.loc[tag_matches_indices]

#             # Combine matches
#             matches = pd.concat([name_matches, tag_matches]).drop_duplicates()

#             if matches.empty:
#                 raise ValueError(f"No account found matching '{key}'")

#             if len(matches) > 1:
#                 self.on_multiple_account_matches.choose(matches)

#             return matches.iloc[0][id_column]
#         else:
#             # Strict matching only
#             direct_matches = core_data[(core_data[id_column] == key) | (core_data[name_column] == key)]

#             # Try matching against tags if available
#             if tags_column in core_data.columns:
#                 # Find rows where the key is in the tags list
#                 tag_matches = core_data[
#                     core_data[tags_column].apply(
#                         lambda tags: isinstance(tags, list) and str(key) in [str(t) for t in tags]
#                     )
#                 ]
#                 direct_matches = pd.concat([direct_matches, tag_matches]).drop_duplicates()

#             if direct_matches.empty:
#                 raise ValueError(f"No account found matching '{key}'")

#             if len(direct_matches) > 1:
#                 self.on_multiple_account_matches.choose(matches)

#             return direct_matches.iloc[0][id_column]

#     def _match_accounts(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
#         """
#         Match account IDs in the transaction data with accounts in the accounts DataFrame.

#         Args:
#             data: DataFrame containing transaction data with from_account_id and to_account_id columns

#         Returns:
#             DataFrame with matched account IDs
#         """
#         accounts = self.accounts[
#             [
#                 self.accounts_service.dto_type.__dao_type__.__table__.c.id.key,
#                 self.accounts_service.dto_type.__dao_type__.__table__.c.name.key,
#                 self.accounts_service.dto_type.__dao_type__.__table__.c.tags.key,
#             ]
#         ]
#         data_columns = [
#             self.service.dto_type.__dao_type__.__table__.c.from_account_id.key,
#             self.service.dto_type.__dao_type__.__table__.c.to_account_id.key,
#         ]
#         data_ = data.copy()

#         id_column = self.accounts_service.dto_type.__dao_type__.__table__.c.id.key
#         name_column = self.accounts_service.dto_type.__dao_type__.__table__.c.name.key
#         tags_column = self.accounts_service.dto_type.__dao_type__.__table__.c.tags.key

#         # Create a mapping cache to avoid redundant lookups
#         account_map: dict[type, type] = {}

#         # Process each column that needs account matching
#         for col in data_columns:
#             if col in data_.columns:
#                 # Create a new column for the matched IDs
#                 matched_col = f"{col}_matched"
#                 data_[matched_col] = None

#                 # Match each account in the column
#                 for idx, value in data_[col].items():
#                     if pd.isna(value) or value == "":
#                         continue

#                     # Use cached result if available
#                     if value in account_map:
#                         data_.at[idx, matched_col] = account_map[value]
#                     else:
#                         try:
#                             # Match account and store in cache
#                             matched_id = self._match(value, accounts, id_column, name_column, tags_column)
#                             account_map[value] = matched_id
#                             data_.at[idx, matched_col] = matched_id
#                         except ValueError as e:
#                             logger.warning(f"Account matching error for '{value}': {str(e)}")

#                 # Replace original column with matched IDs
#                 data_[col] = data_[matched_col]
#                 data_.drop(columns=[matched_col], inplace=True)

#         return data_

#     def load(self, *, data: pd.DataFrame, **kwargs) -> "AbstractLoadHandler":
#         logger.debug("Loading data from loader '%s'", self.loader.__class__.__name__)
#         return self
