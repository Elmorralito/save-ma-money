# pylint: disable=C0103
"""Add ingestion connection and run-status tables (PPT-083 / #177).

Revision ID: l9a0b1c2d3e4
Revises: k8f9a0b1c2d3
Create Date: 2026-08-12 12:00:00.000000+00:00

Non-secret connection metadata + append-only run history for status APIs.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from papita_txnsmodel.model.contstants import (
    INGESTION_CONNECTIONS__TABLENAME,
    INGESTION_RUNS__TABLENAME,
    SCHEMA_NAME,
    USERS__TABLENAME,
)

revision: str = "l9a0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "k8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INGESTION_RUN_STATUS_ENUM = "ingestion_run_status"
_FK_CONN_OWNER = "fk_ingestion_connections_owner_id"
_FK_RUN_OWNER = "fk_ingestion_runs_owner_id"
_FK_RUN_CONN = "fk_ingestion_runs_connection_id"
_UQ_CONN = "uq_ingestion_connections_owner_provider_flow"
_IX_CONN_OWNER = "ix_ingestion_connections_owner_id"
_IX_RUN_OWNER = "ix_ingestion_runs_owner_id"
_IX_RUN_CONN = "ix_ingestion_runs_connection_id"
_IX_RUN_OWNER_STARTED = "ix_ingestion_runs_owner_started_at"


def _ingestion_run_status_type(*, create_type: bool = False) -> postgresql.ENUM:
    """Return the shared Postgres enum type for ingestion_run_status columns."""
    return postgresql.ENUM(
        "STARTED",
        "SUCCEEDED",
        "FAILED",
        "PARTIAL",
        name=_INGESTION_RUN_STATUS_ENUM,
        schema=SCHEMA_NAME,
        create_type=create_type,
    )


def upgrade() -> None:
    """Create ingestion_run_status enum, connections table, and runs table."""
    op.execute(sa.text(f"""
            DO $$ BEGIN
                CREATE TYPE {SCHEMA_NAME}.{_INGESTION_RUN_STATUS_ENUM}
                    AS ENUM ('STARTED', 'SUCCEEDED', 'FAILED', 'PARTIAL');
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """))
    run_status = _ingestion_run_status_type(create_type=False)

    op.create_table(
        INGESTION_CONNECTIONS__TABLENAME,
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("flow_name", sa.String(length=128), nullable=False),
        sa.Column("deployment_name", sa.String(length=128), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("lookback_hours", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            [f"{SCHEMA_NAME}.{USERS__TABLENAME}.id"],
            name=_FK_CONN_OWNER,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        _IX_CONN_OWNER,
        INGESTION_CONNECTIONS__TABLENAME,
        ["owner_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        _UQ_CONN,
        INGESTION_CONNECTIONS__TABLENAME,
        ["owner_id", "provider", "flow_name"],
        unique=True,
        schema=SCHEMA_NAME,
    )

    op.create_table(
        INGESTION_RUNS__TABLENAME,
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=True),
        sa.Column("status", run_status, nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("finished_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("fetched", sa.Integer(), nullable=False),
        sa.Column("created", sa.Integer(), nullable=False),
        sa.Column("updated", sa.Integer(), nullable=False),
        sa.Column("reactivated", sa.Integer(), nullable=False),
        sa.Column("failed", sa.Integer(), nullable=False),
        sa.Column("dead_lettered", sa.Integer(), nullable=False),
        sa.Column("acknowledged", sa.Integer(), nullable=False),
        sa.Column("dry_run_skipped", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("flow_name", sa.String(length=128), nullable=True),
        sa.Column("deployment_name", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            [f"{SCHEMA_NAME}.{USERS__TABLENAME}.id"],
            name=_FK_RUN_OWNER,
        ),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            [f"{SCHEMA_NAME}.{INGESTION_CONNECTIONS__TABLENAME}.id"],
            name=_FK_RUN_CONN,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        _IX_RUN_OWNER,
        INGESTION_RUNS__TABLENAME,
        ["owner_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        _IX_RUN_CONN,
        INGESTION_RUNS__TABLENAME,
        ["connection_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        _IX_RUN_OWNER_STARTED,
        INGESTION_RUNS__TABLENAME,
        ["owner_id", "started_at"],
        unique=False,
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    """Drop run and connection tables, then the ingestion_run_status enum."""
    op.drop_index(
        _IX_RUN_OWNER_STARTED,
        table_name=INGESTION_RUNS__TABLENAME,
        schema=SCHEMA_NAME,
    )
    op.drop_index(
        _IX_RUN_CONN,
        table_name=INGESTION_RUNS__TABLENAME,
        schema=SCHEMA_NAME,
    )
    op.drop_index(
        _IX_RUN_OWNER,
        table_name=INGESTION_RUNS__TABLENAME,
        schema=SCHEMA_NAME,
    )
    op.drop_table(INGESTION_RUNS__TABLENAME, schema=SCHEMA_NAME)

    op.drop_index(
        _UQ_CONN,
        table_name=INGESTION_CONNECTIONS__TABLENAME,
        schema=SCHEMA_NAME,
    )
    op.drop_index(
        _IX_CONN_OWNER,
        table_name=INGESTION_CONNECTIONS__TABLENAME,
        schema=SCHEMA_NAME,
    )
    op.drop_table(INGESTION_CONNECTIONS__TABLENAME, schema=SCHEMA_NAME)

    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA_NAME}.{_INGESTION_RUN_STATUS_ENUM}"))
