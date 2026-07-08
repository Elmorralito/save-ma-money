"""Materialized view entity registry for Alembic and runtime refresh helpers.

Prefer ``papita_txnsmodel.views`` or ``papita_txnsmodel.views.balance_reports`` for view SQL.
"""

from papita_txnsmodel.views import (
    ACCOUNT_BALANCES_MATERIALIZED_VIEW,
    ALEMBIC_ENTITIES,
    OWNER_BIANNUAL_BALANCES_MATERIALIZED_VIEW,
    OWNER_MONTHLY_BALANCES_MATERIALIZED_VIEW,
    OWNER_QUARTERLY_BALANCES_MATERIALIZED_VIEW,
    OWNER_YEARLY_BALANCES_MATERIALIZED_VIEW,
    view_entities,
)
from papita_txnsmodel.views.balance_reports.views import account_balances

ACCOUNT_BALANCES_SELECT = account_balances.definition

__all__ = [
    "ACCOUNT_BALANCES_MATERIALIZED_VIEW",
    "ACCOUNT_BALANCES_SELECT",
    "ALEMBIC_ENTITIES",
    "OWNER_BIANNUAL_BALANCES_MATERIALIZED_VIEW",
    "OWNER_MONTHLY_BALANCES_MATERIALIZED_VIEW",
    "OWNER_QUARTERLY_BALANCES_MATERIALIZED_VIEW",
    "OWNER_YEARLY_BALANCES_MATERIALIZED_VIEW",
    "view_entities",
]
