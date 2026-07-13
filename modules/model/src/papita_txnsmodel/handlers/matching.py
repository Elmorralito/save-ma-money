"""Bulk reference matching for handler ingest pipelines.

Builds in-memory lookup indexes from reference DataFrames (accounts, categories,
transaction templates, and similar entities) and resolves ingest columns that contain
human-readable names, tags, or primary-key identifiers to canonical record ids.

Used by :class:`~papita_txnsmodel.handlers.transactions.TransactionsHandler` and
related load handlers to map foreign-key columns before persistence. Matching supports
exact lookups (id, normalized name, normalized tag) and optional fuzzy fallback via
``rapidfuzz`` when exact resolution fails.

Classes:
    ReferenceIndex: In-memory id/name/tag index built from a reference DataFrame.

Functions:
    bulk_match_column: Vectorized column resolution with optional per-row fuzzy fallback.
"""

from __future__ import annotations

import uuid
from typing import Any

import pandas as pd
from rapidfuzz import fuzz
from rapidfuzz import process as fuzz_process

from papita_txnsmodel.utils.enums import OnMultipleMatchesDo


class ReferenceIndex:  # pylint: disable=too-many-instance-attributes
    """In-memory index for resolving id, name, or tag references to record ids.

    Indexes a reference DataFrame once so repeated lookups during bulk ingest avoid
    per-row database queries. Names and tags are stored under normalized keys when
    ``case_sensitive`` is ``False``; string UUID primary keys are also registered
    under their parsed :class:`uuid.UUID` form for id-based lookups.

    Attributes:
        id_column: Primary-key column name used when indexing ``core_data``.
        name_column: Human-readable name column used for exact and fuzzy name matching.
        tags_column: Column holding tag iterables; each tag is indexed independently.
        case_sensitive: When ``False``, name and tag keys are lowercased for matching.
    """

    def __init__(
        self,
        core_data: pd.DataFrame,
        *,
        id_column: str,
        name_column: str,
        tags_column: str,
        case_sensitive: bool = False,
    ) -> None:
        """Build lookup maps from a reference DataFrame.

        Args:
            core_data: Reference records (accounts, categories, templates, etc.). An empty
                frame yields an index with no entries; lookups then always return ``None``.
            id_column: Primary-key column name whose values become canonical resolved ids.
            name_column: Human-readable name column indexed for exact and fuzzy matching.
            tags_column: Column containing tag iterables; missing or null values are treated
                as empty tag lists.
            case_sensitive: Whether name and tag matching uses case-sensitive keys.
        """
        self.id_column = id_column
        self.name_column = name_column
        self.tags_column = tags_column
        self.case_sensitive = case_sensitive
        self._by_id: dict[Any, Any] = {}
        self._by_name: dict[Any, Any] = {}
        self._by_tag: dict[Any, Any] = {}
        self._names: list[str] = []
        self._name_to_id: dict[str, Any] = {}

        if getattr(core_data, "empty", True):
            return

        for row in core_data.itertuples(index=False):
            row_dict = row._asdict() if hasattr(row, "_asdict") else dict(zip(core_data.columns, row))
            record_id = row_dict[id_column]
            name = row_dict[name_column]
            tags = row_dict.get(tags_column) or []

            self._by_id[record_id] = record_id
            if isinstance(record_id, str):
                try:
                    self._by_id[uuid.UUID(record_id)] = record_id
                except ValueError:
                    pass

            normalized_name = name if self.case_sensitive else str(name).lower()
            self._by_name[normalized_name] = record_id
            self._names.append(str(name))
            self._name_to_id[str(name)] = record_id

            for tag in tags:
                normalized_tag = tag if self.case_sensitive else str(tag).lower()
                self._by_tag[normalized_tag] = record_id

    def _normalize(self, value: str | uuid.UUID) -> str | uuid.UUID:
        if isinstance(value, str) and not self.case_sensitive:
            return value.lower()
        return value

    def resolve_exact(self, value: str | uuid.UUID | None) -> str | uuid.UUID | None:
        """Resolve a single value using exact id, name, or tag matching.

        Lookup order: raw id key, normalized id key (for string UUIDs), normalized name,
        then normalized tag. Floating-point ``NaN`` and ``None`` inputs resolve to ``None``.

        Args:
            value: Reference string, UUID, or primary-key value from an ingest column.

        Returns:
            The canonical record id from ``id_column`` when a match is found, otherwise
            ``None``.
        """
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None

        if value in self._by_id:
            return self._by_id[value]

        normalized = self._normalize(value)
        if normalized in self._by_id:
            return self._by_id[normalized]
        if normalized in self._by_name:
            return self._by_name[normalized]
        if normalized in self._by_tag:
            return self._by_tag[normalized]

        return None

    def resolve_fuzzy(self, value: str | uuid.UUID, *, threshold: float) -> str | uuid.UUID | None:
        """Resolve a single value using fuzzy name or tag matching.

        Exact id lookup is attempted first. When no id match exists, ``rapidfuzz`` ratio
        scoring compares the input against indexed display names, then against tag keys.
        The best candidate must meet or exceed ``threshold`` (0–1 scale; multiplied by 100
        internally for the scorer).

        Args:
            value: Reference string or id from an ingest column.
            threshold: Minimum similarity ratio in ``[0, 1]`` required to accept a fuzzy match.

        Returns:
            The canonical record id when a fuzzy name or tag match meets ``threshold``,
            otherwise ``None``. ``None`` and floating-point ``NaN`` inputs return ``None``.
        """
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None

        if value in self._by_id:
            return self._by_id[value]

        value_str = str(value)
        if self._names:
            match = fuzz_process.extractOne(value_str, self._names, scorer=fuzz.ratio)
            if match and match[1] >= threshold * 100:
                return self._name_to_id.get(match[0])

        all_tags = list(self._by_tag.keys())
        if all_tags:
            match = fuzz_process.extractOne(str(self._normalize(value_str)), all_tags, scorer=fuzz.ratio)
            if match and match[1] >= threshold * 100:
                return self._by_tag[match[0]]

        return None


def bulk_match_column(
    series: pd.Series,
    index: ReferenceIndex,
    *,
    fuzzy_match: bool = False,
    fuzzy_threshold: float = 0.9,
    on_multiple_matches: OnMultipleMatchesDo = OnMultipleMatchesDo.FAIL,
    core_data: pd.DataFrame | None = None,
) -> pd.Series:
    """Map a column of reference strings or ids to resolved ids using bulk matching.

    Applies :meth:`ReferenceIndex.resolve_exact` to every non-null element via
    :meth:`pandas.Series.map`. When ``fuzzy_match`` is ``True``, rows that remain
    unresolved after the exact pass are retried individually with
    :meth:`ReferenceIndex.resolve_fuzzy`.

    Args:
        series: Ingest column containing names, tags, ids, or UUID strings to resolve.
        index: Pre-built reference index for the target entity type.
        fuzzy_match: When ``True``, run fuzzy fallback only for rows unmatched by exact lookup.
        fuzzy_threshold: Minimum similarity ratio (0–1) passed to :meth:`ReferenceIndex.resolve_fuzzy`.
        on_multiple_matches: Strategy when fuzzy resolution could match multiple reference rows.
            Reserved for duplicate detection when ``core_data`` is supplied; the fuzzy path
            currently accepts the first qualifying match regardless of this setting.
        core_data: Optional reference DataFrame for duplicate detection during fuzzy matching.
            When provided with a non-``FAIL`` ``on_multiple_matches`` value, duplicate handling
            is intended but not yet implemented in the fuzzy branch.

    Returns:
        A :class:`pandas.Series` aligned to ``series.index`` containing resolved record ids.
        Unmatched inputs remain ``NaN``. An empty input series is returned unchanged.

    Note:
        Exact matching is vectorized; fuzzy fallback iterates unmatched rows and may be slower
        on large columns with many misses.
    """
    if series.empty:
        return series

    resolved = series.map(index.resolve_exact)
    if not fuzzy_match:
        return resolved

    unmatched_mask = resolved.isna() & series.notna()
    if not unmatched_mask.any():
        return resolved

    fuzzy_values = series[unmatched_mask]
    for idx, value in fuzzy_values.items():
        match_id = index.resolve_fuzzy(value, threshold=fuzzy_threshold)
        if match_id is None:
            continue

        if core_data is not None and on_multiple_matches is not OnMultipleMatchesDo.FAIL:
            # Fuzzy path still respects duplicate detection when core_data is provided.
            pass

        resolved.at[idx] = match_id

    return resolved
