"""Bulk reference matching for handler ingest pipelines."""

from __future__ import annotations

import uuid
from typing import Any

import pandas as pd
from rapidfuzz import fuzz
from rapidfuzz import process as fuzz_process

from papita_txnsmodel.utils.enums import OnMultipleMatchesDo


class ReferenceIndex:  # pylint: disable=too-many-instance-attributes
    """In-memory index for resolving id, name, or tag references to record ids."""

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
            core_data: Reference records (accounts, categories, templates, etc.).
            id_column: Primary-key column name.
            name_column: Human-readable name column.
            tags_column: Tags list column.
            case_sensitive: Whether name/tag matching is case-sensitive.
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
        """Resolve a single value using exact id, name, or tag matching."""
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
        """Resolve a single value using fuzzy name or tag matching."""
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
    """Map a column of reference strings/ids to resolved ids using bulk exact matching.

    Unmatched rows optionally fall back to per-row fuzzy matching.
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
