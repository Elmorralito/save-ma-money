"""Materialized view entities for balance report read models."""

from alembic_utils.pg_materialized_view import PGMaterializedView

from papita_txnsmodel.model.contstants import (
    ACCOUNT_BALANCES_VIEW,
    OWNER_BIANNUAL_BALANCES_VIEW,
    OWNER_MONTHLY_BALANCES_VIEW,
    OWNER_QUARTERLY_BALANCES_VIEW,
    OWNER_YEARLY_BALANCES_VIEW,
    SCHEMA_NAME,
)
from papita_txnsmodel.views.base import read_data_from_package_file

_PACKAGE: str = __package__ or "papita_txnsmodel.views.balance_reports"

account_balances = PGMaterializedView(
    schema=SCHEMA_NAME,
    signature=ACCOUNT_BALANCES_VIEW,
    definition=read_data_from_package_file(_PACKAGE, "account_balances.sql"),
    with_data=True,
)

owner_yearly_balances = PGMaterializedView(
    schema=SCHEMA_NAME,
    signature=OWNER_YEARLY_BALANCES_VIEW,
    definition=read_data_from_package_file(_PACKAGE, "owner_yearly_balances.sql"),
    with_data=True,
)

owner_monthly_balances = PGMaterializedView(
    schema=SCHEMA_NAME,
    signature=OWNER_MONTHLY_BALANCES_VIEW,
    definition=read_data_from_package_file(_PACKAGE, "owner_monthly_balances.sql"),
    with_data=True,
)

owner_quarterly_balances = PGMaterializedView(
    schema=SCHEMA_NAME,
    signature=OWNER_QUARTERLY_BALANCES_VIEW,
    definition=read_data_from_package_file(_PACKAGE, "owner_quarterly_balances.sql"),
    with_data=True,
)

owner_biannual_balances = PGMaterializedView(
    schema=SCHEMA_NAME,
    signature=OWNER_BIANNUAL_BALANCES_VIEW,
    definition=read_data_from_package_file(_PACKAGE, "owner_biannual_balances.sql"),
    with_data=True,
)

__all__ = [
    "account_balances",
    "owner_biannual_balances",
    "owner_monthly_balances",
    "owner_quarterly_balances",
    "owner_yearly_balances",
]
