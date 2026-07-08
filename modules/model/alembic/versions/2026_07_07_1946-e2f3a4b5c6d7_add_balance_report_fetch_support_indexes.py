# pylint: disable=C0103
"""Add fetch-support indexes for balance report materialized views.

Non-unique (owner_id, currency) indexes speed owner+currency filter paths that
are not covered by existing unique composite indexes.

Revision ID: e2f3a4b5c6d7
Revises: d1e9a4f62c8b
Create Date: 2026-07-07 19:46:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from papita_txnsmodel.views.indexes import FETCH_SUPPORT_INDEX_SPECS, create_view_index, drop_view_index

revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "d1e9a4f62c8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create fetch-support indexes from the views index registry."""
    for spec in FETCH_SUPPORT_INDEX_SPECS:
        create_view_index(op, spec)
    op.execute(sa.text("COMMIT"))


def downgrade() -> None:
    """Drop fetch-support indexes from the views index registry."""
    for spec in reversed(FETCH_SUPPORT_INDEX_SPECS):
        drop_view_index(op, spec)
