# pylint: disable=C0103
"""Add payment-due columns on transaction_templates (PPT-071 / #164).

Revision ID: j7e8f9a0b1c2
Revises: i6d7e8f9a0b1
Create Date: 2026-08-06 15:00:00.000000+00:00

Additive nullable columns only — no backfill. Paid state remains derived from
posted ``transactions.template_id`` (mark-paid in PPT-072), not template flags.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from papita_txnsmodel.model.contstants import (
    ACCOUNTS__TABLENAME,
    SCHEMA_NAME,
    TRANSACTION_TEMPLATES__TABLENAME,
)

revision: str = "j7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "i6d7e8f9a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FK_FROM_ACCOUNT = "fk_transaction_templates_from_account_id"
_IX_OWNER_DUE_DATE = "ix_transaction_templates_owner_due_date"


def upgrade() -> None:
    """Add due_date, remind_days_before, and optional pay-from account FK."""
    op.add_column(
        TRANSACTION_TEMPLATES__TABLENAME,
        sa.Column("due_date", sa.Date(), nullable=True),
        schema=SCHEMA_NAME,
    )
    op.add_column(
        TRANSACTION_TEMPLATES__TABLENAME,
        sa.Column("remind_days_before", sa.SmallInteger(), nullable=True),
        schema=SCHEMA_NAME,
    )
    op.add_column(
        TRANSACTION_TEMPLATES__TABLENAME,
        sa.Column("from_account_id", sa.Uuid(), nullable=True),
        schema=SCHEMA_NAME,
    )
    op.create_foreign_key(
        _FK_FROM_ACCOUNT,
        TRANSACTION_TEMPLATES__TABLENAME,
        ACCOUNTS__TABLENAME,
        ["from_account_id"],
        ["id"],
        source_schema=SCHEMA_NAME,
        referent_schema=SCHEMA_NAME,
    )
    op.create_index(
        _IX_OWNER_DUE_DATE,
        TRANSACTION_TEMPLATES__TABLENAME,
        ["owner_id", "due_date"],
        unique=False,
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    """Drop payment-due columns and supporting FK/index."""
    op.drop_index(
        _IX_OWNER_DUE_DATE,
        table_name=TRANSACTION_TEMPLATES__TABLENAME,
        schema=SCHEMA_NAME,
    )
    op.drop_constraint(
        _FK_FROM_ACCOUNT,
        TRANSACTION_TEMPLATES__TABLENAME,
        schema=SCHEMA_NAME,
        type_="foreignkey",
    )
    op.drop_column(TRANSACTION_TEMPLATES__TABLENAME, "from_account_id", schema=SCHEMA_NAME)
    op.drop_column(TRANSACTION_TEMPLATES__TABLENAME, "remind_days_before", schema=SCHEMA_NAME)
    op.drop_column(TRANSACTION_TEMPLATES__TABLENAME, "due_date", schema=SCHEMA_NAME)
