"""Ingestion provenance, dead-letter, connection, and run tables.

PPT-078 / #172: provenance sidecar + thin DLQ.
PPT-083 / #177: non-secret connection metadata + run-status history (API read model).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKeyConstraint, Index, Integer, String, Text, text
from sqlmodel import Field

from .base import SCHEMA_NAME, BaseSQLModel
from .contstants import (
    INGESTION_CONNECTIONS__TABLENAME,
    INGESTION_DEAD_LETTERS__TABLENAME,
    INGESTION_RUNS__TABLENAME,
    TRANSACTION_INGESTION_PROVENANCE__TABLENAME,
    TRANSACTIONS__TABLENAME,
    USERS__TABLENAME,
)
from .enums import IngestionRunStatus, IngestionSource


class TransactionIngestionProvenance(BaseSQLModel, table=True):  # type: ignore
    """Non-partitioned idempotency / provenance registry for ingested transactions.

    Uniqueness lives here (not on partitioned ``transactions``) via a partial unique
    index on ``(owner_id, ingestion_source, source_ref)`` where ``source_ref`` is set.
    Soft-deleted rows still occupy the unique slot so re-ingest reactivates in place.
    """

    __tablename__ = TRANSACTION_INGESTION_PROVENANCE__TABLENAME
    __table_args__ = (
        ForeignKeyConstraint(
            ["transaction_id", "transaction_ts"],
            [f"{SCHEMA_NAME}.{TRANSACTIONS__TABLENAME}.id", f"{SCHEMA_NAME}.{TRANSACTIONS__TABLENAME}.transaction_ts"],
            name="fk_txn_ingest_prov_transaction",
        ),
        Index(
            "uq_txn_ingest_prov_owner_source_ref",
            "owner_id",
            "ingestion_source",
            "source_ref",
            unique=True,
            postgresql_where=text("source_ref IS NOT NULL"),
        ),
        Index("ix_txn_ingest_prov_owner_id", "owner_id"),
        Index("ix_txn_ingest_prov_transaction_id", "transaction_id"),
        {"schema": SCHEMA_NAME},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Indexes live in ``__table_args__`` (avoid duplicate Field(index=True) autogen names).
    owner_id: uuid.UUID = Field(foreign_key=f"{USERS__TABLENAME}.id", nullable=False)
    transaction_id: uuid.UUID = Field(nullable=False)
    transaction_ts: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    ingestion_source: IngestionSource = Field(
        sa_column=Column(
            SAEnum(IngestionSource, name="ingestion_source", schema=SCHEMA_NAME, create_type=False),
            nullable=False,
        )
    )
    source_ref: str | None = Field(default=None, max_length=255, sa_type=String(255), nullable=True)


class IngestionDeadLetter(BaseSQLModel, table=True):  # type: ignore
    """Minimal store for raw ingest payloads that failed parse/validation (PPT-078)."""

    __tablename__ = INGESTION_DEAD_LETTERS__TABLENAME
    __table_args__ = (
        Index("ix_ingestion_dead_letters_owner_source", "owner_id", "ingestion_source"),
        {"schema": SCHEMA_NAME},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key=f"{USERS__TABLENAME}.id", nullable=False)
    ingestion_source: IngestionSource = Field(
        sa_column=Column(
            SAEnum(IngestionSource, name="ingestion_source", schema=SCHEMA_NAME, create_type=False),
            nullable=False,
        )
    )
    raw_payload: str = Field(sa_type=Text, nullable=False, default="")
    error_message: str = Field(sa_type=Text, nullable=False, default="")
    source_ref: str | None = Field(default=None, max_length=255, sa_type=String(255), nullable=True)


class IngestionConnection(BaseSQLModel, table=True):  # type: ignore
    """Non-secret owner-scoped ingestion connection metadata (PPT-083 / #177).

    Upserted by the worker from settings + flow identity. Never stores OAuth tokens,
    client secrets, or raw mailbox credentials — those stay in env (``GMAIL_*``).
    """

    __tablename__ = INGESTION_CONNECTIONS__TABLENAME
    __table_args__ = (
        Index(
            "uq_ingestion_connections_owner_provider_flow",
            "owner_id",
            "provider",
            "flow_name",
            unique=True,
        ),
        Index("ix_ingestion_connections_owner_id", "owner_id"),
        {"schema": SCHEMA_NAME},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key=f"{USERS__TABLENAME}.id", nullable=False)
    provider: str = Field(max_length=64, sa_type=String(64), nullable=False, default="email")
    flow_name: str = Field(max_length=128, sa_type=String(128), nullable=False)
    deployment_name: str | None = Field(default=None, max_length=128, sa_type=String(128), nullable=True)
    enabled: bool = Field(nullable=False, default=True)
    lookback_hours: int = Field(nullable=False, default=24, sa_type=Integer)


class IngestionRun(BaseSQLModel, table=True):  # type: ignore
    """Owner-scoped ingestion run history for status APIs (PPT-083 / #177).

    Written by the worker after mapping ``RunResult`` counters into model fields.
    Does not store per-record failure payloads (avoid raw-leak adjacency).
    """

    __tablename__ = INGESTION_RUNS__TABLENAME
    __table_args__ = (
        ForeignKeyConstraint(
            ["connection_id"],
            [f"{SCHEMA_NAME}.{INGESTION_CONNECTIONS__TABLENAME}.id"],
            name="fk_ingestion_runs_connection_id",
        ),
        Index("ix_ingestion_runs_owner_id", "owner_id"),
        Index("ix_ingestion_runs_connection_id", "connection_id"),
        Index("ix_ingestion_runs_owner_started_at", "owner_id", "started_at"),
        {"schema": SCHEMA_NAME},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key=f"{USERS__TABLENAME}.id", nullable=False)
    connection_id: uuid.UUID | None = Field(default=None, nullable=True)
    status: IngestionRunStatus = Field(
        sa_column=Column(
            SAEnum(IngestionRunStatus, name="ingestion_run_status", schema=SCHEMA_NAME, create_type=False),
            nullable=False,
        )
    )
    started_at: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    finished_at: datetime | None = Field(default=None, sa_type=TIMESTAMP, nullable=True)
    fetched: int = Field(nullable=False, default=0, sa_type=Integer)
    created: int = Field(nullable=False, default=0, sa_type=Integer)
    updated: int = Field(nullable=False, default=0, sa_type=Integer)
    reactivated: int = Field(nullable=False, default=0, sa_type=Integer)
    failed: int = Field(nullable=False, default=0, sa_type=Integer)
    dead_lettered: int = Field(nullable=False, default=0, sa_type=Integer)
    acknowledged: int = Field(nullable=False, default=0, sa_type=Integer)
    dry_run_skipped: int = Field(nullable=False, default=0, sa_type=Integer)
    error_summary: str | None = Field(default=None, sa_type=Text, nullable=True)
    flow_name: str | None = Field(default=None, max_length=128, sa_type=String(128), nullable=True)
    deployment_name: str | None = Field(default=None, max_length=128, sa_type=String(128), nullable=True)
