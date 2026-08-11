# pylint: disable=C0103
"""Add ingestion provenance sidecar and thin DLQ (PPT-078 / #172).

Revision ID: k8f9a0b1c2d3
Revises: j7e8f9a0b1c2
Create Date: 2026-08-11 14:00:00.000000+00:00

Non-partitioned registry for idempotent ingest. Uniqueness cannot live on the
partitioned ``transactions`` parent (PK is ``(id, transaction_ts)``).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from papita_txnsmodel.model.contstants import (
    INGESTION_DEAD_LETTERS__TABLENAME,
    SCHEMA_NAME,
    TRANSACTION_INGESTION_PROVENANCE__TABLENAME,
    TRANSACTIONS__TABLENAME,
    USERS__TABLENAME,
)

revision: str = "k8f9a0b1c2d3"
down_revision: Union[str, Sequence[str], None] = "j7e8f9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INGESTION_SOURCE_ENUM = "ingestion_source"
_UQ_PROV = "uq_txn_ingest_prov_owner_source_ref"
_FK_PROV_TXN = "fk_txn_ingest_prov_transaction"
_FK_PROV_OWNER = "fk_txn_ingest_prov_owner_id"
_FK_DLQ_OWNER = "fk_ingestion_dead_letters_owner_id"
_IX_PROV_OWNER = "ix_txn_ingest_prov_owner_id"
_IX_PROV_TXN = "ix_txn_ingest_prov_transaction_id"
_IX_DLQ_OWNER_SOURCE = "ix_ingestion_dead_letters_owner_source"


def _ingestion_source_type(*, create_type: bool = False) -> postgresql.ENUM:
    """Return the shared Postgres enum type for ingestion_source columns."""
    return postgresql.ENUM(
        "MANUAL",
        "CSV",
        "EMAIL",
        "API",
        name=_INGESTION_SOURCE_ENUM,
        schema=SCHEMA_NAME,
        create_type=create_type,
    )


def upgrade() -> None:
    """Create ingestion_source enum, provenance sidecar, and dead-letter table."""
    # Idempotent: Alembic/SQLAlchemy may otherwise emit CREATE TYPE twice in one txn.
    op.execute(sa.text(f"""
            DO $$ BEGIN
                CREATE TYPE {SCHEMA_NAME}.{_INGESTION_SOURCE_ENUM}
                    AS ENUM ('MANUAL', 'CSV', 'EMAIL', 'API');
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """))
    ingestion_source = _ingestion_source_type(create_type=False)

    op.create_table(
        TRANSACTION_INGESTION_PROVENANCE__TABLENAME,
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_ts", sa.TIMESTAMP(), nullable=False),
        sa.Column("ingestion_source", ingestion_source, nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            [f"{SCHEMA_NAME}.{USERS__TABLENAME}.id"],
            name=_FK_PROV_OWNER,
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id", "transaction_ts"],
            [f"{SCHEMA_NAME}.{TRANSACTIONS__TABLENAME}.id", f"{SCHEMA_NAME}.{TRANSACTIONS__TABLENAME}.transaction_ts"],
            name=_FK_PROV_TXN,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        _IX_PROV_OWNER,
        TRANSACTION_INGESTION_PROVENANCE__TABLENAME,
        ["owner_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        _IX_PROV_TXN,
        TRANSACTION_INGESTION_PROVENANCE__TABLENAME,
        ["transaction_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        _UQ_PROV,
        TRANSACTION_INGESTION_PROVENANCE__TABLENAME,
        ["owner_id", "ingestion_source", "source_ref"],
        unique=True,
        schema=SCHEMA_NAME,
        postgresql_where=sa.text("source_ref IS NOT NULL"),
    )

    op.create_table(
        INGESTION_DEAD_LETTERS__TABLENAME,
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("ingestion_source", ingestion_source, nullable=False),
        sa.Column("raw_payload", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            [f"{SCHEMA_NAME}.{USERS__TABLENAME}.id"],
            name=_FK_DLQ_OWNER,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        _IX_DLQ_OWNER_SOURCE,
        INGESTION_DEAD_LETTERS__TABLENAME,
        ["owner_id", "ingestion_source"],
        unique=False,
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    """Drop dead-letter and provenance tables, then the ingestion_source enum."""
    op.drop_index(
        _IX_DLQ_OWNER_SOURCE,
        table_name=INGESTION_DEAD_LETTERS__TABLENAME,
        schema=SCHEMA_NAME,
    )
    op.drop_table(INGESTION_DEAD_LETTERS__TABLENAME, schema=SCHEMA_NAME)

    op.drop_index(
        _UQ_PROV,
        table_name=TRANSACTION_INGESTION_PROVENANCE__TABLENAME,
        schema=SCHEMA_NAME,
    )
    op.drop_index(
        _IX_PROV_TXN,
        table_name=TRANSACTION_INGESTION_PROVENANCE__TABLENAME,
        schema=SCHEMA_NAME,
    )
    op.drop_index(
        _IX_PROV_OWNER,
        table_name=TRANSACTION_INGESTION_PROVENANCE__TABLENAME,
        schema=SCHEMA_NAME,
    )
    op.drop_table(TRANSACTION_INGESTION_PROVENANCE__TABLENAME, schema=SCHEMA_NAME)

    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA_NAME}.{_INGESTION_SOURCE_ENUM}"))
