"""Ingestion provenance sidecar and dead-letter tables (PPT-078 / #172)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKeyConstraint, Index, String, Text, text
from sqlmodel import Field

from .base import SCHEMA_NAME, BaseSQLModel
from .contstants import (
    INGESTION_DEAD_LETTERS__TABLENAME,
    TRANSACTION_INGESTION_PROVENANCE__TABLENAME,
    TRANSACTIONS__TABLENAME,
    USERS__TABLENAME,
)
from .enums import IngestionSource


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
