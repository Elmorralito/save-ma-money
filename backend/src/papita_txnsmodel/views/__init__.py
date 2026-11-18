"""PostgreSQL materialized views managed via alembic_utils.

Central registry for Alembic autogenerate and ``alembic check`` parity.
Index definitions live in ``indexes.py`` (applied via Alembic migrations).
See https://pypi.org/project/alembic_utils/
"""

from papita_txnsmodel.views.balance_reports.views import (
    account_balances,
    owner_biannual_balances,
    owner_monthly_balances,
    owner_quarterly_balances,
    owner_yearly_balances,
)
from papita_txnsmodel.views.indexes import (
    ALL_VIEW_INDEX_SPECS,
    FETCH_SUPPORT_INDEX_SPECS,
    VIEW_INDEX_SPECS,
    ViewIndexSpec,
    get_indexes_for_report,
    get_indexes_for_view,
    list_indexed_report_ids,
)

view_entities = [
    account_balances,
    owner_yearly_balances,
    owner_monthly_balances,
    owner_quarterly_balances,
    owner_biannual_balances,
]

ALEMBIC_ENTITIES = view_entities

ACCOUNT_BALANCES_MATERIALIZED_VIEW = account_balances
OWNER_YEARLY_BALANCES_MATERIALIZED_VIEW = owner_yearly_balances
OWNER_MONTHLY_BALANCES_MATERIALIZED_VIEW = owner_monthly_balances
OWNER_QUARTERLY_BALANCES_MATERIALIZED_VIEW = owner_quarterly_balances
OWNER_BIANNUAL_BALANCES_MATERIALIZED_VIEW = owner_biannual_balances

__all__ = [
    "ACCOUNT_BALANCES_MATERIALIZED_VIEW",
    "ALEMBIC_ENTITIES",
    "ALL_VIEW_INDEX_SPECS",
    "FETCH_SUPPORT_INDEX_SPECS",
    "OWNER_BIANNUAL_BALANCES_MATERIALIZED_VIEW",
    "OWNER_MONTHLY_BALANCES_MATERIALIZED_VIEW",
    "OWNER_QUARTERLY_BALANCES_MATERIALIZED_VIEW",
    "OWNER_YEARLY_BALANCES_MATERIALIZED_VIEW",
    "VIEW_INDEX_SPECS",
    "ViewIndexSpec",
    "get_indexes_for_report",
    "get_indexes_for_view",
    "list_indexed_report_ids",
    "view_entities",
]
