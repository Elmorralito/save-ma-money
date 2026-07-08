"""Tests for balance report materialized view index registry."""

from papita_txnsmodel.config.balance_report_specs import list_report_ids
from papita_txnsmodel.views.indexes import (
    ALL_VIEW_INDEX_SPECS,
    FETCH_SUPPORT_INDEX_SPECS,
    get_indexes_for_report,
    list_indexed_report_ids,
)


class TestViewIndexRegistry:
    """Declarative index specs for balance report MVs."""

    def test_all_reports_have_index_specs(self):
        """Every YAML report has at least one index definition."""
        assert list_indexed_report_ids() == list_report_ids()
        for report_id in list_report_ids():
            assert get_indexes_for_report(report_id), f"missing indexes for {report_id}"

    def test_primary_unique_indexes_exist_for_all_views(self):
        """Each view has a unique index for concurrent refresh support."""
        unique_by_report = {
            report_id: [spec for spec in get_indexes_for_report(report_id) if spec.unique]
            for report_id in list_report_ids()
        }
        assert all(unique_by_report.values())
        assert len(unique_by_report) == 5

    def test_fetch_support_indexes_are_non_unique(self):
        """New fetch-support indexes are non-unique and owner+currency oriented."""
        assert len(FETCH_SUPPORT_INDEX_SPECS) == 5
        for spec in FETCH_SUPPORT_INDEX_SPECS:
            assert spec.unique is False
            assert spec.columns == ("owner_id", "currency")

    def test_index_names_are_unique(self):
        """Registry does not define duplicate index names."""
        names = [spec.name for spec in ALL_VIEW_INDEX_SPECS]
        assert len(names) == len(set(names))
