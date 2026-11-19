"""Tests for alembic_utils materialized view entities."""

from alembic_utils.pg_materialized_view import PGMaterializedView

from papita_txnsmodel.model.contstants import (
    ACCOUNT_BALANCES_VIEW,
    OWNER_BIANNUAL_BALANCES_VIEW,
    OWNER_MONTHLY_BALANCES_VIEW,
    OWNER_QUARTERLY_BALANCES_VIEW,
    OWNER_YEARLY_BALANCES_VIEW,
    SCHEMA_NAME,
)
from papita_txnsmodel.views import (
    ACCOUNT_BALANCES_MATERIALIZED_VIEW,
    OWNER_BIANNUAL_BALANCES_MATERIALIZED_VIEW,
    OWNER_MONTHLY_BALANCES_MATERIALIZED_VIEW,
    OWNER_QUARTERLY_BALANCES_MATERIALIZED_VIEW,
    OWNER_YEARLY_BALANCES_MATERIALIZED_VIEW,
    view_entities,
)
from papita_txnsmodel.views.balance_reports.views import (
    account_balances,
    owner_biannual_balances,
    owner_monthly_balances,
    owner_quarterly_balances,
    owner_yearly_balances,
)
from papita_txnsmodel.views.base import read_data_from_package_file

_BALANCE_REPORTS_PACKAGE = "papita_txnsmodel.views.balance_reports"


def test_read_data_from_package_file_loads_account_balances_sql() -> None:
    """SQL definitions are externalized and loadable from the package."""
    sql = read_data_from_package_file(_BALANCE_REPORTS_PACKAGE, "account_balances.sql")
    assert "papita_transactions.accounts" in sql
    assert "per_owner_account_net" in sql
    assert "t.owner_id = a_to.owner_id" in sql
    assert "t.owner_id = a_from.owner_id" in sql
    assert "GROUP BY" in sql


def test_account_balances_materialized_view_metadata() -> None:
    """MV entity matches schema constants and is registered for Alembic."""
    assert isinstance(ACCOUNT_BALANCES_MATERIALIZED_VIEW, PGMaterializedView)
    assert account_balances.schema == SCHEMA_NAME
    assert account_balances.signature == ACCOUNT_BALANCES_VIEW
    assert account_balances.with_data is True
    assert ACCOUNT_BALANCES_MATERIALIZED_VIEW in view_entities


def test_owner_yearly_balances_materialized_view_metadata() -> None:
    """Yearly combined MV is registered and uses owner schema constants."""
    assert isinstance(OWNER_YEARLY_BALANCES_MATERIALIZED_VIEW, PGMaterializedView)
    assert owner_yearly_balances.schema == SCHEMA_NAME
    assert owner_yearly_balances.signature == OWNER_YEARLY_BALANCES_VIEW
    assert owner_yearly_balances.with_data is True
    assert OWNER_YEARLY_BALANCES_MATERIALIZED_VIEW in view_entities


def test_owner_period_balance_materialized_views_registered() -> None:
    """Monthly, quarterly, and biannual MVs are registered for Alembic."""
    assert owner_monthly_balances.signature == OWNER_MONTHLY_BALANCES_VIEW
    assert owner_quarterly_balances.signature == OWNER_QUARTERLY_BALANCES_VIEW
    assert owner_biannual_balances.signature == OWNER_BIANNUAL_BALANCES_VIEW
    assert OWNER_MONTHLY_BALANCES_MATERIALIZED_VIEW in view_entities
    assert OWNER_QUARTERLY_BALANCES_MATERIALIZED_VIEW in view_entities
    assert OWNER_BIANNUAL_BALANCES_MATERIALIZED_VIEW in view_entities
    assert len(view_entities) == 5


def test_owner_period_balance_sql_files_load() -> None:
    """Period balance SQL is externalized under balance_reports."""
    monthly_sql = read_data_from_package_file(_BALANCE_REPORTS_PACKAGE, "owner_monthly_balances.sql")
    quarterly_sql = read_data_from_package_file(_BALANCE_REPORTS_PACKAGE, "owner_quarterly_balances.sql")
    biannual_sql = read_data_from_package_file(_BALANCE_REPORTS_PACKAGE, "owner_biannual_balances.sql")
    assert "balance_month" in monthly_sql
    assert "balance_quarter" in quarterly_sql
    assert "balance_half" in biannual_sql


def test_owner_yearly_balances_sql_aggregates_by_owner_and_year() -> None:
    """SQL externalization includes owner-level yearly rollup."""
    sql = read_data_from_package_file(_BALANCE_REPORTS_PACKAGE, "owner_yearly_balances.sql")
    assert "balance_year" in sql
    assert "total_balance" in sql
    assert "yearly_net_change" in sql


def test_account_balances_create_sql_includes_with_data() -> None:
    """Seed migration relies on WITH DATA for immediate reads."""
    create_sql = str(ACCOUNT_BALANCES_MATERIALIZED_VIEW.to_sql_statement_create())
    assert "CREATE MATERIALIZED VIEW" in create_sql
    assert "WITH" in create_sql and "DATA" in create_sql
    assert ACCOUNT_BALANCES_VIEW in create_sql
