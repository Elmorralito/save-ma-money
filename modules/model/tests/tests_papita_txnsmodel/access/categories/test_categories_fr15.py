"""Tests for v3 categories identity rules (FR-15)."""

from pathlib import Path


class TestCategoriesIdentityConstraint:
    """Categories table enforces per-tenant name uniqueness."""

    def test_seed_migration_declares_owner_name_kind_unique_index(self):
        """FR-15 composite unique (owner_id, name, category_kind) is in v3 seed DDL."""
        seed_path = Path(__file__).resolve().parents[4] / (
            "alembic/versions/2026_07_07_2325-a75354933e79_ppt_031_v3_seed_version.py"
        )
        contents = seed_path.read_text(encoding="utf-8")
        assert "uq_categories_owner_name_kind" in contents
        assert "postgresql_nulls_not_distinct=True" in contents or "NULLS NOT DISTINCT" in contents
