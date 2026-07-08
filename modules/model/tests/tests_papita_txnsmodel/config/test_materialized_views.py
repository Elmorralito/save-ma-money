"""Tests for materialized view config re-exports."""

from papita_txnsmodel.config.materialized_views import (
    ACCOUNT_BALANCES_MATERIALIZED_VIEW,
    ACCOUNT_BALANCES_SELECT,
    view_entities,
)
from papita_txnsmodel.views.balance_reports.views import account_balances


def test_materialized_views_reexports_registry() -> None:
    """Config module exposes Alembic MV entities and account balance SQL."""
    assert ACCOUNT_BALANCES_MATERIALIZED_VIEW in view_entities
    assert ACCOUNT_BALANCES_SELECT == account_balances.definition
