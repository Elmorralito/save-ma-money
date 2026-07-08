"""SQL builders for balance report materialized view queries."""

from __future__ import annotations

import uuid

from papita_txnsmodel.model.contstants import SCHEMA_NAME

REPORT_ORDER_BY: dict[str, str] = {
    "account_balances": "currency, account_id",
    "owner_yearly_balances": "balance_year DESC, currency",
    "owner_monthly_balances": "balance_year DESC, balance_month DESC, currency",
    "owner_quarterly_balances": "balance_year DESC, balance_quarter DESC, currency",
    "owner_biannual_balances": "balance_year DESC, balance_half DESC, currency",
}


def build_balance_report_query_sql(
    *,
    view_name: str,
    report_id: str,
    owner_id: uuid.UUID,
    filters: dict[str, object] | None = None,
) -> tuple[str, dict[str, object]]:
    """Build SELECT SQL and bind parameters for a tenant-scoped balance report.

    Mirrors the predicate and ordering used by ``BalanceReportsRepository``.

    Args:
        view_name: Materialized view relation name.
        report_id: Balance report identifier for ORDER BY selection.
        owner_id: Tenant owner UUID.
        filters: Optional validated filter mapping.

    Returns:
        tuple[str, dict[str, object]]: SQL text and bind parameters.
    """
    statement_sql = f"SELECT * FROM {SCHEMA_NAME}.{view_name} WHERE owner_id = :owner_id"
    params: dict[str, object] = {"owner_id": owner_id}

    for key, value in (filters or {}).items():
        if key == "account_id" and isinstance(value, uuid.UUID):
            statement_sql += " AND account_id = :account_id"
            params["account_id"] = value
        elif key == "currency":
            statement_sql += " AND currency = :currency"
            params["currency"] = value
        elif key == "balance_year":
            statement_sql += " AND balance_year = :balance_year"
            params["balance_year"] = value
        elif key == "balance_month":
            statement_sql += " AND balance_month = :balance_month"
            params["balance_month"] = value
        elif key == "balance_quarter":
            statement_sql += " AND balance_quarter = :balance_quarter"
            params["balance_quarter"] = value
        elif key == "balance_half":
            statement_sql += " AND balance_half = :balance_half"
            params["balance_half"] = value

    order_by = REPORT_ORDER_BY.get(report_id, "currency")
    statement_sql += f" ORDER BY {order_by}"
    return statement_sql, params
