# pylint: disable=C0103
"""Link papita_transactions.users to Supabase Auth identity.

Revision ID: h5c6d7e8f9a0
Revises: g4b5c6d7e8f9
Create Date: 2026-07-13 22:20:00.000000+00:00

``users.id`` is the Supabase Auth user id (JWT ``sub`` / ``auth.users.id``).
Credentials live in Supabase Auth; ``password`` is nullable and used only for
``auth_provider='local'`` (tests / transitional HS256).

A true FK to ``auth.users(id)`` is only valid on Supabase-hosted Postgres
(where the ``auth`` schema exists). Docker B0 and plain Postgres skip that FK.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from papita_txnsmodel.model.contstants import SCHEMA_NAME, USERS__TABLENAME

revision: str = "h5c6d7e8f9a0"
down_revision: Union[str, Sequence[str], None] = "g4b5c6d7e8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_USERS = f'"{SCHEMA_NAME}"."{USERS__TABLENAME}"'


def upgrade() -> None:
    """Add auth_provider, nullify Auth-managed passwords, document Auth link."""
    op.add_column(
        USERS__TABLENAME,
        sa.Column(
            "auth_provider",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'supabase'"),
            comment="Identity authority: supabase | local",
        ),
        schema=SCHEMA_NAME,
    )
    # Existing rows predate Auth linkage and store local Argon2 hashes.
    op.execute(sa.text(f"UPDATE {_USERS} SET auth_provider = 'local' WHERE password IS NOT NULL"))
    op.alter_column(
        USERS__TABLENAME,
        "password",
        existing_type=sa.String(),
        nullable=True,
        schema=SCHEMA_NAME,
    )
    op.execute(sa.text(f"COMMENT ON COLUMN {_USERS}.id IS " f"'Supabase Auth user id (auth.users.id / JWT sub)'"))
    # Optional: on Supabase Postgres only —
    # ALTER TABLE papita_transactions.users
    #   ADD CONSTRAINT users_auth_users_fk
    #   FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;


def downgrade() -> None:
    """Restore NOT NULL password and drop auth_provider."""
    op.execute(sa.text(f"UPDATE {_USERS} SET password = " f"'__downgrade_placeholder__' WHERE password IS NULL"))
    op.alter_column(
        USERS__TABLENAME,
        "password",
        existing_type=sa.String(),
        nullable=False,
        schema=SCHEMA_NAME,
    )
    op.drop_column(USERS__TABLENAME, "auth_provider", schema=SCHEMA_NAME)
    op.execute(sa.text(f"COMMENT ON COLUMN {_USERS}.id IS NULL"))
