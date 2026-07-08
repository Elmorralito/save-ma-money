# pylint: disable=C0103
"""Add composite and FK indexes for tenant ledger and account query paths.

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-07-07 19:54:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, Sequence[str], None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCHEMA = "papita_transactions"


def upgrade() -> None:
    """Create table indexes declared on SQLModel entities."""
    op.create_index(
        "ix_accounts_owner_active",
        "accounts",
        ["owner_id", "active"],
        unique=False,
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_transaction_templates_owner_category",
        "transaction_templates",
        ["owner_id", "category_id"],
        unique=False,
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_transactions_owner_active_status",
        "transactions",
        ["owner_id", "active", "status"],
        unique=False,
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_transactions_owner_transaction_ts",
        "transactions",
        ["owner_id", "transaction_ts"],
        unique=False,
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_transactions_from_account_id",
        "transactions",
        ["from_account_id"],
        unique=False,
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_transactions_to_account_id",
        "transactions",
        ["to_account_id"],
        unique=False,
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_transactions_category_id",
        "transactions",
        ["category_id"],
        unique=False,
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_account_financing_loan_account_id",
        "account_financing",
        ["loan_account_id"],
        unique=False,
        schema=_SCHEMA,
    )
    op.execute(sa.text("COMMIT"))


def downgrade() -> None:
    """Drop table indexes added for ledger and tenant query paths."""
    op.drop_index(
        "ix_account_financing_loan_account_id",
        table_name="account_financing",
        schema=_SCHEMA,
    )
    op.drop_index(
        "ix_transactions_category_id",
        table_name="transactions",
        schema=_SCHEMA,
    )
    op.drop_index(
        "ix_transactions_to_account_id",
        table_name="transactions",
        schema=_SCHEMA,
    )
    op.drop_index(
        "ix_transactions_from_account_id",
        table_name="transactions",
        schema=_SCHEMA,
    )
    op.drop_index(
        "ix_transactions_owner_transaction_ts",
        table_name="transactions",
        schema=_SCHEMA,
    )
    op.drop_index(
        "ix_transactions_owner_active_status",
        table_name="transactions",
        schema=_SCHEMA,
    )
    op.drop_index(
        "ix_transaction_templates_owner_category",
        table_name="transaction_templates",
        schema=_SCHEMA,
    )
    op.drop_index(
        "ix_accounts_owner_active",
        table_name="accounts",
        schema=_SCHEMA,
    )
