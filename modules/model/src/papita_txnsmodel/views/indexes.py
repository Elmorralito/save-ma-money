"""Declarative index registry for balance report materialized views.

alembic_utils ``PGMaterializedView`` tracks view SQL only; indexes are applied via
Alembic ``op.create_index`` / ``op.drop_index`` using specs from this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from papita_txnsmodel.model.contstants import (
    ACCOUNT_BALANCES_VIEW,
    OWNER_BIANNUAL_BALANCES_VIEW,
    OWNER_MONTHLY_BALANCES_VIEW,
    OWNER_QUARTERLY_BALANCES_VIEW,
    OWNER_YEARLY_BALANCES_VIEW,
    SCHEMA_NAME,
)

if TYPE_CHECKING:
    from alembic import op as alembic_op


@dataclass(frozen=True)
class ViewIndexSpec:
    """Index definition for a balance report materialized view."""

    report_id: str
    view_name: str
    name: str
    columns: tuple[str, ...]
    unique: bool
    rationale: str


_PRIMARY_UNIQUE_INDEXES: tuple[ViewIndexSpec, ...] = (
    ViewIndexSpec(
        report_id="account_balances",
        view_name=ACCOUNT_BALANCES_VIEW,
        name="account_balances_owner_account_idx",
        columns=("owner_id", "account_id"),
        unique=True,
        rationale="Tenant account lookup; enables REFRESH MATERIALIZED VIEW CONCURRENTLY.",
    ),
    ViewIndexSpec(
        report_id="owner_yearly_balances",
        view_name=OWNER_YEARLY_BALANCES_VIEW,
        name="owner_yearly_balances_owner_year_currency_idx",
        columns=("owner_id", "balance_year", "currency"),
        unique=True,
        rationale="Year + currency fetch path; concurrent refresh support.",
    ),
    ViewIndexSpec(
        report_id="owner_monthly_balances",
        view_name=OWNER_MONTHLY_BALANCES_VIEW,
        name="owner_monthly_balances_owner_year_month_currency_idx",
        columns=("owner_id", "balance_year", "balance_month", "currency"),
        unique=True,
        rationale="Monthly period fetch path; concurrent refresh support.",
    ),
    ViewIndexSpec(
        report_id="owner_quarterly_balances",
        view_name=OWNER_QUARTERLY_BALANCES_VIEW,
        name="owner_quarterly_balances_owner_year_quarter_currency_idx",
        columns=("owner_id", "balance_year", "balance_quarter", "currency"),
        unique=True,
        rationale="Quarterly period fetch path; concurrent refresh support.",
    ),
    ViewIndexSpec(
        report_id="owner_biannual_balances",
        view_name=OWNER_BIANNUAL_BALANCES_VIEW,
        name="owner_biannual_balances_owner_year_half_currency_idx",
        columns=("owner_id", "balance_year", "balance_half", "currency"),
        unique=True,
        rationale="Biannual period fetch path; concurrent refresh support.",
    ),
)

_FETCH_SUPPORT_INDEXES: tuple[ViewIndexSpec, ...] = (
    ViewIndexSpec(
        report_id="account_balances",
        view_name=ACCOUNT_BALANCES_VIEW,
        name="account_balances_owner_currency_idx",
        columns=("owner_id", "currency"),
        unique=False,
        rationale="Owner + currency filter without account_id (YAML filter path).",
    ),
    ViewIndexSpec(
        report_id="owner_yearly_balances",
        view_name=OWNER_YEARLY_BALANCES_VIEW,
        name="owner_yearly_balances_owner_currency_idx",
        columns=("owner_id", "currency"),
        unique=False,
        rationale="Owner + currency filter without balance_year.",
    ),
    ViewIndexSpec(
        report_id="owner_monthly_balances",
        view_name=OWNER_MONTHLY_BALANCES_VIEW,
        name="owner_monthly_balances_owner_currency_idx",
        columns=("owner_id", "currency"),
        unique=False,
        rationale="Owner + currency filter without period keys.",
    ),
    ViewIndexSpec(
        report_id="owner_quarterly_balances",
        view_name=OWNER_QUARTERLY_BALANCES_VIEW,
        name="owner_quarterly_balances_owner_currency_idx",
        columns=("owner_id", "currency"),
        unique=False,
        rationale="Owner + currency filter without period keys.",
    ),
    ViewIndexSpec(
        report_id="owner_biannual_balances",
        view_name=OWNER_BIANNUAL_BALANCES_VIEW,
        name="owner_biannual_balances_owner_currency_idx",
        columns=("owner_id", "currency"),
        unique=False,
        rationale="Owner + currency filter without period keys.",
    ),
)

ALL_VIEW_INDEX_SPECS: tuple[ViewIndexSpec, ...] = _PRIMARY_UNIQUE_INDEXES + _FETCH_SUPPORT_INDEXES

VIEW_INDEX_SPECS: dict[str, tuple[ViewIndexSpec, ...]] = {
    report_id: tuple(spec for spec in ALL_VIEW_INDEX_SPECS if spec.report_id == report_id)
    for report_id in {spec.report_id for spec in ALL_VIEW_INDEX_SPECS}
}

FETCH_SUPPORT_INDEX_SPECS: tuple[ViewIndexSpec, ...] = _FETCH_SUPPORT_INDEXES


def list_indexed_report_ids() -> list[str]:
    """Return report ids that have index specifications."""
    return sorted(VIEW_INDEX_SPECS)


def get_indexes_for_view(view_name: str) -> tuple[ViewIndexSpec, ...]:
    """Return index specs for a materialized view relation name."""
    return tuple(spec for spec in ALL_VIEW_INDEX_SPECS if spec.view_name == view_name)


def get_indexes_for_report(report_id: str) -> tuple[ViewIndexSpec, ...]:
    """Return index specs for a balance report id."""
    return VIEW_INDEX_SPECS.get(report_id, ())


def create_view_index(op: "alembic_op", spec: ViewIndexSpec) -> None:
    """Create a materialized view index from a registry spec."""
    op.create_index(
        spec.name,
        spec.view_name,
        list(spec.columns),
        unique=spec.unique,
        schema=SCHEMA_NAME,
    )


def drop_view_index(op: "alembic_op", spec: ViewIndexSpec) -> None:
    """Drop a materialized view index from a registry spec."""
    op.drop_index(spec.name, table_name=spec.view_name, schema=SCHEMA_NAME)


__all__ = [
    "ALL_VIEW_INDEX_SPECS",
    "FETCH_SUPPORT_INDEX_SPECS",
    "SCHEMA_NAME",
    "VIEW_INDEX_SPECS",
    "ViewIndexSpec",
    "create_view_index",
    "drop_view_index",
    "get_indexes_for_report",
    "get_indexes_for_view",
    "list_indexed_report_ids",
]
